from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto en producción

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
        flash('Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
    except sqlite3.IntegrityError:
        flash('El nombre de usuario ya existe.')
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
    app.run(debug=True)