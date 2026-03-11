from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import secrets

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Database config
db_url = os.environ.get('DATABASE_URL')
if db_url and HAS_PSYCOPG2:
    db_type = 'postgres'
else:
    db_type = 'sqlite'

def get_conn():
    global db_type
    if db_type == 'postgres':
        try:
            return psycopg2.connect(db_url)
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}. Falling back to SQLite.")
            db_type = 'sqlite'
            return sqlite3.connect('users.db')
    else:
        return sqlite3.connect('users.db')
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción

# Configuración de sesiones persistentes
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Configuración de Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1jExxsuOZIecLZmjw4OaSEJdPwm34fjXLH-f2z59VDU0"

CHRONIC_DISEASES = [
    "Diabetes Mellitus Tipo 2",
    "Hipertensión Arterial",
    "Asma Bronquial",
    "Artritis Reumatoide",
    "Enfermedad Pulmonar Obstructiva Crónica (EPOC)",
    "Insuficiencia Cardiaca",
    "Osteoporosis",
    "Enfermedad Renal Crónica",
    "Depresión Mayor",
    "Esclerosis Múltiple"
]

VIRAL_DISEASES = [
    "Influenza",
    "COVID-19",
    "Hepatitis B",
    "Hepatitis C",
    "Varicela",
    "Sarampión",
    "Paperas",
    "Rubeola",
    "Dengue",
    "Zika"
]

def get_sheet():
    # Leer de variable de entorno (para Render)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS no configurada")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    # Agregar encabezados si la sheet está vacía
    if sheet.row_count == 0:
        sheet.append_row(["Expediente", "Nombre", "Dirección", "Teléfono", "Ciudad", "Enfermedad Crónica", "Enfermedad Viral", "Fecha de Tratamiento"])
    return sheet

# Crear base de datos si no existe
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, address TEXT, phone TEXT, city TEXT, chronic_disease TEXT, viral_disease TEXT, treatment_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id SERIAL PRIMARY KEY, user_id INTEGER, token TEXT UNIQUE, expires_at TEXT)''')
    # Add new columns if not exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN chronic_disease TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN viral_disease TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN treatment_date TEXT")
    except:
        pass
    conn.commit()
    conn.close()

init_db()

def check_token():
    token = request.cookies.get('session_token')
    if token:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, expires_at FROM sessions WHERE token = %s", (token,))
        session_data = c.fetchone()
        conn.close()
        if session_data:
            user_id, expires_at_str = session_data
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() < expires_at:
                # Set session
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
                user = c.fetchone()
                conn.close()
                if user:
                    session['username'] = user[0]
                    return True
    return False

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('welcome'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    city = request.form['city']
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Generate random diseases and date
    chronic = random.choice(CHRONIC_DISEASES)
    viral = random.choice(VIRAL_DISEASES)
    start_date = datetime(2020, 1, 1)
    end_date = datetime.now()
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    treatment_date = random_date.strftime("%d/%m/%Y")

    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, name, address, phone, city, chronic_disease, viral_disease, treatment_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (username, hashed_password, name, address, phone, city, chronic, viral, treatment_date))
        conn.commit()
        # Guardar en Google Sheets
        try:
            sheet = get_sheet()
            sheet.append_row([username, name, address, phone, city, chronic, viral, treatment_date])
        except Exception as e:
            print(f"Error saving to Sheets: {e}")
        flash('Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
    except:
        flash('El nombre de usuario ya existe.')
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        user_id = user[0]
        session['username'] = username
        session.permanent = True
        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (%s, %s, %s)", (user_id, token, expires_at.isoformat()))
        conn.commit()
        conn.close()
        resp = redirect(url_for('welcome'))
        resp.set_cookie('session_token', token, max_age=30*24*3600, httponly=True)
        return resp
    else:
        flash('Nombre de usuario o contraseña incorrectos.')
        return redirect(url_for('home'))

@app.route('/welcome')
def welcome():
    if 'username' not in session:
        if not check_token():
            return redirect(url_for('home'))
    if 'username' in session:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT name, address, phone, city, chronic_disease, viral_disease, treatment_date FROM users WHERE username = %s", (session['username'],))
        user_data = c.fetchone()
        conn.close()
        if user_data:
            name, address, phone, city, chronic_disease, viral_disease, treatment_date = user_data
            return render_template('welcome.html', username=session['username'], name=name, address=address, phone=phone, city=city, chronic_disease=chronic_disease, viral_disease=viral_disease, treatment_date=treatment_date)
        else:
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    token = request.cookies.get('session_token')
    if token:
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()
        conn.close()
    session.pop('username', None)
    resp = redirect(url_for('home'))
    resp.set_cookie('session_token', '', max_age=0)
    return resp

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)