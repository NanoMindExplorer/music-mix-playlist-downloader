# 🎵 YT Mix & Playlist Downloader Pro (AI Edition)

Aplikasi CLI interaktif *Next-Gen* untuk mendownload YouTube Mix dan Playlist secara otomatis, lalu mengonversinya menjadi audio berkualitas tinggi (MP3/FLAC/WAV). Dilengkapi dengan **Kecerdasan Buatan (AI)** untuk menerjemahkan lirik, mengubah huruf asing ke alfabet Latin (Transliterasi), dan memanajemen perpustakaan musik Anda bak seorang profesional!

---

## ⚡ Cara Instalasi & Pembaruan (One-Line)

Cukup salin (copy) dan jalankan (paste) satu baris perintah di bawah ini pada terminal sesuai dengan perangkat yang Anda gunakan. 
Perintah sakti ini didesain untuk **otomatis menginstal versi terbaru** beserta seluruh dependensi AI-nya. Jalankan ulang perintah ini kapan saja untuk *update* ke versi paling mutakhir!

### 📱 Android (Termux)
*(Catatan: Anda akan dimintai izin akses penyimpanan, tekan Allow/Izinkan)*
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && rm -rf yt-mix-playlist-to-audio-downloader && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git && cd yt-mix-playlist-to-audio-downloader && pip install -U -r requirements.txt --break-system-packages
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && rm -rf yt-mix-playlist-to-audio-downloader && git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git && cd yt-mix-playlist-to-audio-downloader && pip3 install -U -r requirements.txt --break-system-packages
```

### 🪟 Windows (PowerShell)
*(Catatan: Pastikan Anda telah menginstal Python dan Git terlebih dahulu).*
```powershell
winget install ffmpeg; if (Test-Path yt-mix-playlist-to-audio-downloader) { Remove-Item -Recurse -Force yt-mix-playlist-to-audio-downloader }; git clone https://github.com/NanoMindExplorer/yt-mix-playlist-to-audio-downloader.git; cd yt-mix-playlist-to-audio-downloader; pip install -U -r requirements.txt
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

- **📥 1. Mode Utama (Unduhan Baru):** Tempelkan link YouTube (Video tunggal/Playlist/Mix) atau cukup **ketik judul lagu** langsung (contoh: "Avenged Sevenfold Dear God"). Pilih resolusi/format, setel sistem AI Lirik, dan saksikan mesin bekerja.
- **🛠️ 2. Mode Retrofit (Otomatis Perbaiki Lagu Lama):** Punya lagu-lagu lama yang tidak bergambar (Cover Art) atau tidak memiliki lirik? Biarkan mesin memindai folder Anda, melacak asal-usulnya di YouTube, dan **menyuntikkan Lirik & Cover ke dalam file MP3/FLAC lama Anda secara otomatis!** (Bisa pilih lirik saja, atau cover saja).
- **📁 3. Mode Pengatur Otomatis:** Mode cerdas untuk menjodohkan file lirik manual yang berantakan dengan MP3 Anda.

---

## 🛡️ Fitur Fundamental
- **Sistem Anti-Duplikat (Smart Archive):** Melompati lagu yang sudah pernah diunduh jika Anda mendownload sebuah Playlist berkali-kali.
- **Injeksi ID3 & Cover Art (FFmpeg):** Gambar *thumbnail* akan ditanam secara paksa dan indah ke dalam file, terdeteksi oleh pemutar mobil (Head Unit) maupun Android/iOS.
- **Resume Otomatis:** Lanjutkan unduhan kapan saja meskipun ada video YouTube yang di-*private* atau terblokir.

> **💡 Lokasi Penyimpanan Cerdas:**  
> Hasil akhir (baik MP3 maupun lirik) otomatis diorganisasikan ke dalam:  
> 📁 **`[Penyimpanan Internal]/Downloads/YT_Downloader/[Nama Playlist]`**
