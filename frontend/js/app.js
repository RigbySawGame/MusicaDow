// State Management
let currentMediaData = null;
let currentMediaType = 'audio'; // 'audio' | 'video'
let selectedAudioQuality = '320';
let selectedAudioFormat = 'mp3';
let selectedVideoQuality = '1080';
let pollInterval = null;

// DOM Elements
const searchForm = document.getElementById('search-form');
const urlInput = document.getElementById('url-input');
const btnPaste = document.getElementById('btn-paste');
const btnSearch = document.getElementById('btn-search');
const loader = document.getElementById('loader');
const loaderText = document.getElementById('loader-text');
const searchResultsSection = document.getElementById('search-results-section');
const searchResultsGrid = document.getElementById('search-results-grid');
const resultsCount = document.getElementById('results-count');
const mediaCard = document.getElementById('media-card');
const mediaBadgeContainer = document.getElementById('media-badge-container');
const mediaBadge = document.getElementById('media-badge');
const mediaBadgeText = document.getElementById('media-badge-text');
const mediaThumbnail = document.getElementById('media-thumbnail');
const mediaDuration = document.getElementById('media-duration');
const mediaTitle = document.getElementById('media-title');
const mediaAuthor = document.getElementById('media-author');
const playlistTracksBox = document.getElementById('playlist-tracks-box');
const btnToggleTracks = document.getElementById('btn-toggle-tracks');
const playlistTrackCount = document.getElementById('playlist-track-count');
const playlistTracksList = document.getElementById('playlist-tracks-list');
const playlistToggleIcon = document.getElementById('playlist-toggle-icon');
const tabAudio = document.getElementById('tab-audio');
const tabVideo = document.getElementById('tab-video');
const audioOptions = document.getElementById('audio-options');
const videoOptions = document.getElementById('video-options');
const videoQualityButtons = document.getElementById('video-quality-buttons');
const btnStartDownload = document.getElementById('btn-start-download');
const btnDownloadText = document.getElementById('btn-download-text');
const progressBox = document.getElementById('progress-box');
const progressBarFill = document.getElementById('progress-bar-fill');
const progressPercent = document.getElementById('progress-percent');
const progressSpeed = document.getElementById('progress-speed');
const progressStatusTitle = document.getElementById('progress-status-title');
const progressStatusStep = document.getElementById('progress-status-step');
const progressIcon = document.getElementById('progress-icon');
const progressCompletedActions = document.getElementById('progress-completed-actions');
const btnSaveFile = document.getElementById('btn-save-file');
const saveFileLabel = document.getElementById('save-file-label');
const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    setupQualityButtons();

    // Paste button support
    btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                showToast('Enlace pegado del portapapeles', 'info');
                if (isYouTubeUrl(text.trim())) {
                    fetchVideoInfo(text.trim());
                }
            }
        } catch (err) {
            showToast('No se pudo acceder al portapapeles. Pégalo manualmente con Ctrl+V.', 'error');
        }
    });

    // Form Submit
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const inputVal = urlInput.value.trim();
        if (!inputVal) return;

        if (isYouTubeUrl(inputVal)) {
            fetchVideoInfo(inputVal);
        } else {
            searchVideos(inputVal);
        }
    });

    // Toggle playlist tracks dropdown
    if (btnToggleTracks) {
        btnToggleTracks.addEventListener('click', () => {
            const isHidden = playlistTracksList.classList.contains('hidden');
            if (isHidden) {
                playlistTracksList.classList.remove('hidden');
                if (playlistToggleIcon) playlistToggleIcon.style.transform = 'rotate(180deg)';
            } else {
                playlistTracksList.classList.add('hidden');
                if (playlistToggleIcon) playlistToggleIcon.style.transform = 'rotate(0deg)';
            }
        });
    }

    // Format radio changes
    document.querySelectorAll('input[name="audio-format"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            selectedAudioFormat = e.target.value;
            updateDownloadButtonLabel();
        });
    });

    // Download Button Click
    btnStartDownload.addEventListener('click', triggerDownload);
});

function isYouTubeUrl(url) {
    return /^(https?:\/\/)?((www|m|music)\.)?(youtube\.com|youtu\.be)\/.+$/i.test(url);
}

// Show Toast Notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    
    let bgColors = 'bg-dark-800 border-slate-700 text-slate-200';
    let icon = '<i class="fa-solid fa-circle-info text-sky-400"></i>';

    if (type === 'error') {
        bgColors = 'bg-rose-950/90 border-rose-800/80 text-rose-200';
        icon = '<i class="fa-solid fa-circle-exclamation text-rose-400"></i>';
    } else if (type === 'success') {
        bgColors = 'bg-emerald-950/90 border-emerald-800/80 text-emerald-200';
        icon = '<i class="fa-solid fa-circle-check text-emerald-400"></i>';
    }

    toast.className = `toast flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-md text-sm ${bgColors}`;
    toast.innerHTML = `
        ${icon}
        <span class="flex-1">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// Fetch Video or Playlist Details
async function fetchVideoInfo(url) {
    showLoader(true, 'Analizando enlace de YouTube...');
    hideMediaCard();
    hideSearchResults();
    hideProgress();

    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Error al obtener información del video o playlist.');
        }

        currentMediaData = res.data;
        displayMediaCard(res.data);
    } catch (err) {
        const msg = err.message === 'Failed to fetch' 
            ? 'No se pudo conectar con el servidor. Asegúrate de que el servidor esté corriendo en la terminal.' 
            : err.message;
        showToast(msg, 'error');
    } finally {
        showLoader(false);
    }
}

// Search Videos
async function searchVideos(query) {
    showLoader(true, `Buscando "${query}" en YouTube...`);
    hideMediaCard();
    hideSearchResults();
    hideProgress();

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=6`);
        const res = await response.json();

        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Error al buscar videos.');
        }

        displaySearchResults(res.data);
    } catch (err) {
        const msg = err.message === 'Failed to fetch' 
            ? 'No se pudo conectar con el servidor. Asegúrate de que el servidor esté corriendo en la terminal.' 
            : err.message;
        showToast(msg, 'error');
    } finally {
        showLoader(false);
    }
}

// Display Search Results
function displaySearchResults(results) {
    if (!results || results.length === 0) {
        showToast('No se encontraron videos para tu búsqueda.', 'info');
        return;
    }

    searchResultsGrid.innerHTML = '';
    resultsCount.textContent = `${results.length} resultados`;

    results.forEach(video => {
        const card = document.createElement('div');
        card.className = 'bg-dark-800/80 hover:bg-dark-700/80 border border-slate-700/60 hover:border-brand-500/60 rounded-xl p-3 flex gap-3 cursor-pointer transition-all duration-200 group';
        card.innerHTML = `
            <div class="relative w-28 h-20 rounded-lg overflow-hidden shrink-0 bg-dark-900">
                <img src="${video.thumbnail}" alt="${video.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform">
                <span class="absolute bottom-1 right-1 bg-black/80 text-[10px] text-white px-1.5 py-0.2 rounded font-semibold">${video.duration_string}</span>
            </div>
            <div class="flex-1 flex flex-col justify-between overflow-hidden">
                <div>
                    <h4 class="text-xs sm:text-sm font-semibold text-white line-clamp-2 leading-tight group-hover:text-brand-300 transition-colors">${video.title}</h4>
                    <p class="text-[11px] text-slate-400 mt-1 truncate">${video.author}</p>
                </div>
                <button class="mt-2 text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center gap-1">
                    <span>Seleccionar</span> <i class="fa-solid fa-arrow-right text-[10px]"></i>
                </button>
            </div>
        `;

        card.addEventListener('click', () => {
            urlInput.value = video.url;
            fetchVideoInfo(video.url);
        });

        searchResultsGrid.appendChild(card);
    });

    searchResultsSection.classList.remove('hidden');
    searchResultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Display Media Card (Supports both Single Media and Playlist)
function displayMediaCard(data) {
    mediaThumbnail.src = data.thumbnail;
    mediaTitle.textContent = data.title;
    mediaAuthor.querySelector('span').textContent = data.author;

    // Manejar estado de Playlist vs Video Individual
    if (data.is_playlist) {
        if (mediaBadgeContainer) {
            mediaBadgeContainer.classList.remove('hidden');
            mediaBadgeText.textContent = `PLAYLIST (${data.track_count} CANCIONES)`;
        }
        mediaDuration.textContent = `${data.track_count} canciones`;

        // Renderizar lista previa de canciones
        if (playlistTracksBox) {
            playlistTracksBox.classList.remove('hidden');
            playlistTrackCount.textContent = data.track_count;
            playlistTracksList.innerHTML = '';
            
            (data.preview_tracks || []).forEach(track => {
                const item = document.createElement('div');
                item.className = 'flex items-center justify-between text-[11px] py-1 border-b border-slate-800/60 last:border-0';
                item.innerHTML = `
                    <span class="truncate pr-2 text-slate-300 font-medium">${track.index}. ${track.title}</span>
                    <span class="text-slate-500 shrink-0 font-mono">${track.duration}</span>
                `;
                playlistTracksList.appendChild(item);
            });

            if (data.track_count > 15) {
                const moreItem = document.createElement('div');
                moreItem.className = 'text-[10px] text-slate-500 italic text-center pt-1';
                moreItem.textContent = `... y ${data.track_count - 15} canciones más`;
                playlistTracksList.appendChild(moreItem);
            }
        }
    } else {
        if (mediaBadgeContainer) mediaBadgeContainer.classList.add('hidden');
        if (playlistTracksBox) playlistTracksBox.classList.add('hidden');
        mediaDuration.textContent = data.duration_string || '00:00';
    }

    // Render Video Quality Options
    videoQualityButtons.innerHTML = '';
    const resolutions = data.available_resolutions || [720, 480, 360];
    
    resolutions.forEach((res, index) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.dataset.resolution = res;
        btn.className = `quality-btn px-3 py-1.5 rounded-lg border text-xs font-semibold ${index === 0 ? 'active' : ''}`;
        
        let label = `${res}p`;
        if (res >= 1080) label += ' (Full HD)';
        else if (res >= 720) label += ' (HD)';

        btn.textContent = label;
        btn.addEventListener('click', () => {
            videoQualityButtons.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedVideoQuality = res.toString();
            updateDownloadButtonLabel();
        });

        videoQualityButtons.appendChild(btn);
    });

    selectedVideoQuality = resolutions[0] ? resolutions[0].toString() : '720';

    switchFormatTab('audio');
    mediaCard.classList.remove('hidden');
    mediaCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Switch between Audio and Video tabs
function switchFormatTab(type) {
    currentMediaType = type;

    if (type === 'audio') {
        tabAudio.className = 'tab-btn flex-1 pb-3 text-sm font-semibold flex items-center justify-center gap-2 border-b-2 border-brand-500 text-brand-400 transition';
        tabVideo.className = 'tab-btn flex-1 pb-3 text-sm font-semibold flex items-center justify-center gap-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
        audioOptions.classList.remove('hidden');
        videoOptions.classList.add('hidden');
    } else {
        tabVideo.className = 'tab-btn flex-1 pb-3 text-sm font-semibold flex items-center justify-center gap-2 border-b-2 border-brand-500 text-brand-400 transition';
        tabAudio.className = 'tab-btn flex-1 pb-3 text-sm font-semibold flex items-center justify-center gap-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
        videoOptions.classList.remove('hidden');
        audioOptions.classList.add('hidden');
    }

    updateDownloadButtonLabel();
}

function setupQualityButtons() {
    document.querySelectorAll('#audio-quality-buttons .quality-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#audio-quality-buttons .quality-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedAudioQuality = btn.dataset.quality;
            updateDownloadButtonLabel();
        });
    });
}

function updateDownloadButtonLabel() {
    const isPl = currentMediaData && currentMediaData.is_playlist;
    if (isPl) {
        if (currentMediaType === 'audio') {
            btnDownloadText.textContent = `Descargar Playlist en .ZIP (${selectedAudioFormat.toUpperCase()} - ${selectedAudioQuality} kbps)`;
        } else {
            btnDownloadText.textContent = `Descargar Playlist en .ZIP (MP4 - ${selectedVideoQuality}p)`;
        }
    } else {
        if (currentMediaType === 'audio') {
            btnDownloadText.textContent = `Descargar Audio (${selectedAudioFormat.toUpperCase()} - ${selectedAudioQuality} kbps)`;
        } else {
            btnDownloadText.textContent = `Descargar Video (MP4 - ${selectedVideoQuality}p)`;
        }
    }
}

// Trigger Download Flow
async function triggerDownload() {
    if (!currentMediaData) return;

    const isPl = !!currentMediaData.is_playlist;
    const payload = {
        url: currentMediaData.webpage_url,
        media_type: currentMediaType,
        quality: currentMediaType === 'audio' ? selectedAudioQuality : selectedVideoQuality,
        audio_format: selectedAudioFormat,
        is_playlist: isPl
    };

    btnStartDownload.disabled = true;
    showProgress(true);

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.detail || 'Error al iniciar la descarga.');
        }

        const taskId = res.task_id;
        pollDownloadProgress(taskId, payload, isPl);

    } catch (err) {
        const msg = err.message === 'Failed to fetch' 
            ? 'No se pudo conectar con el servidor. Asegúrate de que el servidor esté corriendo en la terminal.' 
            : err.message;
        showToast(msg, 'error');
        btnStartDownload.disabled = false;
        hideProgress();
    }
}

// Poll Progress from server
function pollDownloadProgress(taskId, payload, isPlaylist = false) {
    if (pollInterval) clearInterval(pollInterval);

    progressStatusTitle.textContent = isPlaylist ? 'Iniciando descarga de playlist...' : 'Descargando desde YouTube...';
    progressStatusStep.textContent = 'Conectando con el servidor...';
    progressBarFill.style.width = '3%';
    progressPercent.textContent = '3%';
    progressCompletedActions.classList.add('hidden');
    progressIcon.className = 'fa-solid fa-rotate text-sm animate-spin text-brand-400';

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${taskId}`);
            if (!response.ok) return;

            const data = await response.json();

            if (data.status === 'starting') {
                progressStatusTitle.textContent = isPlaylist ? 'Preparando lista de canciones...' : 'Iniciando descarga...';
                progressStatusStep.textContent = data.step || 'Conectando...';
                progressBarFill.style.width = `${data.progress || 5}%`;
                progressPercent.textContent = `${data.progress || 5}%`;
            } else if (data.status === 'downloading') {
                if (isPlaylist && data.total_tracks) {
                    progressStatusTitle.textContent = `Descargando Playlist (${data.track_index || 1} de ${data.total_tracks})`;
                } else {
                    progressStatusTitle.textContent = 'Descargando stream de medios...';
                }
                progressStatusStep.textContent = data.step || 'Descargando...';
                progressBarFill.style.width = `${data.progress}%`;
                progressPercent.textContent = `${data.progress}%`;
                progressSpeed.textContent = data.speed ? `${data.speed} ${data.eta ? '| ETA: ' + data.eta : ''}` : '';
            } else if (data.status === 'processing') {
                progressStatusTitle.textContent = isPlaylist ? 'Comprimiendo canciones en archivo .ZIP...' : 'Convirtiendo formato...';
                progressStatusStep.textContent = data.step || 'Procesando archivos...';
                progressBarFill.style.width = `${data.progress || 95}%`;
                progressPercent.textContent = `${data.progress || 95}%`;
                progressSpeed.textContent = 'Empaquetando...';
            } else if (data.status === 'completed') {
                clearInterval(pollInterval);
                pollInterval = null;

                progressBarFill.style.width = '100%';
                progressPercent.textContent = '100%';
                progressSpeed.textContent = `${data.size_mb} MB`;
                
                if (isPlaylist) {
                    progressStatusTitle.textContent = '¡Playlist Completada!';
                    progressStatusStep.textContent = `Se empaquetaron ${data.tracks_count || currentMediaData.track_count} canciones en un archivo .ZIP.`;
                    saveFileLabel.textContent = `Guardar Playlist ZIP (${data.size_mb} MB)`;
                } else {
                    progressStatusTitle.textContent = '¡Conversión Completada!';
                    progressStatusStep.textContent = `Archivo listo: ${data.title}.${data.extension}`;
                    saveFileLabel.textContent = `Guardar ${data.extension.toUpperCase()} (${data.size_mb} MB)`;
                }

                progressIcon.className = 'fa-solid fa-check text-sm text-emerald-400';

                // Configurar enlace de guardado
                const downloadUrl = `/api/file/${encodeURIComponent(data.filename)}`;
                btnSaveFile.href = downloadUrl;
                progressCompletedActions.classList.remove('hidden');
                btnStartDownload.disabled = false;

                // Iniciar descarga automática en el navegador
                const autoLink = document.createElement('a');
                autoLink.href = downloadUrl;
                autoLink.download = data.filename;
                document.body.appendChild(autoLink);
                autoLink.click();
                autoLink.remove();

                showToast(isPlaylist ? '¡Playlist descargada y comprimida en ZIP!' : '¡Descarga finalizada con éxito!', 'success');

                // Guardar en historial
                addToHistory({
                    title: data.title,
                    thumbnail: currentMediaData.thumbnail,
                    format: isPlaylist ? 'ZIP (Playlist)' : data.extension.toUpperCase(),
                    quality: payload.media_type === 'audio' ? `${payload.quality}k` : `${payload.quality}p`,
                    size: `${data.size_mb} MB`,
                    filename: data.filename,
                    date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                });

            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                pollInterval = null;
                btnStartDownload.disabled = false;
                showToast(`Error al procesar: ${data.error}`, 'error');
                progressStatusTitle.textContent = 'Error en el procesamiento';
                progressStatusStep.textContent = data.error;
                progressIcon.className = 'fa-solid fa-triangle-exclamation text-sm text-rose-400';
            }
        } catch (e) {
            console.error('Error polling progress:', e);
        }
    }, 800);
}

// UI Visibility Helpers
function showLoader(show, text = '') {
    if (show) {
        loaderText.textContent = text;
        loader.classList.remove('hidden');
    } else {
        loader.classList.add('hidden');
    }
}

function hideMediaCard() {
    mediaCard.classList.add('hidden');
}

function hideSearchResults() {
    searchResultsSection.classList.add('hidden');
}

function showProgress(show) {
    if (show) {
        progressBox.classList.remove('hidden');
        progressBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
        progressBox.classList.add('hidden');
    }
}

function hideProgress() {
    if (pollInterval) clearInterval(pollInterval);
    progressBox.classList.add('hidden');
}

function resetApp() {
    hideProgress();
    urlInput.value = '';
    urlInput.focus();
}

// History Functions
function getHistory() {
    try {
        return JSON.parse(localStorage.getItem('musicadow_history') || '[]');
    } catch {
        return [];
    }
}

function saveHistory(history) {
    localStorage.setItem('musicadow_history', JSON.stringify(history.slice(0, 15)));
}

function addToHistory(item) {
    const history = getHistory();
    history.unshift(item);
    saveHistory(history);
    renderHistory();
}

function clearHistory() {
    localStorage.removeItem('musicadow_history');
    renderHistory();
    showToast('Historial limpiado', 'info');
}

function loadHistory() {
    renderHistory();
}

function renderHistory() {
    const history = getHistory();
    if (history.length === 0) {
        historyEmpty.classList.remove('hidden');
        historyList.querySelectorAll('.history-item').forEach(el => el.remove());
        return;
    }

    historyEmpty.classList.add('hidden');
    historyList.querySelectorAll('.history-item').forEach(el => el.remove());

    history.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item bg-dark-800/50 border border-slate-800 hover:border-slate-700 p-3 rounded-xl flex items-center justify-between gap-3 text-xs';
        div.innerHTML = `
            <div class="flex items-center gap-3 min-w-0">
                <img src="${item.thumbnail}" class="w-12 h-9 rounded object-cover shrink-0 bg-dark-900">
                <div class="min-w-0">
                    <p class="font-semibold text-white truncate">${item.title}</p>
                    <div class="flex items-center gap-2 text-slate-400 mt-0.5">
                        <span class="px-1.5 py-0.2 rounded bg-brand-500/20 text-brand-300 font-bold text-[10px]">${item.format} ${item.quality}</span>
                        <span>${item.size}</span>
                        <span>&bull; ${item.date}</span>
                    </div>
                </div>
            </div>
            <a href="/api/file/${encodeURIComponent(item.filename)}" download class="bg-dark-700 hover:bg-dark-600 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-600 transition flex items-center gap-1.5 shrink-0 font-medium">
                <i class="fa-solid fa-download text-xs"></i>
                <span class="hidden sm:inline">Descargar</span>
            </a>
        `;
        historyList.appendChild(div);
    });
}
