# 🎵 Music Mix & Playlist Downloader Pro (AI Edition) v4.0

![CI](https://github.com/NanoMindExplorer/music-mix-playlist-downloader/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
![Tests](https://img.shields.io/badge/tests-376%20passed-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-79%25-brightgreen)
![Version](https://img.shields.io/badge/version-4.0.0-blue)

Aplikasi CLI interaktif *Next-Gen* untuk mendownload YouTube Mix, Playlist Spotify, SoundCloud, dan lainnya secara otomatis, lalu mengonversinya menjadi audio berkualitas tinggi (MP3/FLAC/WAV). Dilengkapi dengan **Kecerdasan Buatan (AI)** untuk menerjemahkan lirik, mengubah huruf asing ke alfabet Latin (Transliterasi), dan memanajemen perpustakaan musik Anda bak seorang profesional!

---

## ⚡ One-Line Install

Salin & jalankan satu baris perintah di terminal Anda. Otomatis install semua dependensi + enable command `mmpd`. Jalankan ulang untuk update ke versi terbaru!

### 📱 Android (Termux)
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && rm -rf music-mix-playlist-downloader && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip install -U -r requirements.txt --break-system-packages && pip install -e . --break-system-packages && echo "✅ Install sukses! Jalankan: mmpd"
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && rm -rf music-mix-playlist-downloader && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip3 install -U -r requirements.txt --break-system-packages && pip3 install -e . --break-system-packages && echo "✅ Install sukses! Jalankan: mmpd"
```

### 🪟 Windows (PowerShell)
```powershell
winget install ffmpeg; if (Test-Path music-mix-playlist-downloader) { Remove-Item -Recurse -Force music-mix-playlist-downloader }; git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git; cd music-mix-playlist-downloader; pip install -U -r requirements.txt; pip install -e .; echo "✅ Install sukses! Jalankan: mmpd"
```

### 🚀 Setelah Install

```bash
mmpd                  # jalankan aplikasi (mode interaktif)
mmpd doctor           # cek semua dependency & network
mmpd --version        # cetak versi
python downloader.py  # alternatif (backward compatible)
```

---

## 🎮 Mode Operasi & Cara Penggunaan

Jalankan `mmpd` (atau `python downloader.py`). Anda akan disajikan UI *Cyberpunk* interaktif (gunakan panah keyboard ⬆️/⬇️ untuk memilih):

### 📥 Mode 1 — Download YouTube
Download video tunggal, playlist, atau Mix dari YouTube. Cukup tempel URL atau **ketik judul lagu** langsung.

**Cara pakai:**
1. Pilih **"📥 1. Mode Utama (Download Lagu/Playlist dari YouTube)"**
2. Tempel URL YouTube (atau ketik judul lagu)
3. Pilih format audio (MP3 320kbps / FLAC / WAV / Original)
4. Aktifkan/nonaktifkan anti-duplikat, lirik, transliterasi, terjemahan
5. Konfirmasi → unduh otomatis ke `Downloads/YT_Downloader/[Nama Playlist]/`

### 🛠️ Mode 2 — Retrofit (Perbaiki Lagu Lama)
Punya koleksi MP3/FLAC lama tanpa cover art atau lirik? Mode ini akan:
- Scan folder Anda untuk file audio
- Cari metadata di YouTube (thumbnail + subtitle)
- Suntikkan cover art ke file audio via FFmpeg
- Cari & tulis lirik via LRCLIB API
- Apply transliterasi + terjemahan jika diminta

**Cara pakai:**
1. Pilih **"🛠️ 2. Mode Retrofit"**
2. Masukkan path folder yang ingin diperbaiki
3. Pilih target: Lirik + Cover / Lirik saja / Cover saja
4. Pilih mesin lirik, transliterasi, terjemahan
5. Konfirmasi → mesin akan memproses setiap file satu per satu

### 📁 Mode 3 — Auto-Organizer (Rapikan File Lirik)
Punya file `.lrc` hasil download manual yang berantakan di folder Downloads? Mode ini akan:
- Match file `.lrc` dengan `.mp3` menggunakan fuzzy string matching (rapidfuzz)
- Rename `.lrc` agar sama persis dengan nama `.mp3`
- Pindahkan `.mp3` ke folder `Music/` dan `.lrc` ke folder `Music/Musiclrc/`
- Khusus Termux: sinkronisasi ke folder Huawei/HarmonyOS Musiclrc

**Cara pakai:**
1. Taruh file `.mp3` dan `.lrc` di folder Downloads
2. Pilih **"📁 3. Mode Pengatur Otomatis"**
3. Konfirmasi → file otomatis dirapikan dan dipindahkan

### 🎵 Mode 4 — Download Spotify
Download lagu, album, atau playlist langsung dari URL Spotify. Memerlukan setup Spotify API credentials untuk ISRC matching (akurasi 99%+).

**Cara pakai:**
1. Pilih **"🎵 4. Mode Spotify"**
2. Tempel URL Spotify (track/album/playlist)
3. Pilih format audio + opsi lirik
4. **Opsional**: Aktifkan ISRC matching (akurasi 99%+) dan concurrent downloads (3x lebih cepat)
5. Konfirmasi → setiap track di-search di YouTube lalu didownload

**Setup Spotify API (recommended untuk ISRC matching):**
```bash
# 1. Buka https://developer.spotify.com/dashboard → Create app (gratis)
# 2. Dapatkan Client ID + Client Secret
# 3. Set environment variables:
echo 'export SPOTIPY_CLIENT_ID="your_client_id"' >> ~/.bashrc
echo 'export SPOTIPY_CLIENT_SECRET="your_client_secret"' >> ~/.bashrc
source ~/.bashrc
# 4. Verifikasi:
mmpd doctor    # harus muncul "Spotify ISRC matching AKTIF"
```

### ☁️ Mode 5 — Download SoundCloud
Download trek tunggal atau playlist dari SoundCloud.

**Cara pakai:**
1. Pilih **"☁️ 5. Mode SoundCloud"**
2. Tempel URL SoundCloud atau ketik judul lagu
3. Pilih format + opsi lirik
4. Konfirmasi → unduh otomatis ke `Downloads/YT_Downloader/SoundCloud_Downloads/`

---

## 🚀 Fitur AI & Lirik Lanjutan

### 1. Dual-Engine Lyrics (Sistem Mesin Ganda)
Pilihan presisi darimana lirik diambil:

| Mesin | Sumber | Cocok untuk |
|---|---|---|
| 🎧 Mesin 1 | LRCLIB API → syncedlyrics (Musixmatch/NetEase) | Lagu asli (original) |
| ✍️ Mesin 2 | LRCLIB/syncedlyrics (input judul manual) | Lagu cover (judul Spotify berbeda dari YouTube) |
| 📺 Mesin 3 | YouTube Subtitles (CC) | Lagu cover (timing 100% akurat dengan video) |

**Fallback chain otomatis**: LRCLIB (gratis, no-auth, database terbesar) → syncedlyrics → YouTube CC. Semua hasil di-cache di SQLite (TTL 30 hari) untuk 10x speedup saat re-download.

### 2. Transliterasi Otomatis (Romaji/Pinyin/Latin)
Tidak bisa membaca huruf Kanji/Hanzi/Hangul? Sistem akan mendeteksi bahasa otomatis (langdetect) dan mengubah aksara asing ke alfabet Latin:
- **Jepang** → Romaji (pykakasi, Hepburn)
- **Mandarin** → Pinyin (pypinyin)
- **Korea** → Revised Romanization (korean_romanizer)
- **Thai/Arab/Rusia/dll** → Latin (anyascii fallback)

Timestamp karaoke `[00:00.00]` tetap utuh, tidak rusak.

### 3. Terjemahan Lirik Bilingual (AI Translation)
Terjemahan setiap baris lirik ke **Bahasa Indonesia**, ditambahkan tepat di bawah teks asli dengan timestamp identik (standar LRC bilingual):
```
[00:01.23] Hello world
[00:01.23] Halo dunia
```

**Dual-engine translation**: Google Translate (utama) → MyMemory (fallback kalau Google rate-limit). Hasil di-cache di SQLite (tidak pernah expire) — re-translate lirik yang sama = 100% cache hit, skip API call.

### 4. ISRC-Based YouTube Matching (Akurasi 99%+)
Untuk Spotify downloads, sistem pakai ISRC (International Standard Recording Code) untuk match track Spotify dengan video YouTube yang tepat:
- **Strategi 1**: ISRC match (akurasi 99%+) — extract ISRC dari metadata top-3 YouTube candidates
- **Strategi 2**: Fuzzy + duration verification (akurasi ~90%) — fuzzy title match + verifikasi durasi <5 detik
- **Strategi 3**: Pure fuzzy (threshold 80%) — fallback terakhir

### 5. Concurrent Downloads (3x Speedup)
Download playlist Spotify dengan 3 worker paralel (ThreadPoolExecutor). Playlist 50 lagu: ~250s (sequential) → ~85s (concurrent).

### 6. SQLite Cache (10x Speedup untuk Re-Download)
- **Translation cache**: SHA256(source_text + lang) → translated_text (never expire)
- **Lyrics cache**: SHA256(title + artist + isrc) → lyrics (TTL 30 hari)
- **Storage**: `~/.local/share/mmpd/cache/cache.db` (Linux) atau `$PREFIX/var/cache/mmpd/cache.db` (Termux)

Playlist 50 lagu re-download dalam 30 hari → **0 API calls** (semua cache hit).

---

## 🛡️ Fitur Fundamental

- **Sistem Anti-Duplikat (Smart Archive)**: Melompati lagu yang sudah pernah diunduh jika Anda mendownload sebuah Playlist berkali-kali.
- **Injeksi ID3 & Cover Art (FFmpeg)**: Gambar thumbnail ditanam ke dalam file audio, terdeteksi oleh pemutar mobil (Head Unit) maupun Android/iOS.
- **Atomic Write**: Semua penulisan file lirik pakai pattern `tempfile + os.replace()` — file tidak bisa korup jika proses crash di tengah jalan.
- **Structured Logging**: Semua aktivitas tercatat di file log dengan rotation (10MB/file, keep 5 files):
  - Linux: `~/.local/share/mmpd/logs/mmpd.log`
  - Termux: `$PREFIX/var/log/mmpd/mmpd.log`
  - Windows: `%LOCALAPPDATA%/mmpd/logs/mmpd.log`
- **Resume Otomatis**: Lanjutkan unduhan kapan saja meskipun ada video YouTube yang di-private atau terblokir.
- **Filename Aman Lintas-Platform**: `restrictfilenames=True` — karakter ilegal Windows NTFS (`/:*?"<>|`) otomatis dihindari.

> **💡 Lokasi Penyimpanan Cerdas:**
> Hasil akhir (baik MP3 maupun lirik) otomatis diorganisasikan ke dalam:
> 📁 **`[Penyimpanan Internal]/Downloads/YT_Downloader/[Nama Playlist]`**

---

## 🩺 `mmpd doctor` — Diagnostik

Jalankan `mmpd doctor` untuk cek:
1. **System binaries**: ffmpeg, git (PATH + version)
2. **Python modules**: 14 required modules (yt-dlp, rich, syncedlyrics, spotipy, dll)
3. **Spotify API credentials**: SPOTIPY_CLIENT_ID/SECRET (untuk ISRC matching)
4. **Network connectivity**: TCP connect test ke 6 endpoint (LRCLIB, iTunes, Spotify, YouTube, SoundCloud)
5. **Storage & permissions**: writable check untuk output/log/cache dir + Termux storage permission
6. **Configuration**: print AppConfig paths (home, output, log, config)

**Exit codes**: 0 = semua OK, 1 = ada failure (dep missing), 2 = hanya warning (network unreachable).

---

## 📊 Format Audio yang Didukung

| Format | Codec | Quality | Use Case |
|---|---|---|---|
| MP3 | mp3 | 320kbps | Default — kompatibel semua player |
| FLAC | flac | Lossless | Best quality murni — audiophile |
| WAV | wav | Uncompressed | Mentah — editing/professional |
| Original | best | Bawaan YouTube | Tidak konversi — fastest |

> **Catatan**: WAV tidak support embed cover art (limitasi format). Pilih MP3 atau FLAC untuk cover art.

---

## 🌍 Bahasa Transliterasi yang Didukung

| Bahasa | Aksara | Konversi | Library |
|---|---|---|---|
| Jepang | Kanji/Hiragana/Katakana | Romaji (Hepburn) | pykakasi |
| Mandarin | Hanzi (Simplified/Traditional) | Pinyin | pypinyin |
| Korea | Hangul | Revised Romanization | korean_romanizer |
| Thai | Thai script | Latin | anyascii |
| Arab | Arabic script | Latin | anyascii |
| Rusia | Cyrillic | Latin | anyascii |
| Lainnya | Aksara non-Latin | Latin | anyascii (fallback universal) |

Bahasa yang sudah pakai alfabet Latin (Inggris, Indonesia, Spanyol, dll) otomatis di-skip (tidak perlu transliterasi).

---

## 🔧 Entry Points (Cara Menjalankan)

Setelah install (`pip install -e .`), ada 3 cara menjalankan:

```bash
mmpd                  # console script (recommended, setelah pip install)
python -m mmpd        # module entry (alternatif)
python downloader.py  # legacy entry (backward compatible)
```

Subcommands:
```bash
mmpd                  # mode interaktif (menu 5 mode)
mmpd doctor           # diagnostik
mmpd --version        # cetak versi
```

---

## 🎵 Panduan Pemutar Musik (Cover Art & Lirik Sinkron `.lrc`)

Panduan lengkap untuk Android, Windows, dan Ubuntu/Linux.
Cocok untuk memutar lagu hasil download dari Music Mix Playlist Downloader Pro (mmpd).

### 📱 Untuk Android

#### 1. Poweramp Music Player (RECOMMENDED)
Poweramp adalah pemutar musik paling powerfull di Android. Dukungan penuh untuk cover art, lirik sinkron (`.lrc`), dan berbagai format audio.

**Fitur:**
- Lirik sinkron karaoke (highlight per baris sesuai timing)
- Cover art resolusi tinggi (embed & external)
- Equalizer bawaan
- Dukung MP3, FLAC, WAV, M4A, APE, dsb.

**Cara Menerapkan:**
1. Download dari Play Store: **Poweramp Music Player**
2. Buka Poweramp → Settings → Pastikan folder musik Anda di-scan.
3. Aktifkan Lyrics dengan cara: Buka lagu → ketuk ikon "Lirik" di pojok kanan bawah.

**Struktur file yang benar:**
```text
📁 Music/
├── 🎵 Adele - Hello.mp3   (cover art sudah tertanam di dalam)
└── 📄 Adele - Hello.lrc    (lirik sinkron, nama harus SAMA PERSIS dengan mp3)
```

**Jika lirik tidak muncul:**
- Pastikan file `.lrc` dan `.mp3` di folder yang sama.
- Pastikan nama file sama persis (case-sensitive).
- Buka Settings → Lyrics → pilih "Online + Local".

#### 2. Musicolet
Musicolet adalah pemutar gratis tanpa iklan dengan dukungan lirik sinkron dan multi-queue.

**Fitur:**
- Lirik sinkron (`.lrc`) dan plain text
- Cover art dari tag ID3 atau file `folder.jpg`
- Sangat ringan dan offline

**Cara Menerapkan:**
1. Download dari Play Store: **Musicolet**
2. Buka app → izinkan akses penyimpanan.
3. Buka Settings → "Lyrics" → Aktifkan "Show lyrics".
4. "Lyrics source" → Pilih "Local .lrc files".
*(Struktur file sama seperti Poweramp: mp3 + lrc di folder yang sama).*

#### 3. Huawei Music (untuk pengguna Huawei/HarmonyOS)
Jika Anda menggunakan CLI mmpd di Termux dan mengaktifkan opsi "Sinkronisasi Lirik khusus Huawei/HarmonyOS", lirik akan otomatis disalin ke folder `Internal/Music/Musiclrc/`.

**Cara Menerapkan:**
1. Pastikan opsi sinkronisasi Huawei aktif saat download/retrofit.
2. Buka Huawei Music app.

**Folder struktur:**
```text
📁 Internal/Music/
├── 🎵 Song1.mp3
├── 🎵 Song2.mp3
└── 📁 Musiclrc/
    ├── 📄 Song1.lrc
    └── 📄 Song2.lrc
```
Putar lagu → lirik akan muncul otomatis di layar karaoke.

#### 4. Retro Music Player
**Fitur:**
- UI modern dengan animasi
- Lirik sinkron dengan tampilan karaoke
- Cover art dari tag atau online (jika terhubung internet)

**Cara Menerapkan:**
1. Download dari Play Store.
2. Settings → Lyrics → Aktifkan "Synced Lyrics".
3. Letakkan file `.lrc` di folder yang sama dengan musik.

---

### 🪟 Untuk Windows

#### 1. MusicBee (RECOMMENDED)
MusicBee adalah pemutar musik desktop terbaik untuk Windows. Sangat mendukung manajemen library besar, lirik, dan cover art.

**Fitur:**
- Lirik sinkron (`.lrc`) dengan tampilan karaoke
- Cover art resolusi tinggi (embed & external `folder.jpg`)
- Auto-tagging dan auto-organize library
- Dukung MP3, FLAC, WAV, M4A, dsb.

**Cara Menerapkan:**
1. Download dari [musicbee.com](https://getmusicbee.com/).
2. Buka MusicBee → Preferences → "Library" → Add folder musik Anda.
3. "Tags" → Pastikan "Embed artwork" dicentang.

**Aktifkan Lirik:**
1. Preferences → "Layout" (1) → pilih layout yang punya panel "Lyrics".
2. Preferences → "Lyrics" → "Save lyrics to music file" → centang.
3. "Lyrics file naming" → set ke `%filename%.lrc`.

**Struktur file:**
```text
📁 D:\Music├── 🎵 Adele - Hello.mp3   (cover art tertanam)
└── 📄 Adele - Hello.lrc    (lirik sinkron)
```
Putar lagu → lirik muncul di panel samping.

#### 2. foobar2000
Pemutar musik ringan dan customizable dengan dukungan lirik via plugin.

**Cara Menerapkan:**
1. Download dari [foobar2000.org](https://www.foobar2000.org/).
2. Install plugin **ESLyric**:
   - Download ESLyric dari forum foobar2000.
   - Ekstrak ke folder `foobar2000/components/`.
3. Buka foobar2000 → File → Preferences → Display → Columns UI → Tambahkan panel "ESLyric" ke layout.
4. ESLyric akan otomatis baca file `.lrc` di folder yang sama dengan musik.

#### 3. VLC Media Player
VLC bisa memutar audio dengan lirik sinkron via plugin (atau load subtitle).

**Cara Menerapkan:**
1. Download VLC dari [videolan.org](https://www.videolan.org/).
2. Buka file musik (`.mp3`) di VLC.
3. Drag & drop file `.lrc` ke jendela VLC, atau:
4. Klik menu "Subtitle" → "Add Subtitle File" → pilih file `.lrc`.
5. Lirik akan muncul di atas video (VLC akan menampilkan visualizer audio + lirik).

---

### 🐧 Untuk Ubuntu / Linux

#### 1. Sayonara Music Player (RECOMMENDED)
Sayonara adalah pemutar musik cepat dan ringan untuk Linux dengan dukungan lirik bawaan.

**Cara Install:**
```bash
sudo apt update
sudo apt install sayonara
```

**Cara Menerapkan:**
1. Buka Sayonara → Settings → "Library" → Add folder musik Anda.
2. Aktifkan Lirik: Settings → "Lyrics" → Aktifkan "Show lyrics".
3. "Lyrics server" → pilih "Local".

**Struktur file:**
```text
📁 ~/Music/
├── 🎵 Adele - Hello.mp3
└── 📄 Adele - Hello.lrc
```
