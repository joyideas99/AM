#%%     Import necessary modules
import sys, psutil
import os, traceback, threading
import shutil
import zipfile
import tempfile
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton, QProgressBar, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from io import BytesIO
#%%     Global Variables

#region:DynamicServerReplacementBlock
update_url:str = r"http://localhost:5000/api/download-update"
obsolete_files = []; closablePID = None
#endregion:DynamicServerReplacementBlock

rootPath = os.environ.get("EXEAMRootPath",None) # os.path.abspath(os.path.dirname(__file__))
if rootPath:
    rootPath = rootPath.strip("\"'")
    
# # print(f"{__file__=}\n{os.path.dirname(__file__)}\n{rootPath=}\n{os.getcwd()=}")
UPDATE_ZIP_NAME = "update.zip"

#%%     Updater Thread

class UpdaterThread(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished_success = Signal()
    finished_failure = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        """Signal the thread to stop."""
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def run(self):
        try:

            self.status_changed.emit("Downloading update...")
            memory_file = self.download_update(update_url)
            if self.is_stopped():
                self.status_changed.emit("Update cancelled during download.")
                return

            self.status_changed.emit("Extracting update...")
            with tempfile.TemporaryDirectory() as extract_dir:
                self.extract_zip(memory_file, extract_dir)
                if self.is_stopped():
                    self.status_changed.emit("Update cancelled during extraction.")
                    return

                self.status_changed.emit("Removing obsolete files...")
                self.remove_obsolete_files(obsolete_files)
                if self.is_stopped():
                    self.status_changed.emit("Update cancelled during file removal.")
                    return

                self.status_changed.emit("Replacing app files...")
                self.replace_app_files(extract_dir, rootPath)
                if self.is_stopped():
                    self.status_changed.emit("Update cancelled during file replacement.")
                    return

            self.progress_changed.emit(100)
            self.status_changed.emit("Update completed successfully!")
            self.finished_success.emit()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            error_msg = f"Update failed: {str(e)}\n{tb}"
            self.finished_failure.emit(error_msg)

    def download_update(self, url):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_length = r.headers.get('content-length')
            memory_file = BytesIO()

            if total_length is None:
                memory_file.write(r.content)
                self.progress_changed.emit(100)
            else:
                dl = 0
                total_length = int(total_length)
                for chunk in r.iter_content(chunk_size=8192):
                    if self.is_stopped():
                        break
                    if chunk:
                        memory_file.write(chunk)
                        dl += len(chunk)
                        percent = int(dl * 100 / total_length)
                        self.progress_changed.emit(percent)

            memory_file.seek(0)
            return memory_file

    def extract_zip(self, memory_file, extract_dir):
        if self.is_stopped():
            return
        with zipfile.ZipFile(memory_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def remove_obsolete_files(self, obsolete_files_list):
        if self.is_stopped():
            return
        errors = []
        for obsolete_file in obsolete_files_list:
            if self.is_stopped():
                break
            path = os.path.join(rootPath, obsolete_file)
            if os.path.exists(path):
                try:
                    if os.path.isfile(path) or os.path.islink(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception as e:
                    errors.append(f"Failed to remove {path}: {e}")

        if errors:
            for err in errors:
                # print(err)
                pass
            self.status_changed.emit("Warning: Some obsolete files could not be removed.")

    def replace_app_files(self, source_dir, dest_dir):
        if self.is_stopped():
            return
        errors = []
        total_files = sum(len(files) for _, _, files in os.walk(source_dir))
        processed_files = 0

        for root, dirs, files in os.walk(source_dir):
            if self.is_stopped():
                break
            rel_path = os.path.relpath(root, source_dir)
            target_root = os.path.join(dest_dir, rel_path) if rel_path != '.' else dest_dir

            if not os.path.exists(target_root):
                try:
                    os.makedirs(target_root, exist_ok=True)
                except Exception as e:
                    errors.append(f"Failed to create directory {target_root}: {e}")
                    continue

            for file in files:
                if self.is_stopped():
                    break
                src_file = os.path.join(root, file)
                dest_file = os.path.join(target_root, file)

                try:
                    shutil.move(src_file, dest_file)
                except Exception:
                    try:
                        shutil.copy2(src_file, dest_file)
                        os.remove(src_file)
                    except Exception as e:
                        errors.append(f"Failed to replace file {dest_file}: {e}")

                processed_files += 1
                percent = int(processed_files * 100 / total_files)
                self.progress_changed.emit(percent)

        if errors:
            for err in errors:
                # print(err)
                pass
            self.status_changed.emit("Warning: Some files could not be replaced properly.")

#%%     UpdaterGUI

class UpdaterGUI(QWidget):
    def __init__(self):
        self.initUI()

        
        global closablePID
        if closablePID:

            closablePID = int(closablePID)

            if psutil.pid_exists(closablePID):

                try:
                    p = psutil.Process(closablePID)
                except psutil.NoSuchProcess:
                    return  # Process does not exist
                except psutil.AccessDenied:
                    # print(f"No permission to terminate process {closablePID}")
                    return

                try:
                    
                    p.terminate()  # Graceful termination (SIGTERM equivalent)
                    p.wait(timeout=5)  # Wait for process to terminate
                    # print(f"Process {closablePID} terminated successfully.")
                except psutil.TimeoutExpired:
                    # print(f"Process {closablePID} did not terminate in time; killing it.")
                    p.kill()  # Force kill
                except Exception as e:
                    # print(f"Failed to terminate process {closablePID}: {e}")
                    pass

                self.show()
                
            else:
                self.close()
        

    def initUI(self):
        super().__init__()
        self.setWindowTitle("Automater")
        self.setFixedSize(400, 150)
        widgetX = (self.screen().size().width()-400)*0.5
        widgetY = (self.screen().size().height()-150)*0.5
        self.setGeometry(widgetX, widgetY, 400, 150)

        self.glayout = QGridLayout(self)

        self.label_Status = QLabel("The version you are using is no longer supported.\nPlease update to the latest version.", self)
        self.label_Status.setFont("Arial")
        self.label_Status.setStyleSheet(f"""color: #ffffff;
                                            background-color: #8c8c8c;
                                            border-radius: 10px;""")
        self.label_Status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glayout.addWidget(self.label_Status,1,1,1,5)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.glayout.addWidget(self.progress_bar,2,1,1,5)

        self.button_Update = QPushButton("Update", self)
        self.button_Update.clicked.connect(self.start_update)
        self.glayout.addWidget(self.button_Update,3,3,1,1)

        self.updater_thread = None

    def start_update(self):
        self.button_Update.setEnabled(False)
        self.progress_bar.setValue(0)
        self.label_Status.setText("Starting update...")

        self.updater_thread = UpdaterThread()
        self.updater_thread.progress_changed.connect(self.progress_bar.setValue)
        self.updater_thread.status_changed.connect(self.label_Status.setText)
        self.updater_thread.finished_success.connect(self.on_update_success)
        self.updater_thread.finished_failure.connect(self.on_update_failure)
        self.updater_thread.start()

    def on_update_success(self):
        # If updater was updated, this instance will exit. Otherwise, show success message.
        QMessageBox.information(self, "Update", "Update completed successfully!\nPlease close this window and restart the app. ")
        self.button_Update.setEnabled(True)
        # Optionally restart app here

    def on_update_failure(self, error_msg):
        QMessageBox.critical(self, "Update Failed", f"Update failed:\n{error_msg}.\nPlease try after sometime.")
        self.label_Status.setText("Update failed.")
        self.button_Update.setEnabled(True)

    def closeEvent(self, event):
        if hasattr(self, "updater_thread"):
            if self.updater_thread.isRunning():
                self.updater_thread.stop()  # Signal thread to stop
                self.updater_thread.wait(3000)  # Wait up to 5 seconds for thread to finish
        return super().closeEvent(event)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = UpdaterGUI()
    sys.exit(app.exec())
