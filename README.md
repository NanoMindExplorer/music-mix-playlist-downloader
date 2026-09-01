# 🎵 Music Mix & Playlist Downloader (mmpd)

Aplikasi CLI interaktif untuk mendownload lagu dari YouTube, Spotify, dan SoundCloud menjadi audio berkualitas tinggi (MP3/FLAC/WAV). Dilengkapi **Lyrics Engine** yang cerdas untuk mencari lirik karaoke (LRC), menerjemahkan lirik, dan mengubah huruf asing (Jepang/Mandarin/Korea/Thai) menjadi huruf biasa.

---

## ⚡ Instalasi Cepat

Salin & jalankan satu baris perintah di terminal Anda.

> ⚠️ **Catatan:** Untuk memperbarui aplikasi di kemudian hari, Anda cukup menjalankan perintah `mmpd self-update`. Jangan menjalankan ulang perintah instalasi di bawah ini untuk menghindari terhapusnya pengaturan Anda.

### 📱 Android (Termux)
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip install -U -e . --break-system-packages && echo "✅ Install sukses! Jalankan: mmpd"
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip3 install -U -e . --break-system-packages && echo "✅ Install sukses! Jalankan: mmpd"
```

### 🪟 Windows (PowerShell)
```powershell
winget install --id Gyan.FFmpeg -e --source winget; git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git; cd music-mix-playlist-downloader; pip install -U -e .; Write-Host "✅ Install sukses! Jalankan: mmpd"
```

---

## 🎮 Cara Penggunaan

Setelah terinstal, cukup ketik `mmpd` di terminal Anda. Aplikasi akan menampilkan menu interaktif. Anda dapat memilih mode operasi menggunakan tombol panah atas/bawah pada keyboard Anda:

### 📥 1. Mode Utama (YouTube)
Download video tunggal, playlist, atau YouTube Mix. Cukup tempel URL atau **ketik judul lagu** langsung. File akan otomatis tersimpan di folder *Downloads/YT_Downloader*.

### 🛠️ 2. Mode Retrofit (Perbaiki Lagu Lama)
Punya koleksi MP3/FLAC lama tanpa cover art (sampul album) atau lirik? Mode ini akan memindai folder Anda, lalu otomatis mencari dan menyuntikkan lirik serta gambar cover ke dalam file lagu Anda.

### 📁 3. Mode Pengatur Otomatis
Merapikan file lirik (`.lrc`) dan musik Anda secara otomatis. Mencocokkan nama file lirik dengan file lagu, lalu memindahkannya ke folder musik dengan rapi.

### 🎵 4. Mode Spotify
Download lagu, album, atau playlist langsung dari URL Spotify. Cukup tempel URL dan aplikasi akan mencari versi terbaiknya di YouTube secara otomatis.

### ☁️ 5. Mode SoundCloud
Download trek tunggal atau playlist dari SoundCloud dengan mudah.

---

## 🚀 Fitur Unggulan

- **Format Audio Terbaik**: Mendukung MP3 (320kbps), FLAC (Lossless), WAV, atau format original bawaan YouTube.
- **Transliterasi Otomatis**: Secara otomatis mendeteksi lagu berbahasa asing (Jepang, Mandarin, Korea, Thai, dll) dan mengubah lirik aslinya menjadi huruf biasa/latin agar mudah dibaca.
- **Terjemahan Lirik (Bilingual)**: Menambahkan terjemahan lirik tepat di bawah lirik aslinya dengan waktu (timing karaoke) yang presisi.
- **Lirik Lengkap & Sinkron**: Mendukung pencarian lirik karaoke (`.lrc`) yang tersinkronisasi otomatis untuk aplikasi pemutar musik modern.
- **Download Paralel**: Mengunduh playlist besar jauh lebih cepat secara bersamaan (Concurrent Downloads).
- **Aman Lintas-Platform**: Penamaan file otomatis disesuaikan agar aman digunakan di Windows, Linux, maupun Android.

---


## 🔑 Cara Menambahkan Kredensial Spotify (Opsional)

Untuk hasil pencocokan lagu yang jauh lebih akurat (hingga 99%) saat menggunakan **Mode Spotify**, sangat disarankan untuk menambahkan *Spotify API Credentials*. Tanpa kredensial ini, aplikasi hanya akan menebak lagu berdasarkan kemiripan judul.

1. Kunjungi [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) dan *Log in* menggunakan akun Spotify Anda.
2. Klik tombol **Create App**, isi nama dan deskripsi aplikasi secara bebas, centang persetujuan persyaratannya, lalu simpan.
3. Buka aplikasi yang baru Anda buat, lalu klik tombol **Settings**.
4. Anda akan melihat **Client ID**. Untuk melihat sandi rahasianya, klik **View Client Secret**.
5. Salin kedua kode tersebut, lalu buka terminal Anda dan jalankan perintah berikut (ganti teks `KODE_...` dengan kode milik Anda):

**Untuk Linux / Android (Termux):**
```bash
echo 'export SPOTIPY_CLIENT_ID="KODE_CLIENT_ID_ANDA"' >> ~/.bashrc
echo 'export SPOTIPY_CLIENT_SECRET="KODE_CLIENT_SECRET_ANDA"' >> ~/.bashrc
source ~/.bashrc
```

**Untuk Windows (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable('SPOTIPY_CLIENT_ID', 'KODE_CLIENT_ID_ANDA', 'User')
[System.Environment]::SetEnvironmentVariable('SPOTIPY_CLIENT_SECRET', 'KODE_CLIENT_SECRET_ANDA', 'User')
```

Setelah selesai, Anda dapat memverifikasinya dengan mengetik `mmpd doctor` di terminal. Jika berhasil, Anda akan melihat status kredensial telah disetel dengan tanda `[OK]` berwarna hijau.

---

## 🎵 Aplikasi Pemutar Musik yang Disarankan

Untuk mendapatkan pengalaman terbaik dalam mendengarkan lagu dan membaca lirik karaoke hasil unduhan, Anda dapat menggunakan aplikasi pemutar musik berikut:

- **Android**: Poweramp Music Player, Musicolet, Retro Music Player, atau pemutar bawaan Huawei/HarmonyOS.
- **Windows**: MusicBee, foobar2000 (dengan plugin ESLyric).
- **Linux**: Sayonara Music Player.

Pastikan file lirik (`.lrc`) diletakkan di folder yang sama dan memiliki nama yang sama persis dengan file lagu (`.mp3` atau `.flac`) Anda.
