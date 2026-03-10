from pyngrok import ngrok

# Inicia el túnel en el puerto 5000
public_url = ngrok.connect(5000)
print(f"Tu aplicación está disponible en: {public_url}")

# Mantén el túnel abierto
ngrok_process = ngrok.get_ngrok_process()
try:
    ngrok_process.proc.wait()
except KeyboardInterrupt:
    print("Cerrando túnel...")
    ngrok.kill()