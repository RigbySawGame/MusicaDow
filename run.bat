@echo off
cd /d "%~dp0"
echo ========================================================
echo               MusicaDow - Servidor Web
echo ========================================================
echo.
echo En tu PC abre:       http://localhost:8000
echo En tu Tablet/Movil:  http://192.168.18.2:8000
echo.
echo (Ambos dispositivos deben estar en el mismo Wi-Fi)
echo ========================================================
echo.
.\venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
