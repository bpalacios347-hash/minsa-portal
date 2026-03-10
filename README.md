# Portal Médico MINSA Nicaragua

Proyecto de portal médico con registro y login de usuarios.

## Instalación

1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar la aplicación: `python app.py`
3. Abrir en navegador: http://127.0.0.1:5000/

## Funcionalidades

- Registro de nuevos usuarios con información personal.
- Inicio de sesión con número de expediente y contraseña.
- Página de bienvenida después del login.
- Almacenamiento de usuarios en base de datos SQLite.

## Estructura

- `app.py`: Servidor Flask con rutas y lógica.
- `templates/`: Plantillas HTML.
- `users.db`: Base de datos SQLite (creada automáticamente).
