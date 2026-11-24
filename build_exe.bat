@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo        Compilando MusicaDow a Ejecutable (.EXE)
echo ========================================================
echo.

if not exist "venv\Scripts\pyinstaller.exe" (
    echo [1/3] Instalando PyInstaller en el entorno virtual...
    .\venv\Scripts\python.exe -m pip install pyinstaller
) else (
    echo [1/3] PyInstaller ya instalado.
)

echo.
echo [2/3] Generando ejecutable con PyInstaller...
echo Esto puede tomar entre 1 y 2 minutos mientras empaqueta librerias, ffmpeg y frontend...
echo.

.\venv\Scripts\pyinstaller.exe MusicaDow.spec --clean -y

if exist "dist\MusicaDow.exe" (
    echo.
    echo ========================================================
    echo      COMPILACION COMPLETADA CON EXITO!
    echo ========================================================
    echo.
    echo Tu ejecutable portatil esta listo en:
    echo   dist\MusicaDow.exe
    echo.
    echo Puedes mover 'MusicaDow.exe' a cualquier carpeta o USB.
    echo Al hacer doble clic, iniciara el servidor y abrira tu navegador automaticamente.
    echo ========================================================
) else (
    echo.
    echo [ERROR] Ocurrio un problema durante la compilacion.
)

pause
