import os
import time
import threading

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")

def cleanup_old_files(max_age_seconds: int = 1800):
    """Elimina archivos de la carpeta downloads que tengan más de max_age_seconds de antigüedad."""
    now = time.time()
    if not os.path.exists(DOWNLOADS_DIR):
        return

    for filename in os.listdir(DOWNLOADS_DIR):
        file_path = os.path.join(DOWNLOADS_DIR, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"[Cleanup] Eliminado archivo temporal antiguo: {filename}")
                except Exception as e:
                    print(f"[Cleanup] No se pudo eliminar {filename}: {e}")

def start_periodic_cleanup(interval_seconds: int = 600, max_age_seconds: int = 1800):
    """Inicia un ciclo en segundo plano para limpiar archivos periódicamente."""
    def loop():
        while True:
            time.sleep(interval_seconds)
            cleanup_old_files(max_age_seconds)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
