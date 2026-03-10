from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción

# Configuración de Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1jExxsuOZIecLZmjw4OaSEJdPwm34fjXLH-f2z59VDU0"

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
        sheet.append_row(["Expediente", "Nombre", "Dirección", "Teléfono", "Ciudad"])
    return sheet

# Crear base de datos si no existe
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, address TEXT, phone TEXT, city TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
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

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, name, address, phone, city) VALUES (?, ?, ?, ?, ?, ?)", (username, hashed_password, name, address, phone, city))
        conn.commit()
        # Guardar en Google Sheets
        try:
            sheet = get_sheet()
            sheet.append_row([username, name, address, phone, city])
        except Exception as e:
            print(f"Error saving to Sheets: {e}")
        flash('Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
    except sqlite3.IntegrityError:
        flash('El nombre de usuario ya existe.')
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
        session['username'] = username
        return redirect(url_for('welcome'))
    else:
        flash('Nombre de usuario o contraseña incorrectos.')
        return redirect(url_for('home'))

@app.route('/welcome')
def welcome():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name, address, phone, city FROM users WHERE username = ?", (session['username'],))
        user_data = c.fetchone()
        conn.close()
        if user_data:
            name, address, phone, city = user_data
            return render_template('welcome.html', username=session['username'], name=name, address=address, phone=phone, city=city)
        else:
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)