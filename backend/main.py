import os
import uuid
import urllib.parse
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend.services.ytdl_service import (
    get_video_info,
    search_youtube,
    start_download_task,
    start_playlist_download_task,
    tasks_progress,
    DOWNLOADS_DIR
)
from backend.services.cleanup_service import start_periodic_cleanup, cleanup_old_files

app = FastAPI(title="MusicaDow API", description="API para descargar música y videos de YouTube", version="1.0.0")

# Permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Iniciar servicio de limpieza en segundo plano
@app.on_event("startup")
async def startup_event():
    start_periodic_cleanup(interval_seconds=300, max_age_seconds=1800)

# Modelos de datos
class InfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    media_type: str = "audio"  # "audio" o "video"
    quality: str = "320"       # 320, 256, 192, 128 para audio; 1080, 720, 480, 360 para video
    audio_format: str = "mp3"  # mp3, m4a, wav
    is_playlist: bool = False  # True si se descarga la playlist completa en ZIP
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    cover_url: Optional[str] = None

@app.post("/api/info")
async def api_get_info(req: InfoRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Debe proporcionar una URL válida de YouTube.")
    try:
        info = get_video_info(req.url.strip())
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener información: {str(e)}")

@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), limit: int = Query(6, ge=1, le=15)):
    try:
        results = search_youtube(q, limit=limit)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en la búsqueda: {str(e)}")

@app.post("/api/download")
async def api_start_download(req: DownloadRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL requerida")
    
    task_id = str(uuid.uuid4())[:8]
    custom_meta = {
        "title": req.title,
        "artist": req.artist,
        "album": req.album,
        "year": req.year,
        "genre": req.genre,
        "cover_url": req.cover_url
    }
    custom_meta = {k: v.strip() for k, v in custom_meta.items() if v and v.strip()}

    if req.is_playlist:
        start_playlist_download_task(
            task_id=task_id,
            url=req.url.strip(),
            media_type=req.media_type,
            quality=req.quality,
            audio_format=req.audio_format
        )
    else:
        start_download_task(
            task_id=task_id,
            url=req.url.strip(),
            media_type=req.media_type,
            quality=req.quality,
            audio_format=req.audio_format,
            custom_metadata=custom_meta
        )
    return {"success": True, "task_id": task_id}

@app.get("/api/progress/{task_id}")
async def api_get_progress(task_id: str):
    if task_id not in tasks_progress:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o expirada.")
    return tasks_progress[task_id]

@app.get("/api/file/{filename}")
async def api_download_file(filename: str):
    # Asegurar que no haya path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOWNLOADS_DIR, safe_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="El archivo solicitado no existe o ya ha expirado.")

    # Remover el prefijo task_id para el nombre de descarga amigable
    display_name = safe_filename
    if "_" in safe_filename:
        display_name = safe_filename.split("_", 1)[1]

    # Codificar nombre para cabeceras HTTP de forma segura
    encoded_name = urllib.parse.quote(display_name)

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=display_name,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"}
    )

# Servir Frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "MusicaDow API activa. Interfaz web no encontrada."}

if __name__ == "__main__":
    import uvicorn
    print("Iniciando MusicaDow en http://127.0.0.1:8000 ...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
