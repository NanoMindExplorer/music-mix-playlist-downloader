# 🎵 Music Mix & Playlist Downloader Pro (AI Edition)

Aplikasi CLI interaktif *Next-Gen* untuk mendownload YouTube Mix, Playlist Spotify, SoundCloud, dan lainnya secara otomatis, lalu mengonversinya menjadi audio berkualitas tinggi (MP3/FLAC/WAV). Dilengkapi dengan **Kecerdasan Buatan (AI)** untuk menerjemahkan lirik, mengubah huruf asing ke alfabet Latin (Transliterasi), dan memanajemen perpustakaan musik Anda bak seorang profesional!

## 🆕 Apa Baru di v3.5 (Fase 4 — Hardening & Polish)

- **Translation cache** (SQLite) — avoid re-translate same lyrics via Google API
- **Lyrics cache** (SQLite, TTL 30 hari) — avoid re-fetch dari LRCLIB/syncedlyrics
- **333 unit tests** (+99 dari Fase 3), coverage **77%** (naik dari 72%)
- **`mmpd/cache.py`** baru — SQLite-based persistent cache (no external dep)
- **Deprecate `spotify_parser.py`** — pakai `mmpd.spotify_client.SpotifyClient` (official API)
- **Termux ruff fix** — skip ruff/black di Android (butuh Rust toolchain)
- **Coverage threshold** naik dari 70% → 75%
- **mypy strict** di CI (Python <3.14 only)
- **Modul yang sekarang 100% coverage**: `concurrent.py`, `ytdlp.py`, `utils/__init__.py`

### Performance Impact

Cache menghindari API call berulang:
- Translation: kalau lirik yang sama di-translate lagi, **100% cache hit** (skip Google API)
- Lyrics: kalau track yang sama di-search lagi dalam 30 hari, **cache hit** (skip LRCLIB API)

Untuk playlist Spotify 50 lagu yang di-download ulang:
- Tanpa cache: ~50 API calls ke LRCLIB + ~50 calls ke Google Translate
- Dengan cache: **0 API calls** (semua cache hit) → 10x lebih cepat

## 🆕 Apa Baru di v3.4 (Fase 3 — Testing & QA)

- **Unit tests komprehensif** (10 file test, 100+ test cases) untuk semua modul modular
- **Coverage target 80%+** via pytest-cov dengan config di `pyproject.toml`
- **GitHub Actions CI/CD** — auto-run tests di setiap push/PR (Python 3.9-3.14)
- **Mock strategy** — tidak hit network saat test (mock yt_dlp, spotipy, requests, pykakasi)
- **Test fixtures** di `tests/conftest.py` (mock_track_info, mock_youtube_entry, dll)
- **CI status badge** — lihat status build real-time di README
- **Type check** via mypy (non-blocking untuk saat ini)
- **Linting** via ruff (non-blocking untuk saat ini)

### Run tests locally

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run semua test
pytest tests/ -v

# Run dengan coverage report
pytest tests/ --cov=mmpd --cov-report=term

# Generate HTML coverage report (buka htmlcov/index.html)
pytest tests/ --cov=mmpd --cov-report=html
```

Lihat [`tests/README.md`](tests/README.md) untuk dokumentasi lengkap test suite.

## 🆕 Apa Baru di v3.3 (Fase 2.3 — Spotify Modernization)

- **Spotify official API** via `spotipy` (menggantikan scraping `__NEXT_DATA__` yang rapuh)
- **ISRC-based YouTube matching** (akurasi 99%+ vs fuzzy title matching lama)
- **Concurrent downloads** untuk Spotify playlist (3 worker paralel, 3x speedup)
- **Spotify API retry** dengan exponential backoff (1s → 2s → 4s)
- **`mmpd doctor`** sekarang cek Spotify credentials (SPOTIPY_CLIENT_ID/SECRET)
- **Fallback chain**: spotipy (with ISRC) → spotipy (no ISRC) → legacy scraping
- **Backward compatible**: tanpa credentials Spotify, tetap jalan pakai legacy scraping

### Setup Spotify API (opsional, tapi recommended untuk ISRC matching)

1. Buka https://developer.spotify.com/dashboard
2. Login dengan akun Spotify (gratis)
3. Klik **"Create app"**
4. Isi App name & description (apa saja), Redirect URI: `http://localhost`
5. Setelah app dibuat, buka Settings → salin **Client ID** dan **Client Secret**
6. Set environment variables di Termux/Linux:
   ```bash
   echo 'export SPOTIPY_CLIENT_ID="your_client_id_here"' >> ~/.bashrc
   echo 'export SPOTIPY_CLIENT_SECRET="your_client_secret_here"' >> ~/.bashrc
   source ~/.bashrc
   ```
7. Verifikasi: `mmpd doctor` → harus muncul "Spotify ISRC matching AKTIF"

Tanpa setup ini, aplikasi tetap jalan tapi Spotify matching pakai fuzzy title (akurasi ~70%).

## 🆕 Apa Baru di v3.2 (Fase 2.2 — Module Extraction)

- **downloader.py turun dari 1165 → 142 baris** (-88%!) — semua logic dipindah ke package `mmpd/`
- **Modular package structure**:
  ```
  mmpd/
  ├── config.py            (Fase 2.1)
  ├── logger.py            (Fase 2.1)
  ├── types.py             (Fase 2.1)
  ├── lyrics_providers.py  (Fase 2.1)
  ├── doctor.py            (Fase 2.1)
  ├── ui.py                (BARU — banner, theme, helpers)
  ├── ytdlp.py             (BARU — opts builder, hooks)
  ├── spotify.py           (BARU — URL parser wrapper)
  ├── lyrics.py            (BARU — transliteration + translation + sync)
  ├── utils/
  │   ├── ffmpeg.py        (BARU — subprocess wrapper)
  │   ├── fs.py            (BARU — atomic write, file ops)
  │   └── matching.py      (BARU — rapidfuzz wrapper)
  └── modes/
      ├── retrofit.py      (BARU — Mode 2)
      ├── organizer.py     (BARU — Mode 3)
      └── download.py      (BARU — Mode 1/4/5)
  ```
- **Clear separation of concerns**: UI code terpisah dari business logic, file ops di utils/, mode handlers di modes/
- **Testable**: setiap modul bisa di-unit-test terpisah (Fase 3 akan tambah tests/)
- **Backward compatible**: semua import lama (`from downloader import run_cli`, `from downloader import fetch_synced_lyrics`) tetap berfungsi via re-export

## 🆕 Apa Baru di v3.1 (Fase 2.1)

- **Package `mmpd`**: struktur modular dengan `pyproject.toml` resmi
- **Multi-entry point**:
  - `python downloader.py` (backward compatible, masih support)
  - `python -m mmpd` (baru — module entry)
  - `mmpd` (baru — entry point setelah `pip install .`)
- **`mmpd doctor`**: command diagnostik untuk cek dependency, network, storage, dan konfigurasi
- **Structured logging** dengan file rotation di `~/.local/share/mmpd/logs/mmpd.log` (atau `$PREFIX/var/log/mmpd/mmpd.log` di Termux)
- **Lyrics provider abstraction** dengan fallback chain:
  1. **LRCLIB** (baru — database lirik sinkron terbesar, gratis, no-auth)
  2. **syncedlyrics** (existing — Musixmatch/NetEase/Megalobiz)
- **Type hints** bertahap untuk fungsi publik + `mypy` config
- **Centralized config** (`mmpd/config.py`) — path detection Termux/Linux/Windows terpusat

---

## ⚡ Cara Instalasi & Pembaruan (One-Line)

Cukup salin (copy) dan jalankan (paste) satu baris perintah di bawah ini pada terminal sesuai dengan perangkat yang Anda gunakan. 
Perintah sakti ini didesain untuk **otomatis menginstal versi terbaru** beserta seluruh dependensi AI-nya. Jalankan ulang perintah ini kapan saja untuk *update* ke versi paling mutakhir!

### 📱 Android (Termux)
*(Catatan: Anda akan dimintai izin akses penyimpanan, tekan Allow/Izinkan)*
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && rm -rf music-mix-playlist-downloader && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip install -U -r requirements.txt --break-system-packages
```

**Cara pakai baru (Fase 2.1):** setelah clone, Anda bisa juga install sebagai package:
```bash
pip install -e . --break-system-packages   # enable command `mmpd`
mmpd doctor                                  # cek semua dependency & network
mmpd                                         # jalankan aplikasi (sama dengan `python downloader.py`)
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && rm -rf music-mix-playlist-downloader && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip3 install -U -r requirements.txt --break-system-packages
```

### 🪟 Windows (PowerShell)
*(Catatan: Pastikan Anda telah menginstal Python dan Git terlebih dahulu).*
```powershell
winget install ffmpeg; if (Test-Path music-mix-playlist-downloader) { Remove-Item -Recurse -Force music-mix-playlist-downloader }; git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git; cd music-mix-playlist-downloader; pip install -U -r requirements.txt
```

---

## 🚀 Fitur Kecerdasan Buatan (AI) & Lirik Lanjutan

Versi terbaru ini membawa perombakan masif di sektor pemrosesan Lirik Sinkron (`.lrc`).

### 1. Dual-Engine Lyrics (Sistem Mesin Ganda)
Berbeda dengan pengunduh biasa, Anda diberikan pilihan presisi darimana lirik diambil:
- **🎧 Mesin Spotify/Musixmatch:** Mengambil lirik versi "Studio Asli" yang bersih. Sangat cocok jika Anda mendownload lagu-lagu resmi.
- **✍️ Mesin Spotify (Input Manual):** Fitur dewa bagi Anda yang mendownload lagu *Cover*. Mengingat judul di YouTube (misal `【Rainych】JUSTadICE`) sering kali berbeda dengan di Spotify (`JUSTadICE Rainych`), mesin ini akan memberhentikan sementara layar dan meminta Anda mengetik kata kunci Spotify secara spesifik untuk lagu tersebut!
- **📺 Mesin YouTube Subtitles:** Khusus untuk lagu *Cover* yang liriknya hanya tersedia di CC YouTube agar ketukan dan *timing* nafas sang *cover artist* tepat sasaran 100%.

### 2. Transliterasi Otomatis (Romaji/Pinyin/Latin)
Bosan tidak bisa menyanyikan lagu Jepang, China, atau Korea karena hurufnya *Kanji/Hanzi*?
Sistem dibekali dengan **Deteksi Bahasa Otomatis** (menggunakan *langdetect*). Mesin akan mendeteksi bahasa lagu Anda dan langsung menerjemahkan aksara asing tersebut ke alfabet latin yang bisa Anda baca (Romaji untuk Jepang, Pinyin untuk China, Latin untuk Korea, Thai, Arab, dll), tanpa merusak waktu karaoke (`[00:00.00]`).

### 3. Terjemahan Lirik AI Berdampingan (Dual-Engine Translation)
Ingin tahu arti lagunya? Mesin ini dilengkapi dengan sistem penerjemahan langsung!
Jika diaktifkan, mesin akan menerjemahkan setiap baris lirik ke **Bahasa Indonesia** menggunakan AI (Google Translate). Jika sistem Google memblokir karena Anda mengunduh terlalu banyak (Error 500), mesin ini **memiliki otak cadangan (Fallback)** untuk secara otomatis membelokkan lalu lintas terjemahan ke *MyMemoryTranslator*. Hasil terjemahan akan disuntikkan secara presisi dengan ketukan waktu yang persis sama, tepat di bawah teks aslinya!

### 4. Mode Auto-Organizer (Integrasi Huawei/HarmonyOS)
Bagi pengguna *Huawei Music Player* yang mensyaratkan lirik (`.lrc`) berada terpisah di folder `Internal/Music/Musiclrc`, Anda cukup:
- Mengunduh lirik secara manual di internet (jika lagu tersebut super langka).
- Menaruh file `.lrc` kotor tersebut ke sembarang tempat di dalam folder *Downloads* Anda.
- Menjalankan **Mode 3 (Auto-Organizer)**. CLI akan melacak lirik tersebut, mencocokkannya dengan lagu MP3 Anda, menamai ulang (rename) agar sama persis, memindahkannya ke dalam folder `Musiclrc`, lalu menghapus sisa file sampahnya. Keajaiban sinkronisasi instan!

---

## 🎮 Mode Operasi Utama

Jalankan skrip dengan perintah:
```bash
python downloader.py
```

Anda akan disajikan UI *Cyberpunk* interaktif (gunakan panah *keyboard* ⬆️/⬇️ untuk memilih):

- **📥 1. Mode Utama (Unduhan Baru):** Tempelkan link YouTube (Video tunggal/Playlist/Mix) atau cukup **ketik judul lagu** langsung.
- **🛠️ 2. Mode Retrofit (Otomatis Perbaiki Lagu Lama):** Punya lagu-lagu lama yang tidak bergambar (Cover Art) atau tidak memiliki lirik? Biarkan mesin memindai folder Anda, melacak asal-usulnya di YouTube, dan **menyuntikkan Lirik & Cover ke dalam file MP3/FLAC lama Anda secara otomatis!**
- **📁 3. Mode Pengatur Otomatis:** Mode cerdas untuk menjodohkan file lirik manual yang berantakan dengan MP3 Anda.
- **🎵 4. Mode Spotify:** Unduh lagu, album, atau *playlist* langsung dari tautan Spotify dengan dukungan parsing metadata tingkat lanjut yang meneruskan unduhan tanpa hambatan.
- **☁️  5. Mode SoundCloud:** Dukungan langsung untuk mengunduh trek tunggal maupun *playlist* dari SoundCloud.

---

## 🛡️ Fitur Fundamental
- **Sistem Anti-Duplikat (Smart Archive):** Melompati lagu yang sudah pernah diunduh jika Anda mendownload sebuah Playlist berkali-kali.
- **Injeksi ID3 & Cover Art (FFmpeg):** Gambar *thumbnail* akan ditanam secara paksa dan indah ke dalam file, terdeteksi oleh pemutar mobil (Head Unit) maupun Android/iOS.
- **Resume Otomatis:** Lanjutkan unduhan kapan saja meskipun ada video YouTube yang di-*private* atau terblokir.

> **💡 Lokasi Penyimpanan Cerdas:**  
> Hasil akhir (baik MP3 maupun lirik) otomatis diorganisasikan ke dalam:  
> 📁 **`[Penyimpanan Internal]/Downloads/YT_Downloader/[Nama Playlist]`**
