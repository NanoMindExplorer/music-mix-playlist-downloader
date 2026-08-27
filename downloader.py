import os
import sys
import shutil
import glob
from pathlib import Path
import yt_dlp
import questionary
from rich.console import Console
from rich import box
from rich.panel import Panel
from urllib.error import HTTPError
import urllib.request
import re
import json
from spotify_parser import parse_spotify_url
try:
    import syncedlyrics
    # Patch bawaan syncedlyrics yang membatasi timeout koneksi menjadi 2 detik (terlalu singkat untuk Termux/koneksi lambat)
    from syncedlyrics.providers.base import TimeoutSession
    def custom_request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (10, 30)) # Connect 10s, Read 30s
        return super(TimeoutSession, self).request(method, url, **kwargs)
    TimeoutSession.request = custom_request
except ModuleNotFoundError:
    print("\n❌ Modul 'syncedlyrics' belum terinstal!")
    print("Silakan jalankan perintah berikut untuk menginstal pembaruan:")
    print("pip install -U -r requirements.txt\n")
    sys.exit(1)
from rich.table import Table
from rich.text import Text
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn
)

console = Console()

class YTDLPLogger:
    """Custom Logger untuk membisukan log bawaan yt-dlp agar UI tetap bersih"""
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        # Abaikan error ringan dari metadata, thumbnail, subtitle, atau limitasi YouTube 429 agar UI tidak hancur
        msg_lower = msg.lower()
        if not any(k in msg_lower for k in ["metadata", "thumbnail", "subtitles", "429", "too many requests"]):
            console.print(f"[bold red]❌ Error yt-dlp:[/bold red] {msg}")

def check_dependencies():
    missing = []
    if not shutil.which('ffmpeg'): missing.append("FFmpeg")
    return missing

def print_banner():
    console.clear()
    banner = Text()
    banner.append("✦ ════════════════════════════════════════════ ✦\n", style="bold cyan")
    banner.append(" High-Fidelity & Lossless Audio Engine \n", style="italic bright_white")
    banner.append("✦ ════════════════════════════════════════════ ✦\n\n", style="bold cyan")
    banner.append("Artfully Crafted by\n", style="dim white")
    banner.append("✦ NanoMindExplorer ✦", style="bold bright_yellow")
    banner.justify = "center"
    console.print(Panel(
        banner, box=box.DOUBLE, border_style="bold magenta", padding=(1, 4),
        title="[bold bright_white on magenta] 🎵 YT AUDIO DOWNLOADER PRO [/bold bright_white on magenta]",
        title_align="center",
        subtitle="[bold white]v3.0[/bold white] [dim]• Interactive CLI & Retrofit Engine[/dim]",
        subtitle_align="center"
    ))
    console.print()

def get_default_path():
    if "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
        return str(Path.home() / "storage" / "downloads" / "YT_Downloader")
    return str(Path.home() / "Downloads" / "YT_Downloader")

def sync_huawei_lrc(lrc_path):
    """Menyalin file .lrc ke folder khusus Musiclrc bawaan Huawei/Android"""
    if "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
        # Gunakan path shared/Music agar dijamin mengarah ke Internal Storage/Music
        huawei_dir = os.path.join(str(Path.home()), "storage", "shared", "Music", "Musiclrc")
        try:
            os.makedirs(huawei_dir, exist_ok=True)
            filename = os.path.basename(lrc_path)
            # Pastikan file lrc yang di-copy memang ada
            if os.path.exists(lrc_path):
                shutil.copy2(lrc_path, os.path.join(huawei_dir, filename))
        except Exception as e:
            console.print(f"[dim yellow]⚠️ Gagal sinkronisasi LRC ({os.path.basename(lrc_path)}): {e}[/dim yellow]")

def _atomic_write_text(path, content):
    """
    Fix R2 (atomic write): Tulis file secara atomik untuk mencegah korupsi
    jika proses crash di tengah penulisan (mis. Ctrl+C saat menulis LRC).
    
    Pattern: tulis ke temporary file di direktori yang sama, lalu os.replace()
    untuk swap atomik (atomic rename) ke path final. os.replace() adalah
    operasi atomic di POSIX & Windows, sehingga file final selalu utuh
    (versi lama atau versi baru — tidak pernah setengah jadi).
    """
    import tempfile
    dir_path = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix='.atomic_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Bersihkan temporary file jika os.replace() gagal
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

def process_transliteration(lrc_path, transliterate_mode):
    """Mengubah huruf Jepang/Mandarin/Korea/Lainnya di dalam file LRC menjadi Romaji/Pinyin/Latin"""
    if not os.path.exists(lrc_path): return
    if transliterate_mode.startswith("❌ 1"): return
    
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        import re
        # Fungsi untuk menghapus tag waktu [00:00.00] agar tidak mengganggu deteksi bahasa
        pure_text = " ".join([re.sub(r'\[.*?\]', '', line).strip() for line in lines if line.strip()])
        if not pure_text: return
        
        # Tentukan bahasa target
        target_lang = ""
        if transliterate_mode.startswith("🤖 4"):
            import langdetect
            target_lang = langdetect.detect(pure_text)
            # Jangan ubah jika sudah menggunakan alfabet Latin (Inggris, Indonesia, dll)
            if target_lang in ['en', 'id', 'es', 'fr', 'de', 'it', 'nl', 'tl']: return
        elif transliterate_mode.startswith("🇯🇵 2"):
            target_lang = "ja"
        elif transliterate_mode.startswith("🇨🇳 3"):
            target_lang = "zh-cn"
            
        new_lines = []
        if target_lang == "ja":
            import pykakasi
            k = pykakasi.kakasi()
            for line in lines:
                if line.strip() and not line.strip().startswith('['):
                    # Hanya konversi teks liriknya, amankan tag waktu
                    time_tag = re.match(r'\[.*?\]', line)
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    conv = k.convert(text)
                    new_text = "".join([item['hepburn'] for item in conv])
                    new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
                else:
                    new_lines.append(line)
                    
        elif target_lang in ["zh-cn", "zh-tw"]:
            from pypinyin import pinyin, Style
            for line in lines:
                if line.strip() and not line.strip().startswith('['):
                    time_tag = re.match(r'\[.*?\]', line)
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    py_list = pinyin(text, style=Style.NORMAL)
                    # Fix B3 (bug logika): kode lama memakai `item[0].isascii() == False`
                    # yang SELALU False karena pypinyin selalu menghasilkan ASCII.
                    # Akibatnya spasi antar kata tidak pernah disisipkan, sehingga
                    # output Pinyin menempel tanpa pemisah (mis. "wǒaìshàngwǎng").
                    # Versi baru: gabungkan setiap suku kata Pinyin dengan spasi
                    # sehingga terbaca natural ("wǒ ài shàng wǎng").
                    new_text = " ".join([item[0] for item in py_list])
                    new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
                else:
                    new_lines.append(line)
                    
        elif target_lang == "ko":
            from korean_romanizer.romanizer import Romanizer
            for line in lines:
                if line.strip() and not line.strip().startswith('['):
                    time_tag = re.match(r'\[.*?\]', line)
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    try:
                        new_text = Romanizer(text).romanize()
                        new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
                    # Fix R1: bare except menelan KeyboardInterrupt & SystemExit.
                    # Pakai \`except Exception as e:\` agar Ctrl+C masih bisa menghentikan proses.
                    except Exception as e:
                        console.print(f"[dim yellow]⚠️ Romanizer gagal untuk baris ({e}). Memakai teks asli.[/dim yellow]")
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                    
        else:
            # Fallback Universal (Thailand, Rusia, Arab, dll)
            from anyascii import anyascii
            for line in lines:
                if line.strip() and not line.strip().startswith('['):
                    time_tag = re.match(r'\[.*?\]', line)
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    new_text = anyascii(text)
                    new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
                else:
                    new_lines.append(line)
                    
        # Fix R2: gunakan _atomic_write_text agar file LRC tidak korup jika
        # proses terputus (Ctrl+C, signal, OOM) di tengah penulisan.
        _atomic_write_text(lrc_path, "".join(new_lines))
    except Exception as e:
        console.print(f"[dim yellow]⚠️ Gagal melakukan transliterasi pada {os.path.basename(lrc_path)}: {e}[/dim yellow]")

def process_translation(lrc_path, translate_mode):
    """Menerjemahkan baris-baris LRC ke bahasa Indonesia secara berdampingan tanpa merusak timing"""
    if not os.path.exists(lrc_path) or not translate_mode: return
    
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        import re
        from deep_translator import GoogleTranslator, MyMemoryTranslator
        import langdetect
        
        texts_to_translate = []
        for line in lines:
            text = re.sub(r'\[.*?\]', '', line).strip()
            texts_to_translate.append(text if text else " ")

        translated_texts = []
        try:
            translator = GoogleTranslator(source='auto', target='id')
            # Gabungkan semua baris menjadi satu string besar (dipisah newline) untuk menghindari spam HTTP Request
            combined_text = "\n".join(texts_to_translate)
            res = translator.translate(combined_text)
            if not res or "Error 500" in res:
                raise Exception("Google Translate Web API Error 500")
            translated_texts = res.split('\n')
        except Exception as e:
            console.print(f"[dim yellow]⚠️ Google Translate gagal ({e}). Beralih ke mesin cadangan (MyMemory)...[/dim yellow]")
            pure_text = " ".join([t for t in texts_to_translate if t.strip()])
            if not pure_text: return
            lang = langdetect.detect(pure_text)
            
            lang_map = {'ja': 'ja-JP', 'zh-cn': 'zh-CN', 'zh-tw': 'zh-TW', 'ko': 'ko-KR', 'th': 'th-TH', 'en': 'en-US'}
            source_lang = lang_map.get(lang, f"{lang}-{lang.upper()}")
            
            try:
                # MyMemory memiliki limit 500 karakter per request.
                import time
                mm = MyMemoryTranslator(source=source_lang, target='id-ID')
                current_chunk = []
                current_len = 0
                for text in texts_to_translate:
                    if current_len + len(text) + 1 > 450:
                        combined = "\n".join(current_chunk)
                        res = mm.translate(combined)
                        translated_texts.extend(res.split('\n'))
                        current_chunk = [text]
                        current_len = len(text)
                        time.sleep(1) # Hindari Rate Limit MyMemory
                    else:
                        current_chunk.append(text)
                        current_len += len(text) + 1
                        
                if current_chunk:
                    combined = "\n".join(current_chunk)
                    res = mm.translate(combined)
                    translated_texts.extend(res.split('\n'))
            except Exception as e2:
                console.print(f"[dim yellow]⚠️ Semua mesin terjemahan gagal: {e2}[/dim yellow]")
                return

        # Pastikan jumlah array cocok, jika MyMemory memotong baris kosong
        if len(translated_texts) < len(lines):
            translated_texts.extend([""] * (len(lines) - len(translated_texts)))

        output = []
        for i, line in enumerate(lines):
            output.append(line.rstrip('\n'))
            t_text = translated_texts[i].strip() if translated_texts[i] else ""
            if t_text and t_text.lower() != texts_to_translate[i].strip().lower():
                match = re.match(r'(\[.*?\])', line)
                if match:
                    timestamp = match.group(1)
                    # Fix B4 (format non-standard): kode lama menulis terjemahan
                    # sebagai \`timestamp (translation)\` dalam satu baris. Format
                    # parenthetical TIDAK dikenali oleh Huawei Music, Poweramp,
                    # BlackPlayer, AIMP, dan mayoritas player mobile.
                    # Standar LRC bilingual yang kompatibel: dua baris dengan
                    # timestamp identik (satu untuk lirik asli, satu untuk
                    # terjemahan). Player yang mendukung bilingual (termasuk
                    # Huawei Music karaoke) akan menampilkannya berdampingan.
                    output.append(f"{timestamp}{t_text}")
                    
        # Fix R2: gunakan _atomic_write_text agar file LRC tidak korup jika
        # proses terputus di tengah penulisan terjemahan bilingual.
        _atomic_write_text(lrc_path, "\n".join(output))
            
    except Exception as e:
        console.print(f"[dim yellow]⚠️ Gagal menerjemahkan lirik pada {os.path.basename(lrc_path)}: {e}[/dim yellow]")

def fetch_synced_lyrics(title, lrc_path, sync_huawei, transliterate_mode="❌ 1", override_query=None, translate_mode=False):
    """Menggunakan library pihak ketiga (syncedlyrics) untuk mendapatkan lirik Studio Quality tanpa diblokir YouTube"""
    try:
        if override_query:
            clean_title = override_query.strip()
        else:
            # Hapus teks dalam kurung siku/biasa/jepang yang mengganggu pencarian lirik (e.g., "[Rainych]", "【Rainych】", "(Official Video)")
            import re
            clean_title = re.sub(r'\[.*?\]|\(.*?\)|【.*?】', '', title).strip()
        
        lrc_text = syncedlyrics.search(clean_title)
        
        # [Formula Pencarian Cerdas] Jika gagal, gunakan iTunes API untuk menebak judul resmi Spotify!
        if not lrc_text and not override_query:
            try:
                import requests
                smart_query = re.sub(r'(?i)(official|music video|mv|lyric|video|audio|cover)', '', clean_title).strip()
                # Fix B2 (silently fail): kode lama memakai \`import requests\` tapi
                # requests TIDAK ada di requirements.txt. Setiap ImportError ditelan
                # \`except: pass\` sehingga fitur "Formula Cerdas" mati tanpa user tahu.
                # Sekarang requests sudah dideklarasikan; kita juga log error eksplisit.
                from urllib.parse import quote
                encoded_query = quote(smart_query)
                res = requests.get(
                    f"https://itunes.apple.com/search?term={encoded_query}&entity=song&limit=1",
                    timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                res.raise_for_status()
                data = res.json()
                if data.get('resultCount', 0) > 0:
                    track = data['results'][0]['trackName']
                    artist = data['results'][0]['artistName']
                    smart_title = f"{artist} {track}"
                    console.print(f"   [dim cyan]🔍 Formula Cerdas mendeteksi judul resmi: '{smart_title}'. Mencoba ulang...[/dim cyan]")
                    lrc_text = syncedlyrics.search(smart_title)
            except ImportError:
                # Fallback jika requests belum terinstal (seharusnya tidak terjadi setelah fix requirements)
                console.print("[dim yellow]⚠️ Modul 'requests' belum terinstal — Fitur Formula Cerdas (iTunes) dilewati.[/dim yellow]")
            except Exception as e:
                # Fix R1: bare except → except Exception as e. Log setiap kegagalan agar transparan.
                console.print(f"[dim yellow]⚠️ Formula Cerdas iTunes gagal: {e}[/dim yellow]")
        if lrc_text:
            # Fix R2: tulis hasil lirik dari syncedlyrics secara atomik juga.
            _atomic_write_text(lrc_path, lrc_text)
            process_transliteration(lrc_path, transliterate_mode)
            process_translation(lrc_path, translate_mode)
            if sync_huawei:
                sync_huawei_lrc(lrc_path)
        else:
            console.print(f"[dim yellow]⚠️ Lirik tidak ditemukan di database untuk: {clean_title}[/dim yellow]")
    except Exception as e:
        console.print(f"[dim red]❌ Error saat menarik lirik untuk {title}: {e}[/dim red]")
    return False

custom_theme = questionary.Style([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'bold white'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('highlighted', 'fg:#ff00ff bold'),
    ('selected', 'fg:#00ff00'),
    ('instruction', 'fg:#808080 italic')
])

def run_retrofit():
    folder = get_default_path()
    console.print(f"\n[bold cyan]🛠️ Mode Perbaikan / Retrofit Otomatis[/bold cyan]")
    console.print(f"[white]Sistem akan memindai folder Anda, mencari lagu tanpa lirik/cover, mencarinya di YouTube, lalu menyuntikkannya ke file asli![/white]\n")
    
    target_folder = questionary.text("Masukkan path folder yang ingin diperbaiki:", default=folder, style=custom_theme).ask()
    if not os.path.exists(target_folder):
        console.print("[bold red]❌ Folder tidak ditemukan![/bold red]")
        return

    # Prompt khusus Termux/Huawei
    sync_huawei = False
    if "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
        sync_huawei = questionary.confirm("📱 Aktifkan Sinkronisasi Lirik khusus Huawei/HarmonyOS (Kopi ke folder Music/Musiclrc)?", default=False, style=custom_theme).ask()

    console.print()
    lyrics_mode = questionary.select(
        "📝 Pilih Sumber & Mesin Lirik (Sangat Penting):",
        choices=[
            "🎧 1. Mesin Spotify/Musixmatch (Anti-Blokir YT) - Terbaik untuk Lagu Asli (Original)",
            "✍️ 2. Mesin Spotify (Input Judul Manual) - Terbaik jika judul Spotify berbeda dari YouTube",
            "📺 3. Mesin YouTube Subtitles (Rawan 429) - Terbaik untuk Lagu Cover (Timing 100% Akurat)",
            "❌ 4. Jangan download lirik"
        ],
        style=custom_theme
    ).ask()
    
    download_lyrics = not lyrics_mode.startswith("❌ 4")

    transliterate = "❌ 1"
    if download_lyrics:
        console.print()
        transliterate = questionary.select(
            "🔤 Ubah Huruf Asing (Jepang/Mandarin/Korea/Thai dll) ke Tulisan Biasa (Romaji/Pinyin/Latin)?",
            choices=[
                "❌ 1. Biarkan Aslinya (Jangan diubah)",
                "🇯🇵 2. Ya, Ubah Huruf Jepang ke Romaji (Khusus Lagu Jepang/Anime)",
                "🇨🇳 3. Ya, Ubah Huruf Mandarin ke Pinyin (Khusus Lagu China)",
                "🤖 4. Deteksi Otomatis & Ubah Semua (Khusus Playlist Campur/Berbagai Negara)"
            ],
            style=custom_theme
        ).ask()
        translate_id = questionary.confirm("🌐 Terjemahkan Lirik ke Bahasa Indonesia (Otomatis ditambahkan di bawah teks asli)?", default=False, style=custom_theme).ask()
    else:
        translate_id = False

    # Langkah 0: Perbaiki (Rename) file LRC lama, Terapkan Transliterasi, dan Sync ke Huawei
    fixed_lrc_count = 0
    for lrc_file in glob.glob(os.path.join(target_folder, "**", "*.lrc"), recursive=True):
        parts = lrc_file.rsplit('.', 2)
        if len(parts) == 3 and len(parts[1]) <= 3:
            new_name = f"{parts[0]}.lrc"
            new_path = os.path.join(os.path.dirname(lrc_file), new_name)
            if os.path.exists(new_path):
                if parts[1] != 'id' and os.path.getsize(new_path) > 0:
                    os.remove(lrc_file)
                    continue
                os.remove(new_path)
            shutil.move(lrc_file, new_path)
            process_transliteration(new_path, transliterate)
            if sync_huawei:
                sync_huawei_lrc(new_path)
            fixed_lrc_count += 1
        else:
            # Jika namanya sudah benar, terapkan transliterasi lalu sync
            process_transliteration(lrc_file, transliterate)
            if sync_huawei:
                sync_huawei_lrc(lrc_file)
                
    # Langkah 0.5: Bersihkan file sampah sisa timeout sebelumnya (.vtt, .part, .json)
    junk_files = glob.glob(os.path.join(target_folder, "**", "temp_meta_*"), recursive=True)
    for junk in junk_files:
        try:
            os.remove(junk)
        # Fix R1: bare except → except Exception as e. FileNotFoundError boleh diabaikan diam-diam.
        except FileNotFoundError:
            pass
        except Exception as e:
            console.print(f"[dim yellow]⚠️ Gagal menghapus sampah {os.path.basename(junk)}: {e}[/dim yellow]")
            
    if fixed_lrc_count > 0:
        console.print(f"[bold green]✅ Berhasil memperbaiki penamaan & sinkronisasi {fixed_lrc_count} file Lirik lama secara instan![/bold green]")

    # Kumpulkan file audio
    audio_files = []
    for ext in ["*.mp3", "*.flac"]:
        audio_files.extend(glob.glob(os.path.join(target_folder, "**", ext), recursive=True))
        
    if not audio_files:
        console.print("[bold yellow]⚠️ Tidak ada file MP3/FLAC yang ditemukan di folder tersebut.[/bold yellow]")
        return
        
    console.print(f"[bold green]✅ Ditemukan {len(audio_files)} file musik.[/bold green]")
    target_mode = questionary.select(
        "🎯 Pilih Target Injeksi / Perbaikan:",
        choices=[
            "✨ 1. Perbaiki Lirik & Cover Art (Lengkap)",
            "📝 2. Perbaiki Lirik Saja (Abaikan Cover)",
            "🖼️ 3. Perbaiki Cover Art Saja (Abaikan Lirik)"
        ],
        style=custom_theme
    ).ask()
    
    force_overwrite_lrc = False
    if target_mode.startswith("✨ 1") or target_mode.startswith("📝 2"):
        force_overwrite_lrc = questionary.confirm("⚠️ Hapus & Timpa file lirik (.lrc) lama yang mungkin salah timing?", default=False, style=custom_theme).ask()
        
    start = questionary.confirm("▶️ Mulai eksekusi sekarang?", default=True, style=custom_theme).ask()
    if not start: return
    
    # Progress UI
    with Progress(
        SpinnerColumn(spinner_name="dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="green"),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        main_task = progress.add_task("[cyan]Memulai Retrofit Engine...", total=len(audio_files))
        
        for audio_path in audio_files:
            filename = os.path.basename(audio_path)
            title = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1].lower()
            dir_path = os.path.dirname(audio_path)
            
            progress.update(main_task, description=f"[cyan]Menyelidiki: [bold white]{title[:20]}...")
            
            # Cek jika lirik sudah ada
            lrc_path = os.path.join(dir_path, f"{title}.lrc")
            
            # Kita gunakan yt-dlp untuk search title dan download thumbnail + subs tanpa audio
            temp_outtmpl = os.path.join(dir_path, f"temp_meta_{title}.%(ext)s")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'skip_download': True,
                'writethumbnail': True,
                'sleep_interval_requests': 1,
                'sleep_interval': 3,           
                'max_sleep_interval': 8,       
                'retries': 5,
                'file_access_retries': 5,
                'fragment_retries': 5,
                'outtmpl': temp_outtmpl,
                # Fix R13: restrictfilenames memaksa yt-dlp hanya menggunakan
                # karakter [a-zA-Z0-9._-] sehingga filename aman lintas-platform.
                # Tanpa ini, judul seperti `Song: A/B/C` menghasilkan file path
                # ilegal di Windows NTFS (/, :, *, ?, \", <, >, | semua dilarang).
                'restrictfilenames': True,
                'quiet': True,
                'no_warnings': True,
                'logger': YTDLPLogger()
            }
            
            if lyrics_mode.startswith("📺 3"):
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['id', 'en', 'ja', 'ko', 'all']
                ydl_opts['postprocessors'] = [{'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'}]
                
            search_query = f"ytsearch1:{title}"
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([search_query])
            # Fix R1: walau \`except Exception:\` sudah spesifik, kita log agar user tahu
            # video mana yang gagal di-fetch metadata/thumbnail. Tanpa ini, retrofit
            # mode terlihat "berhasil" padahal cover art tidak pernah ter-download.
            except Exception as e:
                console.print(f"[dim yellow]⚠️ Gagal ambil metadata YouTube untuk '{title[:30]}...': {e}[/dim yellow]")
                
            # Hapus lirik lama jika diminta
            if force_overwrite_lrc and os.path.exists(lrc_path):
                os.remove(lrc_path)
            
            # BLOK 1: Pemrosesan Lirik
            if not target_mode.startswith("🖼️ 3"):
                # Tangani lirik hasil unduhan YouTube (jika menggunakan Mode 2)
                if lyrics_mode.startswith("📺 3"):
                    for yt_lrc in glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.lrc")):
                        if os.path.exists(lrc_path): os.remove(lrc_path)
                        shutil.move(yt_lrc, lrc_path)
                
                # Jika lirik belum ada dan kita pakai Mode 1/2 (Spotify)
                huawei_lrc_path = os.path.join(str(Path.home()), "storage", "shared", "Music", "Musiclrc", f"{title}.lrc")
                if (lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")) and not os.path.exists(lrc_path) and not (sync_huawei and os.path.exists(huawei_lrc_path)):
                    query = None
                    if lyrics_mode.startswith("✍️ 2"):
                        progress.stop()
                        query = questionary.text(f"📝 Masukkan judul Spotify untuk '{title}':", style=custom_theme).ask()
                        progress.start()
                    fetch_synced_lyrics(title, lrc_path, sync_huawei, transliterate, override_query=query, translate_mode=translate_id)
                # Jika lirik sudah ada (misal dari YouTube CC Mode 3), transliterasi & sinkronisasi
                elif os.path.exists(lrc_path):
                    process_transliteration(lrc_path, transliterate)
                    process_translation(lrc_path, translate_id)
                    if sync_huawei:
                        sync_huawei_lrc(lrc_path)
                
                # Peringatan jika lirik benar-benar tidak ditemukan (YouTube tidak memiliki CC)
                if not os.path.exists(lrc_path):
                    progress.stop()
                    console.print(f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {title[:30]}...[/bold yellow]")
                    progress.start()
                        
            # BLOK 2: Pemrosesan Cover Art
            if not target_mode.startswith("📝 2"):
                # Cari Cover Art hasil download (bisa .jpg, .webp)
                temp_cover_glob = glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.webp")) + glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.jpg"))
                if temp_cover_glob:
                    cover_path = temp_cover_glob[0]
                    
                    # Gunakan FFmpeg untuk menyuntikkan gambar ke dalam audio lama!
                    temp_audio = os.path.join(dir_path, f"temp_{filename}")
                    progress.update(main_task, description=f"[magenta]Menyuntikkan Cover: [bold white]{title[:20]}...")
                    
                    # Fix S1 (command injection): kode lama memakai os.system(cmd)
                    # dengan string interpolation dari path filesystem user. Jika
                    # ada file bernama \`song\"; rm -rf ~; echo \".mp3\`, shell akan
                    # mengeksekusi perintah berbahaya. Sekarang kita pakai
                    # subprocess.run() dengan list argumen — TIDAK ada shell
                    # interpolation, argumen dilewatkan langsung ke execvp().
                    import subprocess
                    if ext == '.mp3':
                        ffmpeg_cmd = [
                            'ffmpeg', '-y', '-v', 'quiet',
                            '-i', audio_path,
                            '-i', cover_path,
                            '-map', '0:0', '-map', '1:0',
                            '-c', 'copy',
                            '-id3v2_version', '3',
                            '-metadata:s:v', 'title=Album cover',
                            '-metadata:s:v', 'comment=Cover (front)',
                            temp_audio
                        ]
                    elif ext == '.flac':
                        ffmpeg_cmd = [
                            'ffmpeg', '-y', '-v', 'quiet',
                            '-i', audio_path,
                            '-i', cover_path,
                            '-map', '0:0', '-map', '1:0',
                            '-c', 'copy',
                            '-disposition:v', 'attached_pic',
                            temp_audio
                        ]
                    else:
                        ffmpeg_cmd = None
                    
                    if ffmpeg_cmd:
                        try:
                            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
                        except subprocess.CalledProcessError as e:
                            console.print(f"[dim red]❌ FFmpeg gagal menyuntik cover untuk {filename}: {e.stderr.strip() if e.stderr else str(e)}[/dim red]")
                        except FileNotFoundError:
                            console.print(f"[dim red]❌ FFmpeg tidak ditemukan di PATH. Pastikan sudah terinstal.[/dim red]")
                        except Exception as e:
                            console.print(f"[dim red]❌ Error tak terduga saat injeksi cover {filename}: {e}[/dim red]")
                    
                    # Ganti file asli dengan yang sudah disuntik jika berhasil
                    if os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                        os.remove(audio_path)
                        shutil.move(temp_audio, audio_path)
                    
            # Bersihkan SEMUA sisa file sampah sementara (seperti .vtt, .part, .json, .webp)
            temp_junk_glob = glob.glob(os.path.join(dir_path, f"temp_meta_{title}*"))
            for junk in temp_junk_glob:
                try:
                    if os.path.exists(junk):
                        os.remove(junk)
                # Fix R1: log failure agar visible, kecuali FileNotFoundError (race condition dengan cleanup paralel).
                except FileNotFoundError:
                    pass
                except Exception as e:
                    console.print(f"[dim yellow]⚠️ Gagal hapus {os.path.basename(junk)}: {e}[/dim yellow]")
                        
            progress.advance(main_task)
            
        progress.update(main_task, description="[bold green]✨ Proses Retrofit Selesai!", completed=len(audio_files))

def run_organizer():
    console.print(f"\n[bold cyan]📁 Mode 3: Pengatur Otomatis (Auto-Organizer)[/bold cyan]")
    console.print("[white]Sistem akan mencari lagu & lirik yang Anda unduh secara manual di folder Downloads, lalu menyamakan namanya dan memindahkannya ke folder Huawei Music secara otomatis![/white]\n")
    
    is_termux = "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", "")
    if is_termux:
        downloads_dir = str(Path.home() / "storage" / "downloads")
        music_dir = str(Path.home() / "storage" / "shared" / "Music")
        lrc_dir = os.path.join(music_dir, "Musiclrc")
    else:
        downloads_dir = str(Path.home() / "Downloads")
        music_dir = os.path.join(downloads_dir, "Music")
        lrc_dir = os.path.join(music_dir, "Musiclrc")

    if not os.path.exists(downloads_dir):
        console.print("[bold red]❌ Folder Downloads tidak ditemukan![/bold red]")
        return

    # Cari file mp3 dan lrc di root Downloads
    mp3_files = [f for f in os.listdir(downloads_dir) if f.lower().endswith('.mp3')]
    lrc_files = [f for f in os.listdir(downloads_dir) if f.lower().endswith('.lrc')]
    
    if not mp3_files and not lrc_files:
        console.print("[dim yellow]⚠️ Tidak ditemukan file MP3 atau LRC mandiri di folder Downloads Anda.[/dim yellow]")
        return
        
    console.print(f"[bold green]✅ Ditemukan {len(mp3_files)} MP3 dan {len(lrc_files)} file LRC di folder Downloads.[/bold green]")
    
    if not questionary.confirm("▶️ Mulai proses perapian (Ganti Nama Otomatis & Pindahkan ke Folder Musik)?", default=True, style=custom_theme).ask():
        return

    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(lrc_dir, exist_ok=True)
    
    from rapidfuzz import fuzz
    
    moved_mp3 = 0
    moved_lrc = 0

    with console.status("[cyan]Merapikan file Anda..."):
        # Pindahkan dan ganti nama LRC agar cocok dengan MP3 menggunakan AI String Matching (RapidFuzz)
        for lrc in lrc_files:
            lrc_path = os.path.join(downloads_dir, lrc)
            lrc_name = os.path.splitext(lrc)[0]
            
            best_match = None
            best_score = 0
            for mp3 in mp3_files:
                mp3_name = os.path.splitext(mp3)[0]
                score = fuzz.ratio(lrc_name.lower(), mp3_name.lower())
                if score > best_score:
                    best_score = score
                    best_match = mp3_name
            
            if best_match and best_score > 50:
                # Ganti nama lrc sama persis dengan mp3
                new_lrc_name = f"{best_match}.lrc"
                target_lrc_path = os.path.join(lrc_dir, new_lrc_name)
                # Timpa jika ada
                if os.path.exists(target_lrc_path): os.remove(target_lrc_path)
                shutil.move(lrc_path, target_lrc_path)
                moved_lrc += 1
            else:
                # Jika tidak ada yang cocok, pindahkan dengan nama aslinya
                target_lrc_path = os.path.join(lrc_dir, lrc)
                if os.path.exists(target_lrc_path): os.remove(target_lrc_path)
                shutil.move(lrc_path, target_lrc_path)
                moved_lrc += 1

        # Pindahkan MP3
        for mp3 in mp3_files:
            mp3_path = os.path.join(downloads_dir, mp3)
            target_mp3_path = os.path.join(music_dir, mp3)
            if os.path.exists(target_mp3_path): os.remove(target_mp3_path)
            shutil.move(mp3_path, target_mp3_path)
            moved_mp3 += 1
            
    console.print(f"\n[bold green]✨ Proses Perapian Selesai![/bold green]")
    console.print(f"🎵 {moved_mp3} lagu dipindahkan ke: [yellow]{music_dir}[/yellow]")
    console.print(f"🎤 {moved_lrc} lirik dipindahkan ke: [yellow]{lrc_dir}[/yellow]\n")

def run_cli():
    missing_deps = check_dependencies()
    if missing_deps:
        console.print(Panel(
            f"[bold red]Dependensi Sistem Hilang![/bold red]\n\n"
            f"Aplikasi ini membutuhkan [bold yellow]{', '.join(missing_deps)}[/bold yellow] untuk melakukan konversi audio.\n"
            f"Silakan install FFmpeg terlebih dahulu.",
            title="⚠️ Sistem Belum Siap", border_style="red"
        ))
        sys.exit(1)

    while True:
        print_banner()

        # PILIHAN MODE
        mode_choices = {
            "📥 1. Mode Utama (Download Lagu/Playlist dari YouTube)": 1,
            "🛠️ 2. Mode Retrofit (Otomatis Cari & Suntik Lirik/Cover ke File Lama)": 2,
            "📁 3. Mode Pengatur Otomatis (Rapikan File Lirik/MP3 Unduhan Manual)": 3,
            "🎵 4. Mode Spotify (Download Lagu/Playlist dari Spotify)": 4,
            "☁️  5. Mode SoundCloud (Download Lagu/Playlist dari SoundCloud)": 5
        }
        selected_mode = questionary.select("Pilih Mode Operasi Aplikasi:", choices=list(mode_choices.keys()), style=custom_theme, use_indicator=True).ask()
        mode = mode_choices[selected_mode]
        
        if mode == 2:
            run_retrofit()
            if not questionary.confirm("\n🔄 Kembali ke menu utama?", default=True, style=custom_theme).ask():
                console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
                break
            continue
        elif mode == 3:
            run_organizer()
            if not questionary.confirm("\n🔄 Kembali ke menu utama?", default=True, style=custom_theme).ask():
                console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
                break
            continue

        # MODE DOWNLOAD UTAMA & SPOTIFY & SOUNDCLOUD
        is_spotify_mode = (mode == 4)
        is_soundcloud_mode = (mode == 5)
        spotify_targets = []
        
        if is_spotify_mode:
            url_or_search = questionary.text("🎵 Masukkan URL Track/Playlist/Album Spotify:", style=custom_theme).ask()
            if not url_or_search or "spotify.com" not in url_or_search:
                console.print("[red]⚠️ URL Spotify tidak valid![/red]")
                import time; time.sleep(1); continue
            url_or_search = url_or_search.strip()
            
            console.print("[cyan]🔍 Membaca metadata dari Spotify...[/cyan]")
            spotify_targets = parse_spotify_url(url_or_search)
            if not spotify_targets:
                console.print("[red]⚠️ Gagal mengambil data Spotify atau playlist kosong![/red]")
                import time; time.sleep(1); continue
                
            console.print(f"[bold green]✅ Ditemukan {len(spotify_targets)} lagu dari Spotify![/bold green]")
            max_songs = None
            limit_choice = questionary.confirm(f"Batasi jumlah lagu yang diunduh (dari {len(spotify_targets)} lagu)?", default=False, style=custom_theme).ask()
            if limit_choice:
                while True:
                    limit_input = questionary.text("Berapa maksimal lagu? (Angka):", style=custom_theme).ask()
                    if limit_input and limit_input.isdigit() and int(limit_input) > 0:
                        max_songs = int(limit_input)
                        spotify_targets = spotify_targets[:max_songs]
                        break
                    else: console.print("[red]⚠️ Masukkan angka valid![/red]")
            
            final_target = None
            display_target = f"Spotify Playlist/Track ({len(spotify_targets)} lagu)"
            
        else:
            prompt_text = "☁️ Masukkan URL SoundCloud ATAU Ketik Judul Lagu:" if is_soundcloud_mode else "Masukkan URL YouTube ATAU Ketik Judul Lagu:"
            url_or_search = questionary.text(prompt_text, style=custom_theme).ask()
            if not url_or_search:
                console.print("[red]⚠️ Input tidak boleh kosong![/red]")
                import time; time.sleep(1); continue
                
            url_or_search = url_or_search.strip()
            is_search = not (url_or_search.startswith("http://") or url_or_search.startswith("https://") or url_or_search.startswith("www."))
                
            limit_choice = questionary.confirm(f"Batasi jumlah lagu yang diunduh {'dari hasil pencarian' if is_search else 'dari playlist'} ini?", default=False, style=custom_theme).ask()
            max_songs = None
            if limit_choice:
                while True:
                    limit_input = questionary.text("Berapa maksimal lagu? (Angka):", style=custom_theme).ask()
                    if limit_input and limit_input.isdigit() and int(limit_input) > 0:
                        max_songs = int(limit_input); break
                    else: console.print("[red]⚠️ Masukkan angka valid![/red]")
            
            if is_search:
                search_limit = max_songs if max_songs else 1
                search_prefix = "scsearch" if is_soundcloud_mode else "ytsearch"
                final_target = f"{search_prefix}{search_limit}:{url_or_search}"
                display_target = f"Pencarian {'SoundCloud' if is_soundcloud_mode else 'YouTube'}: '{url_or_search}' (Top {search_limit})"
            else:
                final_target = url_or_search
                display_target = url_or_search
        
        console.print()
        format_options = {
            "MP3 (320kbps) - Default (Tinggi)": {"codec": "mp3", "quality": "320", "name": "MP3 (320kbps)"},
            "FLAC (Lossless) - Best Quality murni": {"codec": "flac", "quality": None, "name": "FLAC (Lossless)"},
            "WAV (Uncompressed) - Mentah": {"codec": "wav", "quality": None, "name": "WAV (Uncompressed)"},
            "Original Audio - Bawaan YouTube": {"codec": "best", "quality": None, "name": "Original Audio"}
        }
        selected_key = questionary.select("Pilih Kualitas Audio:", choices=list(format_options.keys()), style=custom_theme, use_indicator=True).ask()
        selected_fmt = format_options[selected_key]

        console.print()
        anti_duplicate = questionary.confirm("🛡️ Aktifkan Anti-Duplikat (Lewati lagu lama)?", default=True, style=custom_theme).ask()
        console.print()
        lyrics_mode = questionary.select(
            "📝 Pilih Sumber & Mesin Lirik (Sangat Penting):",
            choices=[
                "🎧 1. Mesin Spotify/Musixmatch (Anti-Blokir YT) - Terbaik untuk Lagu Asli (Original)",
                "✍️ 2. Mesin Spotify (Input Judul Manual) - Terbaik jika judul Spotify berbeda dari YouTube",
                "📺 3. Mesin YouTube Subtitles (Rawan 429) - Terbaik untuk Lagu Cover (Timing 100% Akurat)",
                "❌ 4. Jangan download lirik"
            ],
            style=custom_theme
        ).ask()
        
        download_lyrics = not lyrics_mode.startswith("❌ 4")
        
        transliterate = "❌ 1"
        if download_lyrics:
            console.print()
            transliterate = questionary.select(
                "🔤 Ubah Huruf Asing (Jepang/Mandarin/Korea/Thai dll) ke Tulisan Biasa (Romaji/Pinyin/Latin)?",
                choices=[
                    "❌ 1. Biarkan Aslinya (Jangan diubah)",
                    "🇯🇵 2. Ya, Ubah Huruf Jepang ke Romaji (Khusus Lagu Jepang/Anime)",
                    "🇨🇳 3. Ya, Ubah Huruf Mandarin ke Pinyin (Khusus Lagu China)",
                    "🤖 4. Deteksi Otomatis & Ubah Semua (Khusus Playlist Campur/Berbagai Negara)"
                ],
                style=custom_theme
            ).ask()
            translate_id = questionary.confirm("🌐 Terjemahkan Lirik ke Bahasa Indonesia (Otomatis ditambahkan di bawah teks asli)?", default=False, style=custom_theme).ask()
        else:
            translate_id = False
        sync_huawei = False
        if download_lyrics and "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
            console.print()
            sync_huawei = questionary.confirm("📱 Aktifkan Sinkronisasi Lirik khusus Huawei/HarmonyOS (Kopi ke folder Music/Musiclrc)?", default=False, style=custom_theme).ask()

        output_dir = get_default_path()
        archive_file = os.path.join(output_dir, "archive.txt")
        
        console.print("\n")
        table = Table(title="📋 [bold bright_white]Konfigurasi Sistem Unduhan[/bold bright_white]", box=box.ROUNDED, border_style="cyan")
        table.add_column("Parameter", justify="right", style="cyan", no_wrap=True)
        table.add_column("Nilai", style="magenta")

        table.add_row("🎯 Target", display_target)
        table.add_row("🔢 Batas Lagu", str(max_songs) if max_songs else "Semua (Tanpa Batas)")
        table.add_row("🎵 Format Audio", selected_fmt['name'])
        is_wav = selected_fmt['codec'] == 'wav'
        table.add_row("🖼️ ID3 & Cover Art", "[green]✅ Aktif[/green]" if not is_wav else "[yellow]⚠️ Tidak (WAV)[/yellow]")
        table.add_row("🛡️ Anti-Duplikat", "[green]✅ Aktif[/green]" if anti_duplicate else "[red]❌ Nonaktif[/red]")
        table.add_row("🎤 Download Lirik", "[green]✅ Aktif (.lrc)[/green]" if download_lyrics else "[red]❌ Nonaktif[/red]")
        table.add_row("📁 Folder Simpan", f"[yellow]{output_dir}[/yellow]")
        
        console.print(table)
        console.print()
        if not questionary.confirm("▶️ Mulai eksekusi unduhan sekarang?", default=True, style=custom_theme).ask(): continue

        os.makedirs(output_dir, exist_ok=True)
        if is_spotify_mode:
            outtmpl_path = f'{output_dir}/Spotify_Downloads/%(title)s.%(ext)s'
        elif is_soundcloud_mode:
            outtmpl_path = f'{output_dir}/SoundCloud_Downloads/%(playlist_title)s/%(title)s.%(ext)s'
        else:
            outtmpl_path = f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s'
            
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl_path,
            'noplaylist': False,
            'ignoreerrors': True,
            'geo_bypass': True,
            'sleep_interval_requests': 1,  # Jeda aman saat ekstraksi list lagu
            'sleep_interval': 2,           # Jeda acak minimal 2 detik sebelum unduh
            'max_sleep_interval': 5,       # Jeda acak maksimal 5 detik (menghindari deteksi bot)
            # Fix R13: restrictfilenames memaksa yt-dlp hanya menggunakan
            # karakter [a-zA-Z0-9._-] sehingga filename aman lintas-platform.
            # Mencegah folder/file dengan karakter ilegal (/, :, *, ?, \", <, >, |)
            # di windows NTFS dan menyederhanakan matching LRC dengan audio.
            'restrictfilenames': True,
            'quiet': True,
            'no_warnings': True,
            'logger': YTDLPLogger(),
            'extract_flat': False,
        }
        if anti_duplicate: ydl_opts['download_archive'] = archive_file

        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': selected_fmt['codec']}]
        if selected_fmt['quality']: pp[0]['preferredquality'] = selected_fmt['quality']
        pp.append({'key': 'FFmpegMetadata', 'add_metadata': True})
        if not is_wav:
            ydl_opts['writethumbnail'] = True
            pp.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
            
        if lyrics_mode.startswith("📺 3"):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['id', 'en', 'ja', 'ko', 'all']
            pp.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'})
            
        ydl_opts['postprocessors'] = pp
        if max_songs: ydl_opts['playlistend'] = max_songs

        console.print("")
        with Progress(
            SpinnerColumn(spinner_name="dots2", style="cyan"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40, style="blue", complete_style="green"),
            TaskProgressColumn(),
            console=console,
            expand=False
        ) as progress:
            main_task = progress.add_task("[cyan]Menganalisis URL & Metadata...", total=None)
            def download_hook(d):
                status = d['status']
                if status == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    progress.update(main_task, description=f"[cyan]Mengunduh: [bold white]{filename[:32]}", total=total if total > 0 else None, completed=downloaded)
                elif status == 'finished':
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    progress.update(main_task, description=f"[green]Memproses Media: [bold white]{filename[:32]}", total=None, completed=0)

            ydl_opts['progress_hooks'] = [download_hook]
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    if is_spotify_mode:
                        for track in spotify_targets:
                            # Fix R1: log lagu Spotify yang gagal agar user tahu lagu mana yang skip.
                            # Sebelumnya \`except Exception: pass\` menyembunyikan kegagalan total,
                            # sehingga playlist Spotify terlihat "sukses download" padahal banyak
                            # lagu yang gagal matching tanpa kabar.
                            try:
                                ydl.download([f"ytsearch1:{track}"])
                            except Exception as e:
                                console.print(f"[dim red]❌ Gagal unduh '{track[:40]}...': {e}[/dim red]")
                    else:
                        ydl.download([final_target])
                    
                # Fetch Lirik via API (Bypass YouTube)
                if download_lyrics:
                    progress.update(main_task, description="[cyan]Memproses Lirik & Transliterasi...", total=None)
                    
                    # 1. Bersihkan file lirik berakhiran .en.lrc atau .ja.lrc menjadi .lrc (Bawaan YT)
                    if lyrics_mode.startswith("📺 3"):
                        for lrc_file in glob.glob(os.path.join(output_dir, "**", "*.lrc"), recursive=True):
                            parts = lrc_file.rsplit('.', 2)
                            if len(parts) == 3 and len(parts[1]) <= 3:
                                new_path = f"{parts[0]}.lrc"
                                if os.path.exists(new_path):
                                    os.remove(new_path)
                                shutil.move(lrc_file, new_path)

                    # 2. Proses API / Transliterasi / Copy ke Huawei
                    for root, _, files in os.walk(output_dir):
                        for file in files:
                            if file.endswith('.mp3') or file.endswith('.flac') or file.endswith('.wav'):
                                song_title = os.path.splitext(file)[0]
                                lrc_path = os.path.join(root, f"{song_title}.lrc")
                                
                                # Jika lirik belum ada dan kita pakai Mode 1/2 (Spotify)
                                if (lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")) and not os.path.exists(lrc_path):
                                    query = None
                                    if lyrics_mode.startswith("✍️ 2"):
                                        progress.stop()
                                        query = questionary.text(f"📝 Masukkan judul Spotify untuk '{song_title}':", style=custom_theme).ask()
                                        progress.start()
                                    fetch_synced_lyrics(song_title, lrc_path, sync_huawei, transliterate, override_query=query, translate_mode=translate_id)
                                    
                                # Jika lirik sudah ada (hasil dari YT atau baru saja ditarik), terapkan transliterasi & sync
                                elif os.path.exists(lrc_path):
                                    process_transliteration(lrc_path, transliterate)
                                    process_translation(lrc_path, translate_id)
                                    if sync_huawei:
                                        sync_huawei_lrc(lrc_path)
                                
                                # Peringatan jika lirik benar-benar tidak ditemukan
                                if not os.path.exists(lrc_path):
                                    progress.stop()
                                    console.print(f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {song_title[:30]}...[/bold yellow]")
                                    progress.start()
                progress.update(main_task, description="[bold green]✨ Seluruh tugas selesai!", completed=100, total=100)
            except Exception as e:
                progress.stop()
                console.print(f"\n[bold red]❌ Kegagalan fatal:[/bold red] {e}")

        console.print()
        if not questionary.confirm("🔄 Ingin mengunduh sesuatu yang lain?", default=False, style=custom_theme).ask():
            console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
            break

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Aplikasi dihentikan secara paksa (Ctrl+C).[/bold red]")
        sys.exit(0)
