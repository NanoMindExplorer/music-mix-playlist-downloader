"""
Web UI HTML/CSS/JS template for Music Mix & Playlist Downloader.
Cyberpunk dark-mode interface with zero external CDN dependencies.
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>🎵 Music Mix & Playlist Downloader Pro</title>
  <style>
    :root {
      --bg-dark: #090d16;
      --bg-card: #121826;
      --bg-card-hover: #192236;
      --border: #232f48;
      --border-glow: #38bdf8;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --cyan: #38bdf8;
      --magenta: #ec4899;
      --purple: #a855f7;
      --green: #22c55e;
      --yellow: #eab308;
      --red: #ef4444;
      --radius: 12px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      min-height: 100vh;
      padding-bottom: 90px;
      line-height: 1.5;
    }
    header {
      background: linear-gradient(180deg, rgba(18,24,38,0.95) 0%, rgba(9,13,22,0.85) 100%);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo-badge {
      background: linear-gradient(135deg, #38bdf8, #a855f7, #ec4899);
      padding: 8px 12px;
      border-radius: 10px;
      font-size: 20px;
      box-shadow: 0 0 15px rgba(56,189,248,0.3);
    }
    .brand h1 {
      font-size: 1.15rem;
      font-weight: 800;
      background: linear-gradient(90deg, #38bdf8, #c084fc, #f472b6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }
    .brand p {
      font-size: 0.75rem;
      color: var(--text-muted);
    }
    .header-badges {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.75rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(35,47,72,0.6);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }
    .badge.green { border-color: rgba(34,197,94,0.4); color: #4ade80; background: rgba(34,197,94,0.1); }
    .badge.cyan { border-color: rgba(56,189,248,0.4); color: #38bdf8; background: rgba(56,189,248,0.1); }
    .badge.purple { border-color: rgba(168,85,247,0.4); color: #c084fc; background: rgba(168,85,247,0.1); }

    /* Nav Tabs */
    .tabs-nav {
      display: flex;
      background: var(--bg-card);
      border-bottom: 1px solid var(--border);
      padding: 0 16px;
      overflow-x: auto;
      gap: 4px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 14px 18px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .tab-btn:hover { color: var(--text-main); }
    .tab-btn.active {
      color: var(--cyan);
      border-bottom-color: var(--cyan);
      background: linear-gradient(180deg, transparent 80%, rgba(56,189,248,0.08) 100%);
    }

    /* Container */
    .container {
      max-width: 1200px;
      margin: 20px auto;
      padding: 0 16px;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; animation: fadeIn 0.2s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

    /* Cards */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
      color: var(--text-main);
    }

    /* Form Inputs */
    .form-group {
      margin-bottom: 16px;
    }
    .form-label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--text-muted);
    }
    .input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }
    input[type="text"], input[type="number"], select {
      width: 100%;
      background: #0b101c;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
      color: var(--text-main);
      font-size: 0.95rem;
      transition: all 0.2s;
    }
    input[type="text"]:focus, input[type="number"]:focus, select:focus {
      outline: none;
      border-color: var(--cyan);
      box-shadow: 0 0 0 3px rgba(56,189,248,0.2);
    }
    .platform-indicator {
      position: absolute;
      right: 12px;
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      pointer-events: none;
    }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }

    /* Checkboxes */
    .checkbox-group {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .checkbox-card {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      background: rgba(11,16,28,0.6);
      border: 1px solid var(--border);
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      user-select: none;
      transition: all 0.2s;
    }
    .checkbox-card:hover { border-color: rgba(56,189,248,0.5); background: rgba(56,189,248,0.05); }
    .checkbox-card input[type="checkbox"] {
      margin-top: 3px;
      accent-color: var(--cyan);
      cursor: pointer;
    }
    .checkbox-card span strong { display: block; font-size: 0.85rem; color: var(--text-main); }
    .checkbox-card span small { display: block; font-size: 0.75rem; color: var(--text-muted); }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: all 0.2s;
      text-decoration: none;
    }
    .btn-primary {
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      color: #031326;
      box-shadow: 0 4px 16px rgba(56,189,248,0.3);
    }
    .btn-primary:hover {
      box-shadow: 0 6px 20px rgba(56,189,248,0.5);
      transform: translateY(-1px);
    }
    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
    .btn-secondary {
      background: #1e293b;
      color: var(--text-main);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover { background: #334155; }
    .btn-danger {
      background: rgba(239,68,68,0.2);
      color: #fca5a5;
      border: 1px solid rgba(239,68,68,0.4);
    }
    .btn-danger:hover { background: rgba(239,68,68,0.3); }
    .btn-sm { padding: 6px 12px; font-size: 0.8rem; }

    /* Progress & Logs */
    .progress-box {
      margin-top: 16px;
      background: #0b101c;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
    }
    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 0.85rem;
    }
    .progress-bar-bg {
      height: 10px;
      background: #1e293b;
      border-radius: 9999px;
      overflow: hidden;
      margin-bottom: 10px;
    }
    .progress-bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #38bdf8, #a855f7, #ec4899);
      border-radius: 9999px;
      transition: width 0.3s ease;
    }
    .progress-stats {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* Terminal Console */
    .terminal {
      background: #050811;
      border: 1px solid #1a2233;
      border-radius: 8px;
      padding: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.78rem;
      max-height: 240px;
      overflow-y: auto;
      margin-top: 12px;
      color: #cbd5e1;
    }
    .terminal-line { margin-bottom: 3px; word-break: break-all; }
    .terminal-line.cyan { color: #38bdf8; }
    .terminal-line.green { color: #4ade80; }
    .terminal-line.yellow { color: #fde047; }
    .terminal-line.red { color: #f87171; }
    .terminal-line.dim { color: #64748b; }

    /* Music Library Table */
    .table-responsive {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }
    th, td {
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      background: #0b101c;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.7rem;
      letter-spacing: 0.5px;
    }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .song-title-cell {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .song-icon {
      width: 36px;
      height: 36px;
      border-radius: 6px;
      background: linear-gradient(135deg, #1e293b, #334155);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }
    .song-meta h4 { font-size: 0.88rem; font-weight: 600; color: var(--text-main); margin-bottom: 2px; }
    .song-meta span { font-size: 0.75rem; color: var(--text-muted); }

    /* Persistent Audio Player */
    .audio-player-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(14,20,32,0.96);
      border-top: 1px solid var(--border);
      backdrop-filter: blur(16px);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 100;
      box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
    }
    .player-track-info {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 220px;
      max-width: 300px;
    }
    .player-controls {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      flex: 1;
      max-width: 560px;
    }
    .player-buttons {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .player-btn {
      background: transparent;
      border: none;
      color: var(--text-main);
      cursor: pointer;
      font-size: 18px;
      transition: all 0.2s;
    }
    .player-btn:hover { color: var(--cyan); transform: scale(1.1); }
    .player-btn.play-circle {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--cyan);
      color: #031326;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .player-progress-row {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    .seek-slider {
      flex: 1;
      height: 4px;
      accent-color: var(--cyan);
      cursor: pointer;
    }

    /* Modal Karaoke Lyrics */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 200;
      padding: 16px;
    }
    .modal-overlay.active { display: flex; }
    .modal-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 640px;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 16px 40px rgba(0,0,0,0.6);
    }
    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-body {
      padding: 20px;
      overflow-y: auto;
      flex: 1;
    }
    .lyric-item {
      padding: 8px 12px;
      border-radius: 8px;
      margin-bottom: 6px;
      transition: all 0.2s;
    }
    .lyric-item.current {
      background: rgba(56,189,248,0.12);
      border-left: 3px solid var(--cyan);
    }
    .lyric-time { font-size: 0.72rem; color: var(--cyan); font-family: monospace; }
    .lyric-orig { font-size: 0.95rem; font-weight: 600; color: var(--text-main); }
    .lyric-trans { font-size: 0.85rem; color: #cbd5e1; font-style: italic; margin-top: 2px; }

    @media (max-width: 768px) {
      .header-badges { display: none; }
      .audio-player-bar { flex-direction: column; align-items: stretch; gap: 8px; padding: 8px 12px; }
      .player-track-info { max-width: 100%; }
      body { padding-bottom: 130px; }
    }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="brand">
      <div class="logo-badge">🎧</div>
      <div>
        <h1>MUSIC MIX & PLAYLIST DOWNLOADER</h1>
        <p>Next-Gen Audio & Lyrics AI Engine • Web Browser Edition</p>
      </div>
    </div>
    <div class="header-badges">
      <div class="badge green">● Server Online</div>
      <div class="badge cyan" id="badge-version">v3.1-pro</div>
      <div class="badge purple" id="badge-webhook">🔔 Discord Hook Active</div>
    </div>
  </header>

  <!-- Tabs Navigation -->
  <nav class="tabs-nav">
    <button class="tab-btn active" onclick="switchTab('downloader')">📥 Downloader</button>
    <button class="tab-btn" onclick="switchTab('library')">🎵 Library & Player</button>
    <button class="tab-btn" onclick="switchTab('retrofit')">🛠️ Retrofit Engine</button>
    <button class="tab-btn" onclick="switchTab('settings')">⚙️ Diagnostik & Webhook</button>
  </nav>

  <div class="container">

    <!-- ==================== TAB 1: DOWNLOADER ==================== -->
    <div id="tab-downloader" class="tab-content active">
      <div class="card">
        <div class="card-title">
          <span>🚀 Unduh Lagu, Playlist, atau Album</span>
          <span class="badge cyan" id="detect-badge">🔍 Auto Detect Platform</span>
        </div>

        <form id="download-form" onsubmit="startDownload(event)">
          <div class="form-group">
            <label class="form-label">URL / Judul Lagu (YouTube, Spotify, SoundCloud, atau Kata Kunci):</label>
            <div class="input-wrapper">
              <input type="text" id="dl-url" required 
                placeholder="Contoh: https://open.spotify.com/playlist/... atau https://youtube.com/... atau Avenged Sevenfold"
                oninput="detectPlatform(this.value)">
              <span class="platform-indicator" id="platform-tag">Universal</span>
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Format & Kualitas Audio:</label>
              <select id="dl-format">
                <option value="mp3:320" selected>MP3 (320 kbps) - Rekomendasi (Tinggi)</option>
                <option value="mp3:256">MP3 (256 kbps) - Standar Studio</option>
                <option value="mp3:192">MP3 (192 kbps) - Ringan</option>
                <option value="mp3:128">MP3 (128 kbps) - Hemat Kuota</option>
                <option value="flac:none">FLAC (Lossless) - Kualitas Murni Studio</option>
                <option value="wav:none">WAV (Uncompressed) - Audio Mentah</option>
                <option value="best:none">Original Audio - Format Bawaan Sumber</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Batasan Maksimal Lagu (Opsional):</label>
              <input type="number" id="dl-max" placeholder="Semua (Kosongkan jika ingin unduh penuh)" min="1">
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Mesin Lirik Sinkron (.LRC):</label>
              <select id="dl-lyrics">
                <option value="🎧 1" selected>🎧 Spotify / Musixmatch (Anti-Blokir, Studio Quality)</option>
                <option value="📺 3">📺 YouTube Subtitles (Cocok untuk Lagu Cover)</option>
                <option value="❌ 4">❌ Jangan Download Lirik</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Transliterasi Aksara Asing (Romaji / Pinyin / Latin):</label>
              <select id="dl-transliterate">
                <option value="❌ 1" selected>❌ Biarkan Asli (Tanpa Transliterasi)</option>
                <option value="🇯🇵 2">🇯🇵 Romaji (Jepang / Anime)</option>
                <option value="🇨🇳 3">🇨🇳 Pinyin (Mandarin / China)</option>
                <option value="🇭🇰 4">🇭🇰 Jyutping (Kanton / Hong Kong)</option>
                <option value="🤖 5">🤖 Deteksi Otomatis (Playlist Campuran)</option>
              </select>
            </div>
          </div>

          <!-- Feature Toggles -->
          <div class="checkbox-group">
            <label class="checkbox-card">
              <input type="checkbox" id="dl-translate" checked>
              <span>
                <strong>🌐 Terjemahan Lirik Bahasa Indonesia</strong>
                <small>AI bilingual lyrics (ditampilkan di bawah teks karaoke asli)</small>
              </span>
            </label>

            <label class="checkbox-card">
              <input type="checkbox" id="dl-embed-id3" checked>
              <span>
                <strong>🖼️ Injeksi ID3 & Cover Art (Thumbnail)</strong>
                <small>Tanam gambar & lirik ke dalam file MP3/FLAC</small>
              </span>
            </label>

            <label class="checkbox-card">
              <input type="checkbox" id="dl-antidedup" checked>
              <span>
                <strong>🛡️ Anti-Duplikat (Archive.txt)</strong>
                <small>Lewati lagu yang sudah pernah diunduh sebelumnya</small>
              </span>
            </label>

            <label class="checkbox-card">
              <input type="checkbox" id="dl-sync-huawei">
              <span>
                <strong>📱 Sinkronisasi Huawei Musiclrc</strong>
                <small>Salin lirik otomatis ke folder Internal/Music/Musiclrc</small>
              </span>
            </label>

            <label class="checkbox-card">
              <input type="checkbox" id="dl-notify-discord" checked>
              <span>
                <strong>🔔 Notifikasi Discord Webhook</strong>
                <small>Kirim pesan & detail lagu ke Discord setelah selesai</small>
              </span>
            </label>
          </div>

          <div style="margin-top: 20px; display: flex; gap: 12px; align-items: center;">
            <button type="submit" class="btn btn-primary" id="btn-start-dl">
              <span>⚡ Mulai Unduh Audio</span>
            </button>
            <button type="button" class="btn btn-danger btn-sm" id="btn-cancel-dl" style="display: none;" onclick="cancelTask()">
              <span>⏹️ Batalkan Tugas</span>
            </button>
          </div>
        </form>

        <!-- Live Progress Container -->
        <div class="progress-box" id="progress-container" style="display: none;">
          <div class="progress-header">
            <span id="progress-title" style="font-weight: 600; color: var(--cyan);">Memulai Unduhan...</span>
            <span id="progress-percent" style="font-weight: 700; color: var(--text-main);">0%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" id="progress-bar"></div>
          </div>
          <div class="progress-stats">
            <span id="progress-speed">Kecepatan: --</span>
            <span id="progress-eta">Sisa Waktu: --</span>
          </div>

          <!-- Realtime Terminal Log -->
          <div class="terminal" id="terminal-logs">
            <div class="terminal-line dim">Menunggu respon server...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 2: LIBRARY & PLAYER ==================== -->
    <div id="tab-library" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>📁 Koleksi Musik Unduhan</span>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="lib-search" placeholder="Cari lagu / artis..." style="width: 200px; padding: 6px 10px; font-size: 0.8rem;" oninput="filterLibrary(this.value)">
            <button class="btn btn-secondary btn-sm" onclick="loadLibrary()">🔄 Refresh</button>
          </div>
        </div>

        <div class="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Lagu & Artis</th>
                <th>Format</th>
                <th>Ukuran</th>
                <th>Fitur</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody id="library-tbody">
              <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">Memuat koleksi musik...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ==================== TAB 3: RETROFIT ENGINE ==================== -->
    <div id="tab-retrofit" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>🛠️ Retrofit Engine (Perbaiki Koleksi Lagu Lama)</span>
        </div>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 16px;">
          Punya folder MP3/FLAC lama yang belum ada Cover Art atau Lirik sinkron? Mode ini memindai folder Anda, melacak judulnya, lalu secara otomatis menyuntikkan lirik (.lrc), terjemahan Bahasa Indonesia, dan cover art tanpa mengunduh ulang audionya!
        </p>

        <form id="retrofit-form" onsubmit="startRetrofit(event)">
          <div class="form-group">
            <label class="form-label">Folder Koleksi Musik yang Ingin Diperbaiki:</label>
            <input type="text" id="rf-dir" placeholder="Contoh: /root/Downloads/YT_Downloader">
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Target Perbaikan:</label>
              <select id="rf-target">
                <option value="full" selected>✨ Lirik & Cover Art (Lengkap)</option>
                <option value="lyrics">📝 Lirik Saja (Abaikan Cover Art)</option>
                <option value="covers">🖼️ Cover Art Saja (Abaikan Lirik)</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Transliterasi Aksara Asing:</label>
              <select id="rf-transliterate">
                <option value="❌ 1" selected>❌ Biarkan Asli</option>
                <option value="🤖 5">🤖 Deteksi Otomatis & Ubah Semua</option>
                <option value="🇯🇵 2">🇯🇵 Romaji (Jepang)</option>
                <option value="🇨🇳 3">🇨🇳 Pinyin (Mandarin)</option>
              </select>
            </div>
          </div>

          <div class="checkbox-group">
            <label class="checkbox-card">
              <input type="checkbox" id="rf-translate" checked>
              <span>
                <strong>🌐 Tambahkan Terjemahan Bahasa Indonesia</strong>
                <small>Suntikkan lirik bilingual ke file karaoke</small>
              </span>
            </label>

            <label class="checkbox-card">
              <input type="checkbox" id="rf-overwrite">
              <span>
                <strong>⚠️ Timpa File Lirik Lama</strong>
                <small>Jika lirik lama salah ketukan atau rusak</small>
              </span>
            </label>
          </div>

          <div style="margin-top: 16px;">
            <button type="submit" class="btn btn-primary" id="btn-start-rf">
              <span>🛠️ Mulai Eksekusi Retrofit</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ==================== TAB 4: SETTINGS & DIAGNOSTICS ==================== -->
    <div id="tab-settings" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>🩺 Sistem Diagnostik & Konfigurasi (Doctor)</span>
          <button class="btn btn-secondary btn-sm" onclick="runDoctor()">🩺 Cek Sistem</button>
        </div>
        <div id="doctor-results" style="font-size: 0.85rem;">
          <p style="color: var(--text-muted);">Klik "Cek Sistem" untuk mendiagnosis FFmpeg, Python dependencies, dan izin penyimpanan.</p>
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <span>🔔 Discord Webhook Notifier</span>
          <button class="btn btn-primary btn-sm" onclick="testDiscordWebhook()">🧪 Kirim Uji Coba</button>
        </div>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 12px;">
          Setiap kali proses unduhan atau perbaikan musik selesai, bot akan secara otomatis mengirim kartu rangkuman ke Discord channel Anda:
        </p>
        <div class="form-group">
          <input type="text" id="webhook-url" readonly value="https://discord.com/api/webhooks/1554679149459935418/eZvLqvhcOypINbSiwCvOQVnKJ0KeV_qP_wmQiHw_wTeWxmmmc6wxjZRktzodeX2Mkldo" style="font-family: monospace; font-size: 0.8rem; color: #94a3b8;">
        </div>
        <div id="webhook-status" style="font-size: 0.85rem;"></div>
      </div>
    </div>

  </div>

  <!-- Persistent Audio Player Bar -->
  <div class="audio-player-bar" id="audio-player-bar" style="display: none;">
    <div class="player-track-info">
      <div class="song-icon" id="player-icon">🎵</div>
      <div style="overflow: hidden;">
        <h5 id="player-title" style="font-size: 0.85rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Memutar Lagu</h5>
        <p id="player-artist" style="font-size: 0.72rem; color: var(--text-muted);">MMPD Player</p>
      </div>
    </div>

    <div class="player-controls">
      <div class="player-buttons">
        <button class="player-btn" onclick="seekRelative(-10)">⏪ 10s</button>
        <button class="player-btn play-circle" id="player-play-btn" onclick="togglePlay()">▶</button>
        <button class="player-btn" onclick="seekRelative(10)">10s ⏩</button>
      </div>
      <div class="player-progress-row">
        <span id="player-cur-time">0:00</span>
        <input type="range" class="seek-slider" id="player-seek" min="0" max="100" value="0" oninput="onSeekInput(this.value)">
        <span id="player-dur-time">0:00</span>
      </div>
    </div>

    <div>
      <button class="btn btn-secondary btn-sm" onclick="showLyricsModal()">🎤 Lirik Karaoke</button>
    </div>
  </div>

  <!-- Audio Element -->
  <audio id="global-audio" preload="none"></audio>

  <!-- Modal Karaoke Lyrics -->
  <div class="modal-overlay" id="lyrics-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div>
          <h3 id="modal-song-title" style="font-size: 1rem; font-weight: 700;">Lirik Lagu</h3>
          <p id="modal-song-subtitle" style="font-size: 0.75rem; color: var(--text-muted);">Sinkronisasi Waktu & Terjemahan Indonesia</p>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="closeLyricsModal()">✕ Tutup</button>
      </div>
      <div class="modal-body" id="modal-lyrics-body">
        <p style="color: var(--text-muted); text-align: center;">Memuat lirik...</p>
      </div>
    </div>
  </div>

  <script>
    let currentTaskId = null;
    let pollInterval = null;
    let libraryData = [];
    let currentPlayingTrack = null;
    let currentLyrics = [];

    // Tabs
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + tabId).classList.add('active');
      if (tabId === 'library') loadLibrary();
      if (tabId === 'settings') loadConfig();
    }

    // Auto-detect platform badge
    function detectPlatform(val) {
      const tag = document.getElementById('platform-tag');
      const badge = document.getElementById('detect-badge');
      val = val.toLowerCase();
      if (val.includes('spotify.com')) {
        tag.textContent = '🟢 Spotify';
        tag.style.color = '#22c55e';
        badge.textContent = '🟢 Spotify Mode Terdeteksi';
      } else if (val.includes('soundcloud.com')) {
        tag.textContent = '🟠 SoundCloud';
        tag.style.color = '#f97316';
        badge.textContent = '🟠 SoundCloud Mode Terdeteksi';
      } else if (val.includes('youtube.com') || val.includes('youtu.be')) {
        tag.textContent = '🔴 YouTube';
        tag.style.color = '#ef4444';
        badge.textContent = '🔴 YouTube Mode Terdeteksi';
      } else if (val.trim()) {
        tag.textContent = '🔍 Search Query';
        tag.style.color = '#38bdf8';
        badge.textContent = '🔍 Pencarian Universal';
      } else {
        tag.textContent = 'Universal';
        tag.style.color = 'inherit';
        badge.textContent = '🔍 Auto Detect Platform';
      }
    }

    // Start Download
    async function startDownload(e) {
      e.preventDefault();
      const url = document.getElementById('dl-url').value.trim();
      if (!url) return;

      const formatVal = document.getElementById('dl-format').value.split(':');
      const payload = {
        url: url,
        codec: formatVal[0],
        quality: formatVal[1] === 'none' ? null : formatVal[1],
        max_songs: document.getElementById('dl-max').value ? parseInt(document.getElementById('dl-max').value) : null,
        lyrics_mode: document.getElementById('dl-lyrics').value,
        transliterate: document.getElementById('dl-transliterate').value,
        translate_id: document.getElementById('dl-translate').checked,
        embed_id3: document.getElementById('dl-embed-id3').checked,
        anti_duplicate: document.getElementById('dl-antidedup').checked,
        sync_huawei: document.getElementById('dl-sync-huawei').checked,
        notify_discord: document.getElementById('dl-notify-discord').checked,
      };

      document.getElementById('btn-start-dl').disabled = true;
      document.getElementById('btn-cancel-dl').style.display = 'inline-flex';
      document.getElementById('progress-container').style.display = 'block';
      document.getElementById('terminal-logs').innerHTML = '<div class="terminal-line cyan">Mengirim perintah ke mesin MMPD...</div>';

      try {
        const res = await fetch('/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.task_id) {
          currentTaskId = data.task_id;
          startPolling(currentTaskId);
        } else {
          alert('Gagal memulai tugas: ' + (data.error || 'Unknown'));
          resetDownloadState();
        }
      } catch (err) {
        alert('Koneksi server gagal: ' + err);
        resetDownloadState();
      }
    }

    function startPolling(taskId) {
      if (pollInterval) clearInterval(pollInterval);
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch('/api/task/' + taskId);
          const task = await res.json();

          // Update Progress
          document.getElementById('progress-title').textContent = task.stage_message || 'Sedang memproses...';
          document.getElementById('progress-percent').textContent = Math.round(task.progress || 0) + '%';
          document.getElementById('progress-bar').style.width = Math.min(100, Math.max(0, task.progress || 0)) + '%';
          document.getElementById('progress-speed').textContent = 'Kecepatan: ' + (task.speed || '--');
          document.getElementById('progress-eta').textContent = 'Sisa: ' + (task.eta || '--');

          // Update Logs
          if (task.logs && task.logs.length) {
            const term = document.getElementById('terminal-logs');
            term.innerHTML = task.logs.map(l => {
              const cls = l.level === 'error' ? 'red' : l.level === 'warn' ? 'yellow' : l.level === 'success' ? 'green' : 'cyan';
              return `<div class="terminal-line ${cls}">[${l.time}] ${escapeHtml(l.msg)}</div>`;
            }).join('');
            term.scrollTop = term.scrollHeight;
          }

          if (task.status === 'completed') {
            clearInterval(pollInterval);
            resetDownloadState();
            document.getElementById('progress-title').textContent = '✨ Unduhan Selesai!';
            document.getElementById('progress-percent').textContent = '100%';
            document.getElementById('progress-bar').style.width = '100%';
            loadLibrary();
          } else if (task.status === 'error' || task.status === 'cancelled') {
            clearInterval(pollInterval);
            resetDownloadState();
            document.getElementById('progress-title').textContent = task.status === 'cancelled' ? '⏹️ Dibatalkan' : '❌ Error: ' + (task.error || '');
          }
        } catch (e) {
          console.error(e);
        }
      }, 1000);
    }

    function resetDownloadState() {
      document.getElementById('btn-start-dl').disabled = false;
      document.getElementById('btn-cancel-dl').style.display = 'none';
    }

    async function cancelTask() {
      if (!currentTaskId) return;
      await fetch('/api/task/' + currentTaskId + '/cancel', { method: 'POST' });
    }

    // Library & Player
    async function loadLibrary() {
      const tbody = document.getElementById('library-tbody');
      try {
        const res = await fetch('/api/library');
        libraryData = await res.json();
        renderLibrary(libraryData);
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--red);">Gagal memuat: ${err}</td></tr>`;
      }
    }

    function renderLibrary(items) {
      const tbody = document.getElementById('library-tbody');
      if (!items || !items.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">Belum ada lagu yang diunduh. Silakan unduh lagu di tab Downloader!</td></tr>';
        return;
      }
      tbody.innerHTML = items.map(item => `
        <tr>
          <td>
            <div class="song-title-cell">
              <div class="song-icon">🎵</div>
              <div class="song-meta">
                <h4>${escapeHtml(item.title)}</h4>
                <span>${escapeHtml(item.artist || 'MMPD Library')}</span>
              </div>
            </div>
          </td>
          <td><span class="badge">${item.ext.toUpperCase()}</span></td>
          <td>${item.size_mb} MB</td>
          <td>
            ${item.has_lrc ? '<span class="badge green">🎤 LRC</span>' : '<span class="badge">No LRC</span>'}
            ${item.has_id_lyrics ? '<span class="badge cyan">🇮🇩 ID</span>' : ''}
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-primary btn-sm" onclick="playSong('${escapeHtml(item.rel_path)}', '${escapeHtml(item.title)}')">▶ Putar</button>
              ${item.has_lrc ? `<button class="btn btn-secondary btn-sm" onclick="openLyrics('${escapeHtml(item.lrc_rel_path)}', '${escapeHtml(item.title)}')">Lirik</button>` : ''}
              <a href="/api/download-file/${encodeURIComponent(item.rel_path)}" class="btn btn-secondary btn-sm" download>⬇</a>
            </div>
          </td>
        </tr>
      `).join('');
    }

    function filterLibrary(q) {
      q = q.toLowerCase();
      const filtered = libraryData.filter(i => i.title.toLowerCase().includes(q) || (i.artist && i.artist.toLowerCase().includes(q)));
      renderLibrary(filtered);
    }

    // Audio Playback
    const audio = document.getElementById('global-audio');
    const playBar = document.getElementById('audio-player-bar');
    const playBtn = document.getElementById('player-play-btn');

    function playSong(relPath, title) {
      currentPlayingTrack = { path: relPath, title: title };
      audio.src = '/api/stream/' + encodeURIComponent(relPath);
      audio.play();
      playBar.style.display = 'flex';
      document.getElementById('player-title').textContent = title;
      playBtn.textContent = '⏸';
      loadSongLyrics(relPath);
    }

    function togglePlay() {
      if (audio.paused) {
        audio.play();
        playBtn.textContent = '⏸';
      } else {
        audio.pause();
        playBtn.textContent = '▶';
      }
    }

    function seekRelative(sec) {
      audio.currentTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + sec));
    }

    audio.ontimeupdate = () => {
      const cur = audio.currentTime || 0;
      const dur = audio.duration || 0;
      document.getElementById('player-cur-time').textContent = formatTime(cur);
      document.getElementById('player-dur-time').textContent = formatTime(dur);
      if (dur > 0) {
        document.getElementById('player-seek').value = (cur / dur) * 100;
      }
      highlightLyric(cur);
    };

    function onSeekInput(val) {
      if (audio.duration) {
        audio.currentTime = (val / 100) * audio.duration;
      }
    }

    function formatTime(sec) {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${m}:${s < 10 ? '0' : ''}${s}`;
    }

    // Lyrics Handling
    async function loadSongLyrics(relPath) {
      try {
        const res = await fetch('/api/lyrics/' + encodeURIComponent(relPath));
        const data = await res.json();
        currentLyrics = data.lines || [];
      } catch (e) {
        currentLyrics = [];
      }
    }

    async function openLyrics(lrcPath, title) {
      showLyricsModal();
      document.getElementById('modal-song-title').textContent = title;
      const body = document.getElementById('modal-lyrics-body');
      body.innerHTML = '<p style="color: var(--text-muted); text-align: center;">Memuat lirik...</p>';
      try {
        const res = await fetch('/api/lyrics/' + encodeURIComponent(lrcPath));
        const data = await res.json();
        currentLyrics = data.lines || [];
        renderLyricsList(currentLyrics);
      } catch (e) {
        body.innerHTML = '<p style="color: var(--red); text-align: center;">Lirik tidak ditemukan.</p>';
      }
    }

    function renderLyricsList(lines) {
      const body = document.getElementById('modal-lyrics-body');
      if (!lines || !lines.length) {
        body.innerHTML = '<p style="color: var(--text-muted); text-align: center;">Tidak ada lirik sinkron.</p>';
        return;
      }
      body.innerHTML = lines.map((l, idx) => `
        <div class="lyric-item" id="lyric-line-${idx}">
          <div class="lyric-time">[${formatTime(l.time)}]</div>
          <div class="lyric-orig">${escapeHtml(l.text)}</div>
          ${l.translation ? `<div class="lyric-trans">${escapeHtml(l.translation)}</div>` : ''}
        </div>
      `).join('');
    }

    function highlightLyric(curTime) {
      if (!currentLyrics || !currentLyrics.length) return;
      let activeIdx = -1;
      for (let i = 0; i < currentLyrics.length; i++) {
        if (curTime >= currentLyrics[i].time) {
          activeIdx = i;
        } else {
          break;
        }
      }
      if (activeIdx !== -1) {
        document.querySelectorAll('.lyric-item').forEach(el => el.classList.remove('current'));
        const el = document.getElementById('lyric-line-' + activeIdx);
        if (el) {
          el.classList.add('current');
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }

    function showLyricsModal() {
      document.getElementById('lyrics-modal').classList.add('active');
    }
    function closeLyricsModal() {
      document.getElementById('lyrics-modal').classList.remove('active');
    }

    // Diagnostics & Webhook
    async function runDoctor() {
      const container = document.getElementById('doctor-results');
      container.innerHTML = '<p style="color: var(--cyan);">Menjalankan diagnosa sistem...</p>';
      try {
        const res = await fetch('/api/doctor');
        const data = await res.json();
        container.innerHTML = `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 12px;">
            <div class="badge ${data.ffmpeg_ok ? 'green' : 'red'}">FFmpeg: ${data.ffmpeg_ok ? 'Siap' : 'Hilang'}</div>
            <div class="badge green">Python: ${data.python_version}</div>
            <div class="badge green">yt-dlp: ${data.ytdlp_version}</div>
            <div class="badge cyan">Storage: ${data.storage_ok ? 'Akses OK' : 'Check Permission'}</div>
          </div>
          <div style="margin-top: 14px; color: var(--text-muted); font-size: 0.8rem;">
            Folder Output: <code>${escapeHtml(data.output_dir)}</code>
          </div>
        `;
      } catch (e) {
        container.innerHTML = '<p style="color: var(--red);">Gagal menjalankan diagnosa.</p>';
      }
    }

    async function testDiscordWebhook() {
      const statusDiv = document.getElementById('webhook-status');
      statusDiv.innerHTML = '<span style="color: var(--cyan);">Mengirim notifikasi tes ke Discord...</span>';
      try {
        const res = await fetch('/api/webhook/test', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
          statusDiv.innerHTML = '<span style="color: var(--green);">✅ Berhasil! Notifikasi terkirim ke Discord channel Anda.</span>';
        } else {
          statusDiv.innerHTML = `<span style="color: var(--red);">❌ Gagal: ${data.error}</span>`;
        }
      } catch (e) {
        statusDiv.innerHTML = `<span style="color: var(--red);">❌ Error koneksi: ${e}</span>`;
      }
    }

    // Retrofit
    async function startRetrofit(e) {
      e.preventDefault();
      const dir = document.getElementById('rf-dir').value.trim();
      const payload = {
        dir: dir,
        target: document.getElementById('rf-target').value,
        transliterate: document.getElementById('rf-transliterate').value,
        translate: document.getElementById('rf-translate').checked,
        overwrite: document.getElementById('rf-overwrite').checked,
      };

      document.getElementById('btn-start-rf').disabled = true;
      try {
        const res = await fetch('/api/retrofit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.task_id) {
          switchTab('downloader');
          currentTaskId = data.task_id;
          document.getElementById('progress-container').style.display = 'block';
          startPolling(currentTaskId);
        } else {
          alert('Gagal: ' + data.error);
        }
      } catch (err) {
        alert('Gagal mengirim perintah: ' + err);
      } finally {
        document.getElementById('btn-start-rf').disabled = false;
      }
    }

    async function loadConfig() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        if (data.version) document.getElementById('badge-version').textContent = 'v' + data.version;
        if (data.output_dir && !document.getElementById('rf-dir').value) {
          document.getElementById('rf-dir').value = data.output_dir;
        }
      } catch (e) {}
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Init
    loadConfig();
  </script>
</body>
</html>
"""
