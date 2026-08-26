# 🎵 YT Mix & Playlist Downloader Pro

Aplikasi CLI interaktif untuk mendownload YouTube Mix dan Playlist secara otomatis, lalu mengonversinya menjadi audio berkualitas tinggi (MP3/FLAC/WAV) langsung ke folder *Downloads* Anda.

---

## ⚡ Cara Instalasi (One-Line Install)

Cukup salin (copy) dan jalankan (paste) satu baris perintah di bawah ini pada terminal sesuai dengan perangkat yang Anda gunakan. Perintah ini akan otomatis menginstal semua kebutuhan sistem, mengunduh repositori ini, dan menyiapkan aplikasinya untuk Anda.

### 📱 Android (Termux)
```bash
pkg update -y && pkg install -y python ffmpeg git && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-mp3-320k-downloader.git && cd yt-mix-playlist-to-mp3-320k-downloader && pip install -r requirements.txt
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-mp3-320k-downloader.git && cd yt-mix-playlist-to-mp3-320k-downloader && pip3 install -r requirements.txt --break-system-packages
```

### 🪟 Windows (PowerShell)
*(Catatan: Pastikan Anda telah menginstal Python, Git, dan FFmpeg terlebih dahulu di Windows Anda).*
```powershell
winget install ffmpeg; git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-mp3-320k-downloader.git; cd yt-mix-playlist-to-mp3-320k-downloader; pip install -r requirements.txt
```

---

## 🚀 Cara Penggunaan

Setelah instalasi selesai, pastikan Anda berada di dalam folder aplikasinya (`cd yt-mix-playlist-to-mp3-320k-downloader`), lalu jalankan perintah berikut:

```bash
python downloader.py
```

### Panduan Interaktif:
Aplikasi akan memandu Anda melalui antarmuka (UI) terminal yang cantik:
1. **Masukkan URL YouTube:** Paste *link* (tautan) YouTube Mix atau Playlist yang ingin diunduh.
2. **Pembatasan Lagu (Opsional):** Anda bisa memilih untuk mengunduh semua lagu atau membatasinya (misal: hanya 5 lagu pertama saja).
3. **Pilih Kualitas Audio (Best Quality):**
   - `[1] MP3 (320kbps)` - Kualitas standar tertinggi, hemat penyimpanan.
   - `[2] FLAC (Lossless)` - Kualitas murni tanpa merusak detail suara (ukuran besar).
   - `[3] WAV (Uncompressed)` - Kualitas mentah studio (ukuran sangat besar).
   - `[4] Original Audio` - File audio asli dari YouTube (biasanya Opus/M4A) tanpa konversi.
4. **Mulai Unduhan:** Setelah Anda mengkonfirmasi panel ringkasan, bar progres (Progress Bar) modern akan muncul dan menampilkan kecepatan unduhan (MB/s) serta estimasi waktu.

> **💡 Informasi Penyimpanan Berkas:**  
> Anda tidak perlu mencari-cari file hasil unduhan. Semua file musik akan langsung dikirim dan ditata rapi ke dalam folder bawaan perangkat Anda di:  
> 📁 **`[Penyimpanan Internal]/Downloads/YT_Downloader/[Nama Playlist]`**
