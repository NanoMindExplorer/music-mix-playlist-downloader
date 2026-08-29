with open("README.md", "r") as f:
    content = f.read()

# The section starts at: 🎵 Panduan Pemutar Musik
import re
idx = content.find("🎵 Panduan Pemutar Musik")
if idx != -1:
    main_readme = content[:idx]
    unformatted = content[idx:]
    
    formatted = """## 🎵 Panduan Pemutar Musik (Cover Art & Lirik Sinkron `.lrc`)

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
📁 D:\Music\
├── 🎵 Adele - Hello.mp3   (cover art tertanam)
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
"""
    with open("README.md", "w") as f:
        f.write(main_readme + formatted)
    print("Formatted README.md successfully.")
