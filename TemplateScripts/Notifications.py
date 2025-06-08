#%% import necessary module
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

#%%     Import Locally defined modules

import psutil
    
def abortPID(abortPID: int = None):
    if abortPID:

        abortPID = int(abortPID)

        if psutil.pid_exists(abortPID):

            try:
                p = psutil.Process(abortPID)
            except psutil.NoSuchProcess:
                return  # Process does not exist
            except psutil.AccessDenied:
                # print(f"No permission to terminate process {abortPID}")
                return

            try:
                
                p.terminate()  # Graceful termination (SIGTERM equivalent)
                p.wait(timeout=5)  # Wait for process to terminate
                # print(f"Process {abortPID} terminated successfully.")
            except psutil.TimeoutExpired:
                # print(f"Process {abortPID} did not terminate in time; killing it.")
                p.kill()  # Force kill
            except Exception as e:
                # print(f"Failed to terminate process {abortPID}: {e}")
                pass
        

#region:DynamicServerReplacementBlock
closablePID = messageBoxText = None
#endregion:DynamicServerReplacementBlock

if closablePID:
    pid = int(closablePID)
    
    abortPID(pid)

if __name__ == "__main__" and messageBoxText:

    app = QApplication.instance()

    if not app:
        app = QApplication([])

    connectionMsg = QMessageBox(QMessageBox.Icon.Information,"Automater",messageBoxText)
    connectionMsg.show()

    sys.exit(app.exec())

