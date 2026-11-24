# 🎵 MusicaDow

Aplicación web moderna y rápida para buscar y descargar música (MP3, M4A, WAV) y videos (MP4 en hasta 1080p Full HD) de YouTube.

---

## 📥 Descargas (Releases)

Puedes descargar la versión lista para usar en Windows sin necesidad de instalar Python:

- ⬇️ **[Descargar MusicaDow.exe (Última versión)](https://github.com/RigbySawGame/MusicaDow/releases/latest/download/MusicaDow.exe)**
- 📦 **[Ver todas las versiones (GitHub Releases)](https://github.com/RigbySawGame/MusicaDow/releases)**

> **Nota:** Solo descarga `MusicaDow.exe` y ejecútalo directamente.

---

## 🚀 Características

- 🎧 **Música en Ultra Alta Calidad**: Conversión directa a MP3 hasta 320 kbps con carátula e información ID3.
- 🎬 **Video en Alta Definición**: Descarga videos en MP4 en resolución 1080p, 720p, 480p o 360p.
- 🔍 **Búsqueda Integrada**: Pega una URL de YouTube o escribe el nombre de la canción/artista directamente.
- ⚡ **FFmpeg Embebido**: Sin necesidad de instalar o configurar programas externos en Windows.
- 📊 **Progreso en Tiempo Real**: Visualización de porcentaje, velocidad de descarga y tiempo restante.
- 🕒 **Historial de Descargas**: Acceso rápido a las descargas de la sesión.
- 🧹 **Limpieza Automática**: Borrado inteligente de archivos temporales.

---

## 📦 Estructura del Proyecto

```
MusicaDow/
│
├── backend/
│   ├── main.py                  # API FastAPI y servidor web
│   ├── requirements.txt         # Dependencias Python
│   ├── services/
│   │   ├── ytdl_service.py      # Motor de extracción y descarga con yt-dlp
│   │   └── cleanup_service.py   # Servicio de limpieza de archivos temporales
│   └── downloads/               # Directorio temporal de archivos procesados
│
├── frontend/
│   ├── index.html               # Interfaz de usuario (HTML5 + Tailwind CSS)
│   ├── css/
│   │   └── style.css            # Estilos personalizados y animaciones
│   └── js/
│       └── app.js               # Lógica cliente y consumo de la API
│
├── run.bat                      # Script de inicio rápido en 1 clic (Windows)
└── README.md                    # Documentación del proyecto
```

---

## 🛠️ Cómo Iniciar la Aplicación

### Método 1: Un solo clic (Recomendado)
Haz doble clic sobre el archivo **`run.bat`**.
Esto creará el entorno virtual si no existe, instalará las dependencias necesarias y abrirá automáticamente la aplicación en tu navegador (`http://localhost:8000`).

### Método 2: Desde la terminal
1. Activa el entorno virtual:
   ```powershell
   .\venv\Scripts\activate
   ```
2. Inicia el servidor:
   ```powershell
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
3. Abre tu navegador en [http://localhost:8000](http://localhost:8000).

---

## 📋 Requisitos
- Windows 10 / 11
- Python 3.10 o superior instalado
- Conexión a Internet
