# YT Mix & Playlist to mp3 320k downloader

Repository untuk mendownload Mix & Playlist dari YouTube dan mengkonversinya menjadi format audio berkualitas tinggi.
Versi terbaru kini hadir dengan **Tampilan CLI Interaktif yang Modern**! 🎉

## Fitur
- **Interactive CLI**: Tampilan terminal yang indah, berwarna, dan mudah digunakan (dibangun dengan `rich`).
- Mendownload seluruh video dalam sebuah **YouTube Playlist** atau **YouTube Mix**.
- **Batasi Jumlah Lagu**: Anda akan ditanya secara interaktif apakah ingin membatasi unduhan (misal: hanya 10 lagu pertama).
- **Pilihan Kualitas Audio (Best Quality)**: Kini Anda dapat memilih format output:
  - `MP3 (320kbps)` - Kualitas tinggi, ukuran hemat (Default)
  - `FLAC (Lossless)` - Kualitas audio terbaik / murni tanpa kompresi yang merusak
  - `WAV (Uncompressed)` - Kualitas mentah (studio quality)
  - `Original Audio` - Format murni bawaan YouTube (Opus/M4A)
- Struktur folder otomatis berdasarkan nama Playlist/Mix.
- Melanjutkan unduhan jika ada video yang error (misal: video dihapus/private).

## Persyaratan Sistem

Sebelum menjalankan script, pastikan Anda telah menginstal `Python 3` dan `FFmpeg`.

### 1. Install FFmpeg
Script ini sangat membutuhkan `ffmpeg` untuk mengkonversi audio ke format MP3, FLAC, atau WAV.
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **MacOS:** `brew install ffmpeg`
- **Windows:** Download dari [website resmi FFmpeg](https://ffmpeg.org/download.html) atau gunakan winget: `winget install ffmpeg`

### 2. Install Dependencies Python
Gunakan pip untuk menginstal package yang dibutuhkan (`yt-dlp` dan `rich`):
```bash
pip install -r requirements.txt
```

## Cara Penggunaan

Cukup jalankan script `downloader.py` **tanpa parameter apapun**, dan ikuti instruksi cantik di layar terminal Anda!

```bash
python downloader.py
```

### Langkah Interaktif di Terminal:
1. Anda akan diminta memasukkan `URL YouTube`.
2. Anda akan ditanya apakah ingin membatasi jumlah unduhan lagu.
3. **Baru!** Anda akan diminta memilih kualitas audio `(1: MP3, 2: FLAC, 3: WAV, 4: Original)`.
4. Sebuah **Panel Ringkasan** akan muncul untuk memastikan pengaturan unduhan Anda.
5. Konfirmasi unduhan, dan tunggu prosesnya selesai.
6. Setelah selesai, Anda akan ditawari apakah ingin mendownload playlist yang lain.

## Hasil Download
Hasil file audio akan tersimpan secara otomatis dan terorganisir di dalam folder `downloads/Nama_Playlist/`.
