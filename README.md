# 🎵 YT Mix & Playlist Downloader Pro

Aplikasi CLI interaktif untuk mendownload YouTube Mix dan Playlist secara otomatis, lalu mengonversinya menjadi audio berkualitas tinggi (MP3/FLAC/WAV) langsung ke folder *Downloads* Anda.

---

## ⚡ Cara Instalasi & Pembaruan (One-Line)

Cukup salin (copy) dan jalankan (paste) satu baris perintah di bawah ini pada terminal sesuai dengan perangkat yang Anda gunakan. 
Perintah sakti ini didesain untuk **otomatis menginstal versi terbaru** dari aplikasi beserta seluruh dependensinya (`yt-dlp` dkk). Anda juga bisa menjalankan ulang perintah ini kapan saja untuk memperbarui (*update*) ke versi paling mutakhir!

### 📱 Android (Termux)
*(Catatan: Anda akan dimintai izin akses penyimpanan, tekan Allow/Izinkan)*
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && rm -rf yt-mix-playlist-to-audio-downloader && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git && cd yt-mix-playlist-to-audio-downloader && pip install -U -r requirements.txt
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && rm -rf yt-mix-playlist-to-audio-downloader && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git && cd yt-mix-playlist-to-audio-downloader && pip3 install -U -r requirements.txt --break-system-packages
```

### 🪟 Windows (PowerShell)
*(Catatan: Pastikan Anda telah menginstal Python dan Git terlebih dahulu di Windows Anda).*
```powershell
winget install ffmpeg; if (Test-Path yt-mix-playlist-to-audio-downloader) { Remove-Item -Recurse -Force yt-mix-playlist-to-audio-downloader }; git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git; cd yt-mix-playlist-to-audio-downloader; pip install -U -r requirements.txt
```

---

## 🚀 Cara Penggunaan

Setelah instalasi selesai, pastikan Anda berada di dalam folder aplikasinya (`cd yt-mix-playlist-to-audio-downloader`), lalu jalankan perintah berikut:

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

---

## ✨ Fitur Unggulan
- **Mode Retrofit Otomatis (Perbaikan Metadata Lama)**: Punya lagu-lagu lama yang diunduh sebelumnya tapi belum ada Cover Art atau Lirik? CLI ini bisa memindai seluruh folder Anda, mencarikan metadata aslinya di YouTube, lalu menyuntikkan Lirik & Thumbnail ke dalam file MP3/FLAC lama Anda secara otomatis! (Tanpa perlu unduh audionya ulang).
- **Interactive CLI (Next-Gen UI)**: Tampilan terminal yang indah bergaya *Cyberpunk/Hacker*, dilengkapi dengan menu navigasi berbasis *Arrow Key* (dibangun dengan `rich` & `questionary`).
- **Pencarian Cerdas (Search by Text)**: Tidak mau repot *copy-paste* URL? Cukup ketikkan judul lagunya (misal: "Linkin Park Numb"), dan CLI otomatis mencarikan serta mengunduh hasil terbaik untuk Anda!
- **Download & Sinkronisasi Lirik (Karaoke Mode)**: Otomatis mendownload subtitle resmi lagu dari YouTube dan mengubahnya menjadi file `.lrc`. Sinkron dengan pemutar musik di HP Anda.
- **Sistem Anti-Duplikat (Smart Archive)**: Aplikasi akan mengingat lagu apa saja yang sudah Anda unduh. Jika Anda mengunduh playlist yang sama di masa depan, aplikasi **otomatis melompati (skip) lagu lama** dan hanya mengunduh lagu yang baru ditambahkan!
- **Embed Cover Art & Metadata**: Otomatis menyematkan Thumbnail YouTube sebagai *Album Cover* beserta informasi judul, artis, dan tahun lagu langsung ke dalam file musik Anda. Tampil sangat profesional di HP atau pemutar musik mobil!
- Mendownload seluruh video dalam sebuah **YouTube Playlist** atau **YouTube Mix**.
- **Penyimpanan Otomatis**: Semua lagu kini otomatis tersimpan di folder bawaan `Downloads` di perangkat/komputer Anda (termasuk deteksi pintar untuk Termux Android).
- Melanjutkan unduhan jika ada video yang error (misal: video dihapus/private).

> **💡 Informasi Penyimpanan Berkas:**  
> Anda tidak perlu mencari-cari file hasil unduhan. Semua file musik akan langsung dikirim dan ditata rapi ke dalam folder bawaan perangkat Anda di:  
> 📁 **`[Penyimpanan Internal]/Downloads/YT_Downloader/[Nama Playlist]`**
