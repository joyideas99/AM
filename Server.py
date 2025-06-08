from flask import Flask, Response, request, send_file, g, jsonify, render_template, redirect, url_for, session, flash, abort

import os, re, sqlite3, json, zipfile, csv, secrets
from datetime import datetime, timedelta
from pytz import timezone
from io import BytesIO

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from io import StringIO

rootPath = os.path.abspath(os.path.dirname(__file__))
if rootPath:
    rootPath = rootPath.strip("\"'")

serverVersion = "1.0"
dbPath = os.path.join(rootPath, r"AM.db")

allowedPeerFiles = ['AMDynamicSplash.gif', 'AMStaticSplash.png', 'AMUserLoginAnim.gif', 'DynamicSplash.bin', 'ExecImages.db', 'Implm.bin', 'StaticSplash.bin', 'Val.bin']

def addValidationToken(validationToken):
    leaseTime = datetime.now().astimezone(timezone('Asia/Kolkata')) + timedelta(minutes=3)
    leaseTime = leaseTime.strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn=sqlite3.connect(dbPath)
        cursor=conn.cursor()
        cursor.execute(f'INSERT INTO EnvValTable(ValToken,LeaseTime) VALUES (?,?)', (validationToken,leaseTime))
        conn.commit()
        
    except sqlite3.OperationalError as e:
        raise

    finally:
        cursor.close()
        conn.close()

def cleanEnvValTable():
    conn=sqlite3.connect(dbPath)
    cursor=conn.cursor()
    cursor.execute(f'DELETE FROM EnvValTable WHERE LeaseTime < ?', (datetime.now().astimezone(timezone('Asia/Kolkata')),))
    conn.commit()
    conn.close()

def getLeaseTime(validationToken):
    conn=sqlite3.connect(dbPath)
    cursor=conn.cursor()
    cursor.execute(f'SELECT LeaseTime FROM EnvValTable WHERE ValToken = ?', (validationToken,))
    leaseTime:tuple = cursor.fetchone()
    if leaseTime:
        leaseTime:datetime = datetime.strptime(leaseTime[0],"%Y-%m-%d %H:%M:%S")
    conn.close()
    return leaseTime

def registerUser(userDetails:dict):

    print("registerUser")

    userID = f"""{userDetails["userOS"]}-{userDetails["userMAC"]}-{userDetails.get("email")}"""
    validity = datetime.now().date()+ timedelta(days=365)
    validity = validity.strftime("%Y-%m-%d")
    userPlan:str = "Trial"
    maxAllowedFiles:int = 3
    userKey:str = str(b"\xd5\xd2A\xf1\x02\xacx\xa5!YF\xc6\xf4\xddWL\xc4i8\xee\xe3}\xe9\xc4\x0b\x07'\xd1\xf3\xbb'\xc0")

    try:
        conn=sqlite3.connect(dbPath)
        cursor=conn.cursor()
        cursor.execute(f'INSERT INTO Users(userID,validity,userPlan,maxAllowedFiles,userKey) VALUES (?,?,?,?,?)', (userID,validity,userPlan,maxAllowedFiles,userKey))
        conn.commit()

    except sqlite3.OperationalError as e:
        raise

    finally:
        cursor.close()
        conn.close()

def getUserDetails(userDetails:dict):

    print("getUserDetails")

    userID = f"""{userDetails["userOS"]}-{userDetails["userMAC"]}-{userDetails.get("email")}"""

    conn=sqlite3.connect(dbPath)
    cursor=conn.cursor()
    cursor.execute(f'SELECT Validity, Notifications, UserPlan, MaxAllowedFiles, UserKey FROM Users WHERE UserID = ?', (userID,))
    userDetails = cursor.fetchone()
    cursor.close()
    conn.close()

    if userDetails:
        validity:datetime = datetime.strptime(userDetails[0],"%Y-%m-%d").astimezone(timezone('Asia/Kolkata'))
        notification:str = userDetails[1]
        plan:str = userDetails[2]
        maxAllowedFiles:int = userDetails[3]
        userKey:str = userDetails[4]

        return validity, notification, plan, maxAllowedFiles, userKey

    return None, None, None, None, None

def decreaseFileCount(userID:str):

    print("decreaseFileCount")
    
    try:
        conn=sqlite3.connect(dbPath)
        cursor=conn.cursor()
        cursor.execute(f"""UPDATE Users SET MaxAllowedFiles = MaxAllowedFiles - 1 WHERE UserID = ? AND MaxAllowedFiles > 0""",(userID,))
        conn.commit()

    except sqlite3.OperationalError as e:
        raise

    finally:
        cursor.close()
        conn.close()

    return ""

def addAlerts(alert,userID):
    try:
        conn=sqlite3.connect(dbPath)
        cursor=conn.cursor()
        cursor.execute("UPDATE Users SET Alerts = COALESCE(Alerts, '') || ?, Validity = ? WHERE UserID LIKE ?;", (f"{alert}\n", datetime.now().date()- timedelta(days=1) ,f"{userID}%"))
        conn.commit()
        
    except sqlite3.OperationalError as e:
        raise

    finally:
        cursor.close()
        conn.close()

def returnTemplate(returnFileTemplatePath, replacement):

    def replacementFunction(x):
        return replacement
    with open(returnFileTemplatePath,"r") as file:
        content = file.read()
        blockToReplace = r'(#region:DynamicServerReplacementBlock)[\w\W]*(#endregion:DynamicServerReplacementBlock)'
        content = re.sub(blockToReplace, lambda x: replacementFunction(x), content)
        
    return content

def validateEnv(params:dict):

    print("Inside validateEnv")

    if  os.path.basename(os.path.normpath(params["selfName"])) == r"Val.bin" and \
        os.path.basename(os.path.normpath(params["parentName"])) == r"DynamicSplash.py" and \
        all(x == y for x, y in zip(params["peerFiles"], allowedPeerFiles)) and len(params["peerFiles"]) == len(allowedPeerFiles) and \
        params["userMAC"] is not None:


        if params["selfVersion"] == params["parentVersion"] == serverVersion:

            try:
                validationToken = f"""{params["userOS"]}-{params["userMAC"]}-{datetime.now().timestamp()}"""
                addValidationToken(validationToken)

                returnFileTemplatePath = os.path.join(rootPath, r"UserLogin.py")
                replacement = f"""closablePID:int = {params['closablePID']}; validationToken = '{validationToken}'; virtualParentName = 'UserLogin.py'; virtualParentVersion = '1.0'"""
                
            except Exception as e:

                returnFileTemplatePath = os.path.join(rootPath, r"TemplateScripts",r"Notifications.py")
                messageBoxText = f"Error in starting the app : {e}. Please restart."
                replacement = f"""closablePID = {params['closablePID']}; messageBoxText:str = '{messageBoxText}'"""
                 
        else:

            returnFileTemplatePath = os.path.join(rootPath, r"Updater.py")
            try:
                obsolete_files = os.listdir(os.path.join(rootPath, r"UpdateManagement", "ObsoleteFiles" ))
            except Exception as e:
                print("Obsolete files' folder not present locally.")
                obsolete_files =[]

            replacement = f"""update_url:str = r"{request.base_url}/getUpdates"; obsolete_files = {obsolete_files}; closablePID = {params.get("closablePID")}"""
            print("\033[94m"+f"Inside valEnvUpdater - {request.base_url=}"+'\033[0m')
    
    else:
        print('\033[93m'+f"{params['peerFiles']=}"+'\033[0m'+"\n"+'\033[95m'+f"{allowedPeerFiles=}"+'\033[0m'+f"{params['selfName']=}\n{params['parentName']=}")

        alert = f"Unwanted files detected\n{params=}"
        userID = f"""{params["userOS"]}-{params["userMAC"]}"""
        addAlerts(alert, userID)

        returnFileTemplatePath = os.path.join(rootPath, r"TemplateScripts",r"Notifications.py")
        messageBoxText = f"Error in starting the app. Your access might have been revoked. Please contact the support."
        replacement = f"""closablePID = {params['closablePID']}; messageBoxText:str = '{messageBoxText}'"""
    
    return returnTemplate(returnFileTemplatePath,replacement)

def validateUser(params:dict):

    if datetime.now() < getLeaseTime(params["validationToken"]):
        if  os.path.basename(os.path.normpath(params["selfName"])) == r"Val.bin" and \
            os.path.basename(os.path.normpath(params["parentName"])) == r"Implm.bin" and params["virtualParentName"] == "UserLogin.py" and \
            all(x == y for x, y in zip(params["peerFiles"], allowedPeerFiles)) and len(params["peerFiles"]) == len(allowedPeerFiles) and \
            params["userMAC"] is not None:

            if params["selfVersion"] == params["parentVersion"] == params.get("virtualParentVersion") == serverVersion:

                if params.get("userAction") == "login":
                    return login(params)
                
                else:
                    return register(params)

            else:

                replacement = f"""update_url:str = r"{request.base_url}/getUpdates"; obsolete_files = []; closablePID = {params.get("closablePID")}"""
                return returnTemplate(os.path.join(rootPath, r"Updater.py"),replacement)
        
        else:
            print('\033[93m'+f"{params['parentName']=}"+'\033[0m'+"\n"+'\033[95m'+f"{os.path.join(rootPath, r'Implm.bin')=}"+'\033[0m')
            alert = f"Unwanted files detected\n{params=}"
            userID = f"""{params["userOS"]}-{params["userMAC"]}"""
            addAlerts(alert, userID)

            messageBoxText = f"Error in starting the app. Your access might have been revoked. Please contact the support."
            replacement = f"""closablePID = {params['closablePID']}; messageBoxText:str = '{messageBoxText}'"""

    else:

        replacement = f"closablePID=None; messageBoxText:str = 'Lease Time ended. Please login again'"
        
    return returnTemplate(os.path.join(rootPath, r"TemplateScripts",r"Notifications.py"),replacement)

def login(params:dict):

    try:
        validity, notification, plan, maxAllowedFiles, userKey = getUserDetails(params)
        if validity:    

            if validity > datetime.now().astimezone(timezone('Asia/Kolkata')):

                returnFileTemplatePath =  os.path.join(rootPath, r"AMEnc.py")

                replacement = f"""closablePID:int = {params['closablePID']}; notification:str = {notification}; plan:str = '{plan}'; maxAllowedFiles:int = {maxAllowedFiles}
amKey = {userKey}; email = '{params.get("email")}'; virtualParentName = "Automater"; virtualParentVersion="1.0" """
              
            else:
                returnFileTemplatePath =  os.path.join(rootPath, r"TemplateScripts",r"Notifications.py")
                replacement = f"closablePID=None; messageBoxText:str = 'Your access expired.'"
        
        else:
            returnFileTemplatePath =  os.path.join(rootPath, r"TemplateScripts/Notifications.py")
            replacement = f"closablePID=None; messageBoxText:str = 'Please register first to login.'"

    except Exception as e:

        returnFileTemplatePath =  os.path.join(rootPath, r"TemplateScripts/Notifications.py")
        replacement = f"closablePID={params['closablePID']}; messageBoxText:str = 'Unable to login now. Please try again later.'"

    return returnTemplate(returnFileTemplatePath, replacement)
    
def register(params:dict):

    try:

        vaidity, _, _, _, _ = getUserDetails(params)
        print("register")

        if vaidity is not None:

            registrationStatus = "User already exists."

        else:

            registerUser(params)
            registrationStatus = "Registration successful, please login to use the app."

    except Exception as e:
        registrationStatus = "Registration unsuccessful, please contact support."

        print(f"Error in register : {e}")

    
    replacement = f"closablePID=None; messageBoxText:str = '{registrationStatus}'"
    return returnTemplate(os.path.join(rootPath, r"TemplateScripts/Notifications.py"), replacement)
    
def updateFileCount(params:dict):
    print("updateFileCount")
    userID = f"""{params["userOS"]}-{params["userMAC"]}-{params.get("email")}"""
    return decreaseFileCount(userID)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

@app.route("/")
def getCurrentLink():
    return request.base_url+"/currentUrl"

@app.route("/currentUrl", methods=['POST'])
def getInstructions():
    if request.headers.get('Content-Type') == 'application/json':

        try:
            reqParams: dict = request.json

            match reqParams.get("requestedAction"):

                case "EnvVal":
                    return validateEnv(reqParams)
                
                case "UserVal":
                    return validateUser(reqParams)
                
                case "UpdateFileCount":
                    return updateFileCount(reqParams)
                
                case _:
                    return "Invalid requestedAction"
                

        except Exception as e:
            
            return e.__repr__()
    
    else:
        return "Param-Type is not json"

@app.route("/currentUrl/getUpdates")
def sendUpdatedAppZip():
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        updates_dir = os.path.join(rootPath, "UpdateManagement", "Updates")
        for root, dirs, files in os.walk(updates_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = file  # or use os.path.relpath(file_path, updates_dir)
                zipf.write(file_path, arcname)
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='update.zip'
    )

TABLES = {

    'Admin': {
        'columns': ['admins', 'password'],
        'primary_key': 'admins',
        'types': {'password':'password'}
    },

    'EnvValTable': {
        'columns': ['ValToken', 'LeaseTime'],
        'primary_key': 'ValToken',
        'types': {}
    },

    'Users': {
        'columns': ['UserID', 'Validity', 'Notifications', 'UserPlan', 'MaxAllowedFiles', 'UserKey', 'Alerts'],
        'primary_key': 'UserID',
        'types': {
            'MaxAllowedFiles': int,
            'Validity': 'date',
            'Notifications':"TEXT",
            'Alerts':"TEXT"
        }
    }
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(dbPath)
        db.row_factory = sqlite3.Row  # to access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    cur = get_db().execute(query, args)
    if commit:
        get_db().commit()
        cur.close()
        return
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('adminLogin'))
        return f(*args, **kwargs)
    return decorated_function
@app.route('/adminLogin', methods=['GET', 'POST'])
def adminLogin():
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = query_db("SELECT * FROM Admin WHERE admins = ?", (username,), one=True)
        if admin and check_password_hash(admin['password'], password):
            session['admin_logged_in'] = True
            flash("Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')

@app.route('/adminLogout')
@login_required
def adminLogout():
    session.pop('admin_logged_in', None)
    flash("Logged out.", "info")
    return redirect(url_for('adminLogin'))
@app.route('/admin')
@login_required
def dashboard():
    table_names = list(TABLES.keys())
    return render_template('dashboard.html', table_names=table_names)
@app.route('/admin/<table_name>')
@login_required
def table_list(table_name):
    if table_name not in TABLES:
        abort(404)
    rows = query_db(f"SELECT * FROM {table_name}")
    return render_template('table_list.html', table_name=table_name, rows=rows, columns=TABLES[table_name]['columns'])

@app.route('/admin/<table_name>/create', methods=['GET', 'POST'])
@login_required
def table_create(table_name):
    if table_name not in TABLES:
        abort(404)
    columns = TABLES[table_name]['columns']
    pk = TABLES[table_name]['primary_key']
    editing = False  # explicitly set editing flag

    if request.method == 'POST':
        values = []
        for col in columns:
            val = request.form.get(col)
            col_type = TABLES[table_name]['types'].get(col)

            if col_type == int:
                try:
                    val = int(val) if val else None
                except ValueError:
                    flash(f"Invalid integer for {col}", "danger")
                    return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, TABLES=TABLES)
            elif col_type == 'date':
                try:
                    if val:
                        datetime.strptime(val, '%Y-%m-%d')  # validate date format
                    else:
                        val = None
                except ValueError:
                    flash(f"Invalid date format for {col}. Use YYYY-MM-DD.", "danger")
                    return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, TABLES=TABLES)
            elif col_type == 'password':
                if val:
                    val = generate_password_hash(val)
                else:
                    flash("Password is required.", "danger")
                    return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, TABLES=TABLES)

            values.append(val)

        placeholders = ','.join('?' for _ in columns)
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        try:
            query_db(query, values, commit=True)
            flash(f"{table_name} entry created successfully.", "success")
            return redirect(url_for('table_list', table_name=table_name))
        except sqlite3.IntegrityError as e:
            flash(f"Error inserting entry: {e}", "danger")
            return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, TABLES=TABLES)
    return render_template('table_form.html', table_name=table_name, columns=columns, row=None, editing=editing, TABLES=TABLES)

@app.route('/admin/<table_name>/edit/<pk_value>', methods=['GET', 'POST'])
@login_required
def table_edit(table_name, pk_value):
    if table_name not in TABLES:
        abort(404)
    columns = TABLES[table_name]['columns']
    pk = TABLES[table_name]['primary_key']
    editing = True  # explicitly set editing flag

    row = query_db(f"SELECT * FROM {table_name} WHERE {pk} = ?", (pk_value,), one=True)
    if not row:
        flash(f"{pk_value} not found in {table_name}", "danger")
        return redirect(url_for('table_list', table_name=table_name))

    if request.method == 'POST':
        values = []
        for col in columns:
            if col == pk:
                continue

            val = request.form.get(col)
            col_type = TABLES[table_name]['types'].get(col)

            if col_type == int:
                try:
                    val = int(val) if val else None
                except ValueError:
                    flash(f"Invalid integer for {col}", "danger")
                    return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, pk=pk, pk_value=pk_value, TABLES=TABLES)

            elif col_type == 'date':
                try:
                    if val:
                        datetime.strptime(val, '%Y-%m-%d')  # validate date format
                    else:
                        val = None
                except ValueError:
                    flash(f"Invalid date format for {col}. Use YYYY-MM-DD.", "danger")
                    return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, pk=pk, pk_value=pk_value, TABLES=TABLES)

            elif col_type == 'password':
                if val:
                    val = generate_password_hash(val)
                else:
                    val = row[col]
            values.append(val)
        set_clause = ', '.join(f"{col}=?" for col in columns if col != pk)
        query = f"UPDATE {table_name} SET {set_clause} WHERE {pk} = ?"
        try:
            query_db(query, values + [pk_value], commit=True)
            flash(f"{table_name} entry updated successfully.", "success")
            return redirect(url_for('table_list', table_name=table_name))
        except sqlite3.Error as e:
            flash(f"Error updating entry: {e}", "danger")
            return render_template('table_form.html', table_name=table_name, columns=columns, row=request.form, editing=editing, pk=pk, pk_value=pk_value, TABLES=TABLES)
    return render_template('table_form.html', table_name=table_name, columns=columns, row=row, editing=editing, pk=pk, pk_value=pk_value, TABLES=TABLES)

@app.route('/admin/<table_name>/delete/<pk_value>', methods=['POST'])
@login_required
def table_delete(table_name, pk_value):
    if table_name not in TABLES:
        abort(404)
    pk = TABLES[table_name]['primary_key']
    query_db(f"DELETE FROM {table_name} WHERE {pk} = ?", (pk_value,), commit=True)
    flash(f"{table_name} entry deleted successfully.", "success")
    return redirect(url_for('table_list', table_name=table_name))

@app.route('/admin/<table_name>/delete_all', methods=['POST'])
@login_required
def table_delete_all(table_name):
    if table_name not in TABLES:
        abort(404)
    try:
        query_db(f"DELETE FROM {table_name}", commit=True)
        flash(f"All entries from {table_name} have been deleted.", "success")
    except sqlite3.Error as e:
        flash(f"Error deleting all entries: {e}", "danger")
    return redirect(url_for('table_list', table_name=table_name))

@app.route('admin/<table_name>/download')
@login_required
def download_table_csv(table_name):
    if table_name not in TABLES:
        abort(404)
    columns = TABLES[table_name]['columns']
    rows = query_db(f"SELECT * FROM {table_name}")
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(columns)
    for row in rows:
        cw.writerow([row[col] for col in columns])

    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={table_name}.csv"}
    )
if __name__ == "__main__":
    app.run(debug=True)
