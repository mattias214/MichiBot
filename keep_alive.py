from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def inicio():
    return "¡MichiBot está vivo! 🐱"


def ejecutar():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    """Arranca un mini servidor web en un hilo aparte.
    Un servicio externo (UptimeRobot) le va a hacer 'ping' cada 5 minutos
    a esta URL para que el hosting gratuito no apague el bot por inactividad."""
    servidor = Thread(target=ejecutar)
    servidor.start()
