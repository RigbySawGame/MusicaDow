import os
import sys
import re
import uuid
import shutil
import zipfile
import threading
import static_ffmpeg
import yt_dlp

from backend.services.metadata_service import (
    search_official_metadata,
    get_processed_cover_bytes,
    apply_metadata_to_file,
    clean_song_title
)

# Asegurar que los binarios de FFmpeg estén disponibles en PATH tanto en desarrollo como en ejecutable compilado
def init_ffmpeg():
    if getattr(sys, "frozen", False):
        bundle_bin = os.path.join(sys._MEIPASS, "static_ffmpeg", "bin", "win32")
        if os.path.exists(bundle_bin):
            os.environ["PATH"] = bundle_bin + os.pathsep + os.environ.get("PATH", "")
    try:
        static_ffmpeg.add_paths()
    except Exception as e:
        print(f"Advertencia al inicializar static_ffmpeg: {e}")

init_ffmpeg()

# Detectar ruta de Node.js para resolver desafíos JS de YouTube (EJS)
NODE_PATH = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"

def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOWNLOADS_DIR = os.path.join(get_app_dir(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Diccionario para almacenar el progreso de las tareas
tasks_progress = {}

def is_playlist_url(url: str) -> bool:
    """Detecta si la URL corresponde a una lista de reproducción real."""
    if not url:
        return False
    url = url.strip()
    if "playlist?list=" in url:
        return True
    if "list=" in url and "list=RD" not in url and "list=UL" not in url:
        return True
    return False

def clean_youtube_url(url: str, force_playlist: bool = False) -> str:
    """Limpia parámetros innecesarios según si es playlist o video individual."""
    if not url:
        return url
    url = url.strip()

    if force_playlist or "playlist?list=" in url or ("list=" in url and "watch?v=" not in url):
        match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
        if match:
            return f"https://www.youtube.com/playlist?list={match.group(1)}"
        return url

    if "watch?v=" in url:
        v_match = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
        if v_match:
            if force_playlist:
                l_match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
                if l_match:
                    return f"https://www.youtube.com/playlist?list={l_match.group(1)}"
            return f"https://www.youtube.com/watch?v={v_match.group(1)}"
    elif "youtu.be/" in url:
        v_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        if v_match:
            return f"https://www.youtube.com/watch?v={v_match.group(1)}"
    elif "shorts/" in url:
        v_match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
        if v_match:
            return f"https://www.youtube.com/watch?v={v_match.group(1)}"

    return url

def get_base_ydl_opts(is_playlist: bool = False):
    """Configuración base para eludir desafíos JS, listas infinitas y bot-checks de YouTube."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not is_playlist,
        "remote_components": ["ejs:github"],
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "mweb", "android", "ios"]
            }
        }
    }
    if NODE_PATH and os.path.exists(NODE_PATH):
        opts["js_runtimes"] = {
            "node": {
                "path": NODE_PATH
            }
        }
    return opts

def format_duration(seconds):
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

def get_video_info(url: str):
    """Obtiene metadatos del video o de la playlist sin descargar."""
    raw_url = url.strip()
    is_pl = is_playlist_url(raw_url)

    if is_pl:
        clean_url = clean_youtube_url(raw_url, force_playlist=True)
        ydl_opts = {
            **get_base_ydl_opts(is_playlist=True),
            "extract_flat": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            entries_raw = list(info.get("entries", []))
            valid_entries = [e for e in entries_raw if e and (e.get("id") or e.get("url"))]

            if not valid_entries:
                raise ValueError("La lista de reproducción está vacía o no es pública.")

            # Obtener thumbnail de la playlist o del primer video
            first_e = valid_entries[0]
            thumb = info.get("thumbnail")
            if not thumb:
                thumbs = first_e.get("thumbnails", [])
                thumb = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{first_e.get('id')}/hqdefault.jpg"

            # Formatear lista de canciones para la vista previa
            preview_tracks = []
            for i, e in enumerate(valid_entries[:15], 1):
                clean_title_str = clean_song_title(e.get("title", f"Pista {i}"))
                preview_tracks.append({
                    "index": i,
                    "title": clean_title_str or e.get("title", f"Pista {i}"),
                    "duration": format_duration(e.get("duration")),
                    "id": e.get("id")
                })

            return {
                "is_playlist": True,
                "id": info.get("id"),
                "title": info.get("title") or "Playlist de YouTube",
                "author": info.get("uploader") or info.get("channel") or "Varios Artistas",
                "track_count": len(valid_entries),
                "preview_tracks": preview_tracks,
                "thumbnail": thumb,
                "webpage_url": clean_url,
                "audio_formats": ["mp3", "m4a", "wav"],
                "audio_qualities": [
                    {"label": "320 kbps (Máxima calidad)", "value": "320"},
                    {"label": "256 kbps (Muy alta)", "value": "256"},
                    {"label": "192 kbps (Alta)", "value": "192"},
                    {"label": "128 kbps (Estándar)", "value": "128"},
                ],
                "available_resolutions": [1080, 720, 480, 360]
            }

    # Video individual
    clean_url = clean_youtube_url(raw_url, force_playlist=False)
    ydl_opts = {
        **get_base_ydl_opts(is_playlist=False),
        "skip_download": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=False)
        if "_type" in info and info["_type"] == "playlist":
            entries = list(info.get("entries", []))
            if not entries:
                raise ValueError("No se encontraron videos en el enlace")
            info = entries[0]

        video_resolutions = set()
        if "formats" in info:
            for f in info["formats"]:
                h = f.get("height")
                if h and f.get("vcodec") != "none":
                    video_resolutions.add(h)

        sorted_resolutions = sorted(list(video_resolutions), reverse=True)
        common_resolutions = [r for r in [2160, 1440, 1080, 720, 480, 360] if r in sorted_resolutions]
        if not common_resolutions and sorted_resolutions:
            common_resolutions = sorted_resolutions[:4]

        # Buscar metadatos oficiales (Álbum, Artista, Carátula Oficial, Año, etc.)
        raw_title = info.get("title", "Sin título")
        uploader = info.get("uploader") or info.get("channel", "Desconocido")
        official_meta = search_official_metadata(raw_title=raw_title, uploader=uploader, yt_info=info)

        return {
            "is_playlist": False,
            "id": info.get("id"),
            "title": info.get("title", "Sin título"),
            "author": uploader,
            "duration": info.get("duration", 0),
            "duration_string": format_duration(info.get("duration", 0)),
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url", clean_url),
            "views": info.get("view_count", 0),
            "available_resolutions": common_resolutions if common_resolutions else [720, 480, 360],
            "audio_formats": ["mp3", "m4a", "wav"],
            "audio_qualities": [
                {"label": "320 kbps (Máxima calidad)", "value": "320"},
                {"label": "256 kbps (Muy alta)", "value": "256"},
                {"label": "192 kbps (Alta)", "value": "192"},
                {"label": "128 kbps (Estándar)", "value": "128"},
            ],
            "official_metadata": official_meta
        }

def search_youtube(query: str, limit: int = 6):
    """Busca videos en YouTube por término de búsqueda."""
    ydl_opts = {
        **get_base_ydl_opts(is_playlist=False),
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_result = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = search_result.get("entries", [])
        results = []
        for entry in entries:
            if not entry:
                continue
            results.append({
                "id": entry.get("id"),
                "title": entry.get("title", "Sin título"),
                "author": entry.get("uploader") or entry.get("channel", "Desconocido"),
                "duration": entry.get("duration", 0),
                "duration_string": format_duration(entry.get("duration", 0)),
                "thumbnail": entry.get("thumbnails")[-1].get("url") if entry.get("thumbnails") else f"https://i.ytimg.com/vi/{entry.get('id')}/hqdefault.jpg",
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}"
            })
        return results

def make_progress_hook(task_id: str, track_index: int = 1, total_tracks: int = 1):
    def hook(d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            percentage = 0
            if total_bytes > 0:
                percentage = round((downloaded / total_bytes) * 100, 1)

            speed = d.get("speed")
            speed_str = f"{round(speed / 1024 / 1024, 2)} MB/s" if speed else "Calculando..."
            eta = d.get("eta")
            eta_str = f"{eta}s" if eta is not None else "--"

            if total_tracks > 1:
                overall = round(((track_index - 1) / total_tracks * 100) + (percentage / total_tracks), 1)
                step = f"Pista {track_index} de {total_tracks} ({percentage}%)"
            else:
                overall = percentage
                step = "Descargando stream..."

            tasks_progress[task_id] = {
                "status": "downloading",
                "progress": overall,
                "speed": speed_str,
                "eta": eta_str,
                "step": step,
                "track_index": track_index,
                "total_tracks": total_tracks
            }
        elif d["status"] == "finished":
            if total_tracks > 1:
                step = f"Pista {track_index} de {total_tracks}: Convirtiendo e incrustando metadatos..."
                overall = round(((track_index - 1 + 0.95) / total_tracks) * 100, 1)
            else:
                step = "Convirtiendo formato e incrustando carátula oficial..."
                overall = 95

            tasks_progress[task_id] = {
                "status": "processing",
                "progress": overall,
                "speed": "",
                "eta": "",
                "step": step,
                "track_index": track_index,
                "total_tracks": total_tracks
            }
    return hook

def start_download_task(
    task_id: str,
    url: str,
    media_type: str,
    quality: str,
    audio_format: str = "mp3",
    custom_metadata: dict = None
):
    """Inicia la descarga de un video individual en segundo plano e incrusta metadatos y carátula oficial."""
    clean_url = clean_youtube_url(url, force_playlist=False)

    def run():
        try:
            tasks_progress[task_id] = {
                "status": "starting",
                "progress": 5,
                "step": "Iniciando descarga...",
                "file_path": None,
                "filename": None,
                "error": None
            }

            filename_template = f"{task_id}_raw_%(title)s.%(ext)s"
            outtmpl = os.path.join(DOWNLOADS_DIR, filename_template)

            hook = make_progress_hook(task_id, 1, 1)
            base_opts = get_base_ydl_opts(is_playlist=False)

            if media_type == "audio":
                bitrate = quality if quality in ["320", "256", "192", "128"] else "192"
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "progress_hooks": [hook],
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": audio_format if audio_format in ["mp3", "m4a", "wav", "opus"] else "mp3",
                            "preferredquality": bitrate,
                        },
                        {
                            "key": "FFmpegMetadata",
                            "add_metadata": True,
                        }
                    ],
                }
            else:
                res = quality if quality.isdigit() else "1080"
                ydl_opts = {
                    **base_opts,
                    "format": f"bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best[height<={res}]/best",
                    "outtmpl": outtmpl,
                    "progress_hooks": [hook],
                    "merge_output_format": "mp4",
                    "postprocessors": [
                        {
                            "key": "FFmpegMetadata",
                            "add_metadata": True,
                        }
                    ],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                raw_title = info.get("title", "audio_video")
                uploader = info.get("uploader") or info.get("channel", "")

                ext = audio_format if media_type == "audio" else "mp4"
                final_filename = None
                for fname in os.listdir(DOWNLOADS_DIR):
                    if fname.startswith(f"{task_id}_raw_"):
                        final_filename = fname
                        break

                if not final_filename:
                    raise FileNotFoundError("No se encontró el archivo generado tras la conversión.")

                final_path = os.path.join(DOWNLOADS_DIR, final_filename)

                # Resolver metadatos oficiales y carátula oficial
                tasks_progress[task_id]["status"] = "processing"
                tasks_progress[task_id]["step"] = "Incrustando carátula oficial y metadatos de álbum..."
                tasks_progress[task_id]["progress"] = 96

                meta = dict(custom_metadata) if custom_metadata else {}
                # Si no se aportaron metadatos manuales completos, buscar metadatos oficiales
                if not meta.get("title") or not meta.get("artist") or not meta.get("album"):
                    fetched = search_official_metadata(raw_title=raw_title, uploader=uploader, yt_info=info)
                    for k, v in fetched.items():
                        if not meta.get(k):
                            meta[k] = v

                # Obtener bytes de la carátula oficial en alta definición
                cover_url = meta.get("cover_url")
                fallback_thumb = info.get("thumbnail")
                cover_bytes = get_processed_cover_bytes(cover_url=cover_url, fallback_thumbnail_url=fallback_thumb)

                # Incrustar en el archivo (ID3v2.3 en MP3, MP4 Tags en M4A/MP4, etc.)
                apply_metadata_to_file(final_path, meta, cover_bytes=cover_bytes)

                # Renombrar archivo a formato limpio: "{task_id}_{Artista} - {Canción}.{ext}"
                clean_artist = sanitize_filename(meta.get("artist") or uploader or "Musica")
                clean_name = sanitize_filename(meta.get("title") or clean_song_title(raw_title) or "Pista")
                new_filename = f"{task_id}_{clean_artist} - {clean_name}.{ext}"
                new_path = os.path.join(DOWNLOADS_DIR, new_filename)

                if new_path != final_path:
                    try:
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.replace(final_path, new_path)
                        final_path = new_path
                        final_filename = new_filename
                    except Exception as ren_err:
                        print(f"Aviso al renombrar archivo: {ren_err}")

                display_title = f"{meta.get('artist')} - {meta.get('title')}" if meta.get("artist") and meta.get("title") else raw_title

                tasks_progress[task_id] = {
                    "status": "completed",
                    "progress": 100,
                    "step": "¡Completado con carátula oficial y metadatos de álbum! Listo para descargar.",
                    "file_path": final_path,
                    "filename": final_filename,
                    "title": display_title,
                    "artist": meta.get("artist"),
                    "album": meta.get("album"),
                    "extension": ext,
                    "size_mb": round(os.path.getsize(final_path) / (1024 * 1024), 2),
                    "metadata": meta,
                    "has_cover": bool(cover_bytes),
                    "error": None
                }

        except Exception as e:
            tasks_progress[task_id] = {
                "status": "error",
                "progress": 0,
                "step": f"Error: {str(e)}",
                "error": str(e)
            }

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

def start_playlist_download_task(
    task_id: str,
    url: str,
    media_type: str,
    quality: str,
    audio_format: str = "mp3"
):
    """Inicia la descarga de una playlist completa, incrusta metadatos y carátula a cada canción y comprime en ZIP."""
    clean_url = clean_youtube_url(url, force_playlist=True)

    def run():
        task_dir = os.path.join(DOWNLOADS_DIR, f"{task_id}_dir")
        try:
            os.makedirs(task_dir, exist_ok=True)

            tasks_progress[task_id] = {
                "status": "starting",
                "progress": 2,
                "step": "Obteniendo lista de canciones de la playlist...",
                "file_path": None,
                "filename": None,
                "error": None,
                "is_playlist": True
            }

            # 1. Obtener lista de videos con extract_flat
            base_opts = get_base_ydl_opts(is_playlist=True)
            with yt_dlp.YoutubeDL({**base_opts, "extract_flat": True, "skip_download": True}) as ydl:
                pl_info = ydl.extract_info(clean_url, download=False)
                entries = [e for e in pl_info.get("entries", []) if e and (e.get("id") or e.get("url"))]

            if not entries:
                raise ValueError("No se encontraron videos en la lista de reproducción.")

            total_tracks = len(entries)
            pl_title = sanitize_filename(pl_info.get("title") or "Playlist")
            tasks_progress[task_id]["total_tracks"] = total_tracks

            # 2. Descargar e incrustar metadatos a cada pista
            ext = audio_format if media_type == "audio" else "mp4"

            for index, entry in enumerate(entries, 1):
                track_id = entry.get("id")
                track_url = entry.get("url") if entry.get("url", "").startswith("http") else f"https://www.youtube.com/watch?v={track_id}"
                track_title = sanitize_filename(entry.get("title") or f"Pista_{index}")

                hook = make_progress_hook(task_id, index, total_tracks)
                raw_track_prefix = f"track_{index:03d}_"
                outtmpl = os.path.join(task_dir, f"{raw_track_prefix}%(title)s.%(ext)s")

                track_base_opts = get_base_ydl_opts(is_playlist=False)

                if media_type == "audio":
                    bitrate = quality if quality in ["320", "256", "192", "128"] else "192"
                    track_opts = {
                        **track_base_opts,
                        "format": "bestaudio/best",
                        "outtmpl": outtmpl,
                        "progress_hooks": [hook],
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": audio_format if audio_format in ["mp3", "m4a", "wav", "opus"] else "mp3",
                                "preferredquality": bitrate,
                            },
                            {
                                "key": "FFmpegMetadata",
                                "add_metadata": True,
                            }
                        ],
                    }
                else:
                    res = quality if quality.isdigit() else "1080"
                    track_opts = {
                        **track_base_opts,
                        "format": f"bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best[height<={res}]/best",
                        "outtmpl": outtmpl,
                        "progress_hooks": [hook],
                        "merge_output_format": "mp4",
                        "postprocessors": [
                            {
                                "key": "FFmpegMetadata",
                                "add_metadata": True,
                            }
                        ],
                    }

                try:
                    with yt_dlp.YoutubeDL(track_opts) as ydl:
                        track_info = ydl.extract_info(track_url, download=True)

                    # Buscar el archivo descargado para esta pista
                    downloaded_track_file = None
                    for f in os.listdir(task_dir):
                        if f.startswith(raw_track_prefix):
                            downloaded_track_file = os.path.join(task_dir, f)
                            break

                    if downloaded_track_file and os.path.exists(downloaded_track_file):
                        # Buscar metadatos oficiales y carátula para esta canción
                        meta = search_official_metadata(
                            raw_title=track_info.get("title") or entry.get("title", f"Pista {index}"),
                            uploader=track_info.get("uploader") or entry.get("uploader", ""),
                            yt_info=track_info
                        )
                        meta["track_number"] = index

                        cover_bytes = get_processed_cover_bytes(
                            cover_url=meta.get("cover_url"),
                            fallback_thumbnail_url=track_info.get("thumbnail") or entry.get("thumbnail")
                        )

                        # Incrustar metadatos y carátula oficial
                        apply_metadata_to_file(downloaded_track_file, meta, cover_bytes=cover_bytes)

                        # Renombrar dentro de la carpeta con nombre limpio numerado
                        clean_artist = sanitize_filename(meta.get("artist") or "Artista")
                        clean_song = sanitize_filename(meta.get("title") or track_title)
                        clean_filename = f"{index:02d}. {clean_artist} - {clean_song}.{ext}"
                        clean_path = os.path.join(task_dir, clean_filename)

                        if clean_path != downloaded_track_file:
                            if os.path.exists(clean_path):
                                os.remove(clean_path)
                            os.replace(downloaded_track_file, clean_path)

                except Exception as track_err:
                    print(f"[Playlist] Error en pista {index} ({track_title}): {track_err}")

            # 3. Comprimir todos los archivos en un ZIP
            tasks_progress[task_id]["status"] = "processing"
            tasks_progress[task_id]["step"] = "Comprimiendo pistas con metadatos oficiales en archivo .ZIP..."
            tasks_progress[task_id]["progress"] = 98

            zip_filename = f"{task_id}_{pl_title}.zip"
            zip_path = os.path.join(DOWNLOADS_DIR, zip_filename)

            files_to_zip = [f for f in os.listdir(task_dir) if os.path.isfile(os.path.join(task_dir, f))]
            if not files_to_zip:
                raise FileNotFoundError("No se pudo descargar ninguna de las pistas de la playlist.")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_name in sorted(files_to_zip):
                    file_full_path = os.path.join(task_dir, file_name)
                    zipf.write(file_full_path, arcname=file_name)

            # 4. Eliminar directorio temporal
            shutil.rmtree(task_dir, ignore_errors=True)

            size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)

            tasks_progress[task_id] = {
                "status": "completed",
                "progress": 100,
                "step": f"¡Playlist completada! {len(files_to_zip)} pistas con carátula y metadatos de álbum en archivo .ZIP.",
                "file_path": zip_path,
                "filename": zip_filename,
                "title": pl_title,
                "extension": "zip",
                "size_mb": size_mb,
                "is_playlist": True,
                "tracks_count": len(files_to_zip),
                "error": None
            }

        except Exception as e:
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir, ignore_errors=True)

            tasks_progress[task_id] = {
                "status": "error",
                "progress": 0,
                "step": f"Error en la playlist: {str(e)}",
                "error": str(e)
            }

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
