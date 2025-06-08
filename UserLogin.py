#%%     Import the necessary Modules
from PySide6 import QtCore, QtWidgets, QtGui
import sys, json, os, psutil, subprocess
import ExecImages


#%%     Define global functions and declare variable
rootPath = os.environ.get("EXEAMRootPath",None)
if rootPath:
    rootPath = rootPath.strip("\"'")

    imagesPath = os.path.join(rootPath,"Images")


#region:DynamicServerReplacementBlock
closablePID = validationToken = virtualParentName = virtualParentVersion = None
#endregion:DynamicServerReplacementBlock

#%%     LoginUi
class LoginUI(QtWidgets.QWidget):

    # userDetails = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()

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

        #region: User Settings and config initialization
        self.userSettings = QtCore.QSettings("Automater","Config")
        # self.userSettings = QtCore.QSettings(f"./AMConfig.ini", QtCore.QSettings.Format.IniFormat)

        #endregion

        #region: resize and form base of the app and add grid layout
        self.setWindowTitle("Automater")
        self.setFixedSize(354,216)
        widgetX = (self.screen().size().width()-354)*0.5
        widgetY = (self.screen().size().height()-216)*0.5
        self.setGeometry(widgetX, widgetY, 354, 216)
        self.gridLayout = QtWidgets.QGridLayout(self)
        #endregion

        #region: create the banner
        self.label_LoginBanner = QtWidgets.QLabel("Login",self)
        self.label_LoginBanner.setStyleSheet("""font-weight: bold;
                                                color: rgb(255, 255, 255);
                                                font-size: 60pt;
                                                font-family: Times;
                                                font-style: italic;
                                                border: 1px solid grey;
                                                border-radius : 10px;
                                                background-color: #8e8e91;
                                            """)

        self.label_LoginBanner.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.label_LoginBanner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_LoginBanner.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        self.gridLayout.addWidget(self.label_LoginBanner, 1, 1, 1, 4)
        #endregion

        #region: create the input fields username

        self.lineEdit_username = QtWidgets.QLineEdit(self)
        userID = self.loadSettings("userID",str)
        if userID !="":
            self.lineEdit_username.setText(userID)
        else: 
            self.lineEdit_username.setPlaceholderText("email")

        self.gridLayout.addWidget(self.lineEdit_username, 3, 1, 1, 4)
        
        #endregion

        #region: create the login button
        
        self.pushButton_Login = QtWidgets.QPushButton("Login", self)
        self.pushButton_Login.setFixedSize(61,25)
        self.pushButton_Login.setStyleSheet("""background-color: rgb(167, 253, 192);""")
        self.pushButton_Login.clicked.connect(self.validateUserDetails)

        self.gridLayout.addWidget(self.pushButton_Login, 5, 4, 1, 1, QtCore.Qt.AlignmentFlag.AlignRight)

        #endregion

        #region: create the Register option hint
        hLayout = QtWidgets.QHBoxLayout()
        hLayoutSpacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)


        self.label_newUserHint = QtWidgets.QLabel(self)
        self.label_newUserHint.setText("New User?")
        self.label_newUserHint.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.pushButton_Register = QtWidgets.QPushButton("Register", self)
        self.pushButton_Register.setText("Register")
        self.pushButton_Register.setStyleSheet(""" QPushButton {
                                                                border: none;       /* Remove border */
                                                                background: none;   /* Remove background */
                                                                color: rgb(52, 101, 164);
                                                                text-align: left;
                                                                padding: 0px;
                                                                }
                                                    QPushButton:hover {
                                                                    color: rgb(115, 210, 22);       /* Change text color on hover */
                                                                    }
                                                    QPushButton:pressed {
                                                                    /*font-style: italic;*/
                                                                    font-size: 16px;      
                                                                    }"""
                                            )
        self.pushButton_Register.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.pushButton_Register.setFixedWidth(63)

        self.pushButton_Register.clicked.connect(self.toggleLoginRegister)
        
        hLayout.addWidget(self.label_newUserHint)
        hLayout.addWidget(self.pushButton_Register)
    
        self.gridLayout.addItem(hLayoutSpacer, 6, 1, 1, 1)
        self.gridLayout.addLayout(hLayout, 6, 2, 1, 2)
        self.gridLayout.addItem(hLayoutSpacer, 6, 4, 1, 1)
        
        #endregion
    
    def toggleLoginRegister(self):
        
        if self.pushButton_Register.text() == "Register":
            
            self.label_LoginBanner.setText("Register")
            self.pushButton_Login.setText("Register")
            self.label_newUserHint.setText("Existing User?")
            self.pushButton_Register.setText("Login")
            # # print(f"{self.label_LoginBanner.size()}") --> 332,106

        elif self.pushButton_Register.text() == "Login":
 
            self.label_LoginBanner.setText("Login")
            self.pushButton_Login.setText("Login")
            self.label_newUserHint.setText("New User?")
            self.pushButton_Register.setText("Register")

    def validateUserDetails(self):
        email = self.lineEdit_username.text()
        
        if self.pushButton_Login.text() == "Login":

            self.userValidator = UserValidator(userDetails={"email":email, "userAction":"login"})
            
        elif self.pushButton_Login.text() == "Register":

            self.userValidator = UserValidator(userDetails={"email":email, "userAction":"register"})
            self.saveSettings("userID",email)

        self.userValidator.start()
        self.loadLoadingGif()
   
    def loadLoadingGif(self):
        loadingGif = QtGui.QMovie(os.path.join(imagesPath,"AMUserLoginAnim.gif"))
        loadingGif.setScaledSize(QtCore.QSize(300,100))
        self.label_LoginBanner.setMovie(loadingGif)
        loadingGif.start()

    def loadSettings(self, specificSetting:str=None, settingsType:type=None):

        if specificSetting:
            return self.userSettings.value(specificSetting, f"", settingsType)
        
        else:
            self.userID = self.userSettings.value("userID", f"", type=str)

    def saveSettings(self, settingName:str, settingValue, group:str=None):
            
            if group!=None:
                self.userSettings.beginGroup(group)
                self.userSettings.setValue(settingName, settingValue)
                self.userSettings.endGroup()

            else:
                self.userSettings.setValue(settingName, settingValue)

#%% `   Background Thread`
class UserValidator(QtCore.QThread):

    validatorResponse = QtCore.Signal(str)

    def __init__(self, userDetails:dict = None, parent:LoginUI = None):
        super().__init__(parent)
        self.userDetails = userDetails if userDetails is not None else {}


    def run(self):

        subprocess.Popen([os.path.join(rootPath, "Val.bin"), json.dumps(self.userDetails | {"parentName":sys.argv[0], "parentVersion": "1.0", "virtualParentName":virtualParentName, "virtualParentVersion":virtualParentVersion, "closablePID":os.getpid(), "requestedAction": "UserVal", "validationToken":validationToken})])

        # if self.userDetails.get("userAction") == "login":
        #     subprocess.Popen([python_executable,rootPath + "LocalCode/Val.py", json.dumps(self.userDetails | {"parentName":sys.argv[0], "parentVersion": "1.0", "virtualParentName":virtualParentName, "virtualParentVersion":virtualParentVersion, "closablePID":os.getpid(), "requestedAction": "UserVal", "validationToken":validationToken})])
        
        # else:

        #     subprocess.Popen([python_executable,rootPath + "LocalCode/Val.py", json.dumps(self.userDetails | {"parentName":sys.argv[0], "parentVersion": "1.0", "virtualParentName":virtualParentName, "virtualParentVersion":virtualParentVersion, "closablePID":os.getpid(), "requestedAction": "UserVal", "validationToken":validationToken})])

            # # print(f"UserValidator : exit")



#%%     Run the app

if __name__ == "__main__":

    app = QtWidgets.QApplication.instance()
    
    if not app:
        app = QtWidgets.QApplication([])

    userAuthWin = LoginUI()

    sys.exit(app.exec())

# %%
