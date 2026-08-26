# YT Mix & Playlist to mp3 320k downloader

Repository untuk mendownload Mix & Playlist dari YouTube dan mengkonversinya menjadi format MP3 dengan kualitas tinggi (320kbps).
Versi terbaru kini hadir dengan **Tampilan CLI Interaktif yang Modern**! 🎉

## Fitur
- **Interactive CLI**: Tampilan terminal yang indah, berwarna, dan mudah digunakan (dibangun dengan `rich`). Anda tidak perlu mengetik prompt atau *flag* rumit lagi!
- Mendownload seluruh video dalam sebuah **YouTube Playlist** atau **YouTube Mix**.
- **Batasi Jumlah Lagu**: Anda akan ditanya secara interaktif apakah ingin membatasi unduhan (misal: hanya 10 lagu pertama).
- Mengonversi otomatis menjadi **MP3** kualitas terbaik (**320kbps**).
- Struktur folder otomatis berdasarkan nama Playlist/Mix.
- Melanjutkan unduhan jika ada video yang error (misal: video dihapus/private).

## Persyaratan Sistem

Sebelum menjalankan script, pastikan Anda telah menginstal `Python 3` dan `FFmpeg`.

### 1. Install FFmpeg
Script ini sangat membutuhkan `ffmpeg` untuk mengkonversi audio ke format MP3.
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
2. Anda akan ditanya: `Apakah Anda ingin membatasi jumlah lagu yang diunduh? (y/n)`
3. Jika Anda menjawab `y`, Anda bisa memasukkan angkanya (misal `10`).
4. Sebuah **Panel Ringkasan** akan muncul untuk memastikan data yang Anda masukkan benar.
5. Konfirmasi unduhan, dan biarkan sistem bekerja!
6. Setelah selesai, Anda akan ditawari apakah ingin mendownload playlist yang lain tanpa harus keluar dari aplikasi.

## Hasil Download
Hasil file `.mp3` akan tersimpan secara berurutan di dalam folder `downloads/Nama_Playlist/`.
