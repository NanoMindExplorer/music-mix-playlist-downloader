# 🎵 Music Mix & Playlist Downloader (mmpd)

[![CI](https://github.com/NanoMindExplorer/music-mix-playlist-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/NanoMindExplorer/music-mix-playlist-downloader/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive CLI application to download songs, albums, and playlists from YouTube, Spotify, and SoundCloud into high-quality audio (MP3/FLAC/WAV). Powered by an intelligent **Lyrics Engine** that fetches synchronized karaoke lyrics (LRC), translates lyrics, and transliterates foreign scripts (Japanese, Chinese, Korean, Thai) into readable Romanized/Latin text.

---

## ⚡ Quick Installation

Copy & run the one-line command for your platform in your terminal:

> ⚠️ **Note:** To update the application later, simply run `mmpd self-update`. Do not re-run the installation commands below to avoid overwriting your custom configuration.

### 📱 Android (Termux)
```bash
termux-setup-storage; pkg update -y && pkg install -y python ffmpeg git && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip install -U -e . --break-system-packages && echo "✅ Installation successful! Run: mmpd"
```

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg git && git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git && cd music-mix-playlist-downloader && pip3 install -U -e . --break-system-packages && echo "✅ Installation successful! Run: mmpd"
```

### 🪟 Windows (PowerShell)
```powershell
winget install --id Gyan.FFmpeg -e --source winget; git clone https://github.com/NanoMindExplorer/music-mix-playlist-downloader.git; cd music-mix-playlist-downloader; pip install -U -e .; Write-Host "✅ Installation successful! Run: mmpd"
```

---

## 🎮 How to Use

Once installed, simply type `mmpd` in your terminal to launch the interactive interface. You can navigate the menu using your keyboard's arrow keys:

```bash
mmpd                  # Interactive menu (5 modes)
mmpd doctor           # Diagnostics & dependency check
mmpd self-update      # Update to the latest release
mmpd --version        # Display current version
```

### 📥 1. Main Mode (YouTube)
Download single videos, playlists, or YouTube Mixes. Simply paste a URL or **type song titles** to search directly. Audio files are automatically saved to your *Downloads/YT_Downloader* directory.

### 🛠️ 2. Retrofit Mode (Fix Existing Songs)
Have an existing collection of MP3/FLAC files missing album artwork or lyrics? Retrofit mode scans your folder, searches for missing metadata, and automatically embeds album covers and synchronized lyrics into your tracks.

### 📁 3. Auto Organizer Mode
Automatically cleans up and organizes your lyrics (`.lrc`) and music files. Accurately matches lyric filenames with corresponding song files and moves them into your organized music folder.

### 🎵 4. Spotify Mode
Download tracks, albums, or playlists directly from Spotify URLs. Simply paste the link, and `mmpd` will find and download the highest-quality matching audio from YouTube automatically.

### ☁️ 5. SoundCloud Mode
Seamlessly download individual tracks or full playlists directly from SoundCloud.

---

## 🚀 Key Features

- **High-Fidelity Audio**: Supports MP3 (up to 320kbps), FLAC (Lossless), WAV, or original source formats.
- **Smart Transliteration**: Automatically detects foreign language lyrics (Japanese Romaji, Chinese Pinyin/Jyutping, Korean Romaja, Thai RTGS) and transliterates them into Latin characters for effortless reading.
- **Bilingual Lyric Translation**: Adds lyric translations directly below original lines while preserving precise karaoke synchronization timing.
- **Synchronized Karaoke Lyrics**: Downloads synchronized `.lrc` files compatible with modern desktop and mobile music players.
- **Concurrent Downloads**: Multi-threaded parallel processing speeds up large playlist downloads significantly.
- **Cross-Platform Safe**: Automatic filename sanitization ensures valid, safe filenames across Windows, Linux, and Android (Termux).

---

## 🔑 Spotify API Credentials (Optional)

For significantly higher accuracy (up to 99% via ISRC & Spotify metadata matching) when using **Spotify Mode**, providing Spotify API credentials is recommended. Without credentials, track matching relies on title heuristics.

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in with your Spotify account.
2. Click **Create App**, fill in any app name and description, accept the terms of service, and click **Save**.
3. Open your newly created app and navigate to **Settings**.
4. Locate your **Client ID**. Click **View Client Secret** to reveal and copy your secret key.
5. In your terminal, run the following commands (replace `YOUR_...` with your actual credentials):

**Linux / Android (Termux):**
```bash
echo 'export SPOTIPY_CLIENT_ID="YOUR_CLIENT_ID"' >> ~/.bashrc
echo 'export SPOTIPY_CLIENT_SECRET="YOUR_CLIENT_SECRET"' >> ~/.bashrc
source ~/.bashrc
```

**Windows (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable('SPOTIPY_CLIENT_ID', 'YOUR_CLIENT_ID', 'User')
[System.Environment]::SetEnvironmentVariable('SPOTIPY_CLIENT_SECRET', 'YOUR_CLIENT_SECRET', 'User')
```

To verify your configuration, run `mmpd doctor` in your terminal. A green `[OK]` status will indicate successful configuration.

---

## 🎵 Recommended Music Players

For the best experience enjoying synchronized karaoke lyrics and embedded album artwork, we recommend the following music players:

- **Android**: [Poweramp Music Player](https://play.google.com/store/apps/details?id=com.maxmpz.audioplayer), [Musicolet](https://play.google.com/store/apps/details?id=in.krosbits.musicolet), Retro Music Player, or stock Huawei/HarmonyOS Music Player.
- **Windows**: [MusicBee](https://getmusicbee.com/), [foobar2000](https://www.foobar2000.org/) (with the ESLyric component).
- **Linux**: [Sayonara Music Player](https://sayonara-player.com/).

> 💡 **Tip:** Ensure the `.lrc` lyric file is kept in the same folder and has the exact same base filename as the corresponding music file (e.g., `Song.mp3` and `Song.lrc`).
