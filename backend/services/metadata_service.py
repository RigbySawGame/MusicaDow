import os
import re
import io
import urllib.parse
import requests
from PIL import Image
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, APIC, error as ID3Error
from mutagen.mp4 import MP4, MP4Cover
from mutagen.wave import WAVE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def clean_song_title(title: str) -> str:
    """Elimina ruidos comunes de YouTube como '(Official Music Video)', '[Audio]', etc."""
    if not title:
        return ""
    t = title

    # Patrones de texto entre paréntesis o corchetes que no son parte del título real
    bracket_patterns = [
        r'\[\s*(official\s*(music\s*)?video|video\s*oficial|audio\s*oficial|official\s*audio|lyric\s*video|letra|lyrics?|visualizer|official\s*visualizer|audio|video|hd|4k|hq|remastered|remasterizado|videoclip|clip\s*oficial|prod\.?[^\]]*|en\s*vivo|live)\s*\]',
        r'\(\s*(official\s*(music\s*)?video|video\s*oficial|audio\s*oficial|official\s*audio|lyric\s*video|letra|lyrics?|visualizer|official\s*visualizer|audio|video|hd|4k|hq|remastered|remasterizado|videoclip|clip\s*oficial|prod\.?[^\)]*|en\s*vivo|live)\s*\)',
        r'\|\s*.*$',  # sufijos tras pleca como '| Official Video'
        r'#\w+',      # hashtags
    ]
    for p in bracket_patterns:
        t = re.sub(p, '', t, flags=re.IGNORECASE)

    # Limpiar frases sueltas al final o principio
    noise_phrases = [
        r'\b(official\s*(music\s*)?video|video\s*oficial|official\s*audio|audio\s*oficial|lyric\s*video|video\s*con\s*letra)\b',
        r'\b(remastered|remasterizado|4k|1080p|hd)\b'
    ]
    for p in noise_phrases:
        t = re.sub(p, '', t, flags=re.IGNORECASE)

    # Limpiar comillas, guiones sobrantes y espacios múltiples
    t = re.sub(r'[\"\'«»“”]', '', t)
    t = re.sub(r'\s+', ' ', t).strip(' -:|()[]')
    return t

def clean_artist_name(uploader: str) -> str:
    """Limpia el nombre del canal o autor de YouTube."""
    if not uploader:
        return ""
    name = uploader
    # Quitar sufijos de canales oficiales
    name = re.sub(r'\s*-\s*Topic$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'VEVO$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*(Official|Oficial|Music|Canal Oficial|Videos)$', '', name, flags=re.IGNORECASE)
    return name.strip(' -')

def parse_artist_and_title(raw_title: str, uploader: str = "") -> tuple[str, str]:
    """Intenta separar Artista y Título si están en formato 'Artista - Título'."""
    cleaned_title = clean_song_title(raw_title)
    cleaned_uploader = clean_artist_name(uploader)

    # Si contiene separador ' - ' o ' – ' o ' — '
    separator_match = re.search(r'\s+[-–—:]\s+', cleaned_title)
    if separator_match:
        parts = cleaned_title[:separator_match.start()], cleaned_title[separator_match.end():]
        artist_cand = parts[0].strip()
        title_cand = parts[1].strip()
        if artist_cand and title_cand:
            return artist_cand, title_cand

    # Si no tiene separador, usar el uploader como artista
    if cleaned_uploader:
        return cleaned_uploader, cleaned_title

    return "", cleaned_title

def search_official_metadata(raw_title: str, uploader: str = "", yt_info: dict = None) -> dict:
    """
    Busca metadatos oficiales (nombre, artista, álbum, carátula en alta definición, año, género)
    utilizando Deezer API, iTunes Search API y metadatos de YouTube Music como respaldo.
    """
    artist_cand, title_cand = parse_artist_and_title(raw_title, uploader)
    cleaned_full = clean_song_title(raw_title)
    cleaned_uploader = clean_artist_name(uploader)

    queries = []
    if artist_cand and title_cand:
        queries.append(f"{artist_cand} {title_cand}")
    if cleaned_full and cleaned_full != queries[0] if queries else True:
        queries.append(cleaned_full)
    if cleaned_uploader and cleaned_uploader.lower() not in cleaned_full.lower():
        queries.append(f"{cleaned_uploader} {cleaned_full}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1. Intentar Deezer API
    for q in queries:
        try:
            r = session.get("https://api.deezer.com/search", params={"q": q, "limit": 3}, timeout=6)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    track = data[0]
                    track_id = track.get("id")
                    album_data = track.get("album", {})
                    artist_data = track.get("artist", {})

                    cover_url = album_data.get("cover_xl") or album_data.get("cover_big") or album_data.get("cover_medium")
                    release_year = ""
                    track_position = track.get("track_position")

                    # Consultar detalles del track para obtener año exacto y género si está disponible
                    if track_id:
                        try:
                            tr_detail = session.get(f"https://api.deezer.com/track/{track_id}", timeout=4).json()
                            release_date = tr_detail.get("release_date")
                            if release_date:
                                release_year = release_date.split("-")[0]
                            if not track_position:
                                track_position = tr_detail.get("track_position")
                        except Exception:
                            pass

                    return {
                        "found_official": True,
                        "source": "deezer",
                        "title": track.get("title") or title_cand,
                        "artist": artist_data.get("name") or artist_cand,
                        "album": album_data.get("title") or "Single",
                        "album_artist": artist_data.get("name") or artist_cand,
                        "cover_url": cover_url,
                        "year": release_year,
                        "genre": "",
                        "track_number": track_position,
                    }
        except Exception as e:
            print(f"[Deezer API] Advertencia al consultar '{q}': {e}")

    # 2. Intentar iTunes Search API
    for q in queries:
        try:
            r = session.get("https://itunes.apple.com/search", params={"term": q, "entity": "song", "limit": 3}, timeout=6)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    item = results[0]
                    raw_art = item.get("artworkUrl100", "")
                    # Reemplazar a máxima resolución (1000x1000)
                    high_res_art = raw_art.replace("100x100bb.jpg", "1000x1000bb.jpg") if raw_art else ""
                    rel_date = item.get("releaseDate", "")
                    year = rel_date[:4] if rel_date else ""

                    return {
                        "found_official": True,
                        "source": "itunes",
                        "title": item.get("trackName") or title_cand,
                        "artist": item.get("artistName") or artist_cand,
                        "album": item.get("collectionName") or "Single",
                        "album_artist": item.get("artistName") or artist_cand,
                        "cover_url": high_res_art,
                        "year": year,
                        "genre": item.get("primaryGenreName") or "",
                        "track_number": item.get("trackNumber"),
                    }
        except Exception as e:
            print(f"[iTunes API] Advertencia al consultar '{q}': {e}")

    # 3. Respaldo: Metadatos provistos por YouTube Music o yt-dlp
    yt_title = yt_info.get("track") if yt_info else None
    yt_artist = yt_info.get("artist") if yt_info else None
    yt_album = yt_info.get("album") if yt_info else None
    yt_year = yt_info.get("release_year") if yt_info else None
    yt_thumb = yt_info.get("thumbnail") if yt_info else None

    final_title = yt_title or title_cand or cleaned_full or "Canción"
    final_artist = yt_artist or artist_cand or cleaned_uploader or "Artista Desconocido"
    final_album = yt_album or "Single"
    final_year = str(yt_year) if yt_year else ""

    return {
        "found_official": bool(yt_title and yt_album),
        "source": "youtube_fallback",
        "title": final_title,
        "artist": final_artist,
        "album": final_album,
        "album_artist": final_artist,
        "cover_url": yt_thumb,
        "year": final_year,
        "genre": "",
        "track_number": 1,
    }

def get_processed_cover_bytes(cover_url: str, fallback_thumbnail_url: str = None) -> bytes:
    """
    Descarga la carátula oficial y la procesa en formato JPEG cuadrado de alta calidad.
    Si la imagen no es cuadrada (ej. miniatura de YouTube 16:9), la recorta centralmente a 1:1.
    """
    target_url = cover_url or fallback_thumbnail_url
    if not target_url:
        return None

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    img_data = None
    try:
        r = session.get(target_url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            img_data = r.content
    except Exception as e:
        print(f"[Cover] Error al descargar de {target_url}: {e}")

    # Si falló la principal y hay fallback
    if not img_data and fallback_thumbnail_url and fallback_thumbnail_url != target_url:
        try:
            r = session.get(fallback_thumbnail_url, timeout=10)
            if r.status_code == 200:
                img_data = r.content
        except Exception as e:
            print(f"[Cover] Error al descargar fallback {fallback_thumbnail_url}: {e}")

    if not img_data:
        return None

    try:
        img = Image.open(io.BytesIO(img_data))
        # Convertir a RGB (maneja PNGs con transparencia, RGBA, CMYK, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        # Si la imagen no es cuadrada (diferencia > 5%), recortar al centro a relación 1:1
        if abs(w - h) / max(w, h) > 0.05:
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))

        # Asegurar tamaño estándar de alta fidelidad (hasta 1000x1000)
        if img.width > 1200 or img.height > 1200:
            img = img.resize((1000, 1000), Image.Resampling.LANCZOS)

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="JPEG", quality=95)
        return out_buffer.getvalue()
    except Exception as e:
        print(f"[Cover] Error al procesar imagen con Pillow: {e}")
        return img_data

def apply_metadata_to_file(file_path: str, metadata: dict, cover_bytes: bytes = None):
    """
    Incrusta los metadatos completos y la carátula oficial en el archivo descargado.
    Soporta MP3 (ID3v2.3), M4A (MP4 Atoms), WAV y MP4 (Video).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    title = metadata.get("title") or "Canción"
    artist = metadata.get("artist") or "Artista Desconocido"
    album = metadata.get("album") or "Single"
    album_artist = metadata.get("album_artist") or artist
    year = str(metadata.get("year") or "")
    genre = metadata.get("genre") or ""
    track_num = metadata.get("track_number")

    track_str = str(track_num) if track_num else "1"

    # 1. MP3
    if ext == ".mp3":
        try:
            try:
                audio = MP3(file_path, ID3=ID3)
            except ID3Error:
                audio = MP3(file_path)
            if audio.tags is None:
                audio.add_tags()

            tags = audio.tags
            tags.setall("TIT2", [TIT2(encoding=3, text=title)])
            tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
            tags.setall("TALB", [TALB(encoding=3, text=album)])
            tags.setall("TPE2", [TPE2(encoding=3, text=album_artist)])
            if year:
                tags.setall("TDRC", [TDRC(encoding=3, text=year)])
            if genre:
                tags.setall("TCON", [TCON(encoding=3, text=genre)])
            if track_str:
                tags.setall("TRCK", [TRCK(encoding=3, text=track_str)])

            if cover_bytes:
                tags.delall("APIC")
                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,  # 3 es portada frontal (front cover)
                        desc="Cover",
                        data=cover_bytes
                    )
                )

            # Guardar con ID3v2.3 para compatibilidad absoluta con Windows Explorer y reproductores
            audio.save(v2_version=3)
            print(f"[Metadata] Metadatos y carátula incrustados en MP3: {file_path}")
        except Exception as e:
            print(f"[Metadata] Error al incrustar tags en MP3: {e}")

    # 2. M4A y MP4 (Video o Audio)
    elif ext in [".m4a", ".mp4"]:
        try:
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()

            audio["\xa9nam"] = [title]
            audio["\xa9ART"] = [artist]
            audio["\xa9alb"] = [album]
            audio["aART"] = [album_artist]
            if year:
                audio["\xa9day"] = [year]
            if genre:
                audio["\xa9gen"] = [genre]
            if track_num:
                try:
                    audio["trkn"] = [(int(track_num), 0)]
                except Exception:
                    pass

            if cover_bytes:
                audio["covr"] = [MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]

            audio.save()
            print(f"[Metadata] Metadatos y carátula incrustados en {ext.upper()}: {file_path}")
        except Exception as e:
            print(f"[Metadata] Error al incrustar tags en {ext.upper()}: {e}")

    # 3. WAV
    elif ext == ".wav":
        try:
            audio = WAVE(file_path)
            if audio.tags is None:
                audio.add_tags()

            tags = audio.tags
            tags.setall("TIT2", [TIT2(encoding=3, text=title)])
            tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
            tags.setall("TALB", [TALB(encoding=3, text=album)])
            if year:
                tags.setall("TDRC", [TDRC(encoding=3, text=year)])
            if cover_bytes:
                tags.delall("APIC")
                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=cover_bytes
                    )
                )
            audio.save()
            print(f"[Metadata] Metadatos incrustados en WAV: {file_path}")
        except Exception as e:
            print(f"[Metadata] Error al incrustar tags en WAV: {e}")
