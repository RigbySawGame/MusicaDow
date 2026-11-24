import os
import sys
import time
import socket
import threading
import webbrowser

# Si se ejecuta como ejecutable empaquetado (PyInstaller)
if getattr(sys, "frozen", False):
    os.chdir(sys._MEIPASS)

import uvicorn
from backend.main import app

def is_port_in_use(port: int) -> bool:
    """Verifica si el puerto ya está ocupado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def open_browser(port: int):
    """Espera a que el servidor esté activo y abre el navegador automáticamente."""
    time.sleep(1.5)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 60)
    print("   MusicaDow Iniciado Correctamente!")
    print(f"   Abriendo tu navegador en: {url}")
    print("   (Para cerrar la aplicación, simplemente cierra esta ventana)")
    print("=" * 60 + "\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Aviso al abrir navegador: {e}")

def main():
    port = 8000
    if is_port_in_use(port):
        for p in range(8001, 8030):
            if not is_port_in_use(p):
                port = p
                break

    # Iniciar temporizador para abrir el navegador
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Ejecutar servidor FastAPI
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
