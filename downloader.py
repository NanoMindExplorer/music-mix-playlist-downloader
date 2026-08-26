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

    # Kumpulkan file audio
    audio_files = []
    for ext in ["*.mp3", "*.flac"]:
        audio_files.extend(glob.glob(os.path.join(target_folder, "**", ext), recursive=True))
        
    if not audio_files:
        console.print("[bold yellow]⚠️ Tidak ada file MP3/FLAC yang ditemukan di folder tersebut.[/bold yellow]")
        return
        
    console.print(f"[bold green]✅ Ditemukan {len(audio_files)} file musik.[/bold green]")
    start = questionary.confirm("▶️ Mulai proses injeksi massal (Pencarian YT & Download Lirik/Cover)?", default=True, style=custom_theme).ask()
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
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['id', 'en', 'all'],
                'sleep_interval_requests': 1,  # Jeda aman saat ekstraksi data
                'sleep_interval': 2,           # Jeda acak minimal 2 detik antar tugas
                'max_sleep_interval': 5,       # Jeda acak maksimal 5 detik (seperti aktivitas manusia)
                'sleep_interval_subtitles': 1,
                'outtmpl': temp_outtmpl,
                'quiet': True,
                'no_warnings': True,
                'logger': YTDLPLogger(),
                'postprocessors': [{'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'}]
            }
            
            search_query = f"ytsearch1:{title}"
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([search_query])
            except Exception:
                progress.advance(main_task)
                continue
                
            # Rename Lirik hasil download ke nama aslinya
            temp_lrc_glob = glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.lrc"))
            for temp_lrc in temp_lrc_glob:
                if os.path.exists(temp_lrc):
                    shutil.move(temp_lrc, lrc_path)
                    
            # Cari Cover Art hasil download (bisa .jpg, .webp)
            temp_cover_glob = glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.webp")) + glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.jpg"))
            if temp_cover_glob:
                cover_path = temp_cover_glob[0]
                
                # Gunakan FFmpeg untuk menyuntikkan gambar ke dalam audio lama!
                temp_audio = os.path.join(dir_path, f"temp_{filename}")
                progress.update(main_task, description=f"[magenta]Menyuntikkan Cover: [bold white]{title[:20]}...")
                
                if ext == '.mp3':
                    cmd = f'ffmpeg -y -v quiet -i "{audio_path}" -i "{cover_path}" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "{temp_audio}"'
                elif ext == '.flac':
                    cmd = f'ffmpeg -y -v quiet -i "{audio_path}" -i "{cover_path}" -map 0:0 -map 1:0 -c copy -disposition:v attached_pic "{temp_audio}"'
                
                os.system(cmd)
                
                # Ganti file asli dengan yang sudah disuntik jika berhasil
                if os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                    os.remove(audio_path)
                    shutil.move(temp_audio, audio_path)
                    
                # Bersihkan sisa cover
                for c in temp_cover_glob:
                    if os.path.exists(c):
                        os.remove(c)
                        
            progress.advance(main_task)
            
        progress.update(main_task, description="[bold green]✨ Proses Retrofit Selesai!", completed=len(audio_files))

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
        mode = questionary.select(
            "Pilih Mode Operasi Aplikasi:",
            choices=[
                "📥 1. Mode Utama (Download Lagu/Playlist dari YouTube)",
                "🛠️ 2. Mode Retrofit (Otomatis Cari & Suntik Lirik/Cover ke File Lama)"
            ],
            style=custom_theme,
            use_indicator=True
        ).ask()
        
        if mode.startswith("🛠️"):
            run_retrofit()
            if not questionary.confirm("\n🔄 Kembali ke menu utama?", default=True, style=custom_theme).ask():
                console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
                break
            continue

        # MODE DOWNLOAD UTAMA
        url_or_search = questionary.text("Masukkan URL YouTube ATAU Ketik Judul Lagu:", style=custom_theme).ask()
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
            final_target = f"ytsearch{search_limit}:{url_or_search}"
            display_target = f"Pencarian: '{url_or_search}' (Top {search_limit})"
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
        download_lyrics = questionary.confirm("🎤 Download & Sinkronisasi Lirik (.lrc)?", default=True, style=custom_theme).ask()

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
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s',
            'noplaylist': False,
            'ignoreerrors': True,
            'geo_bypass': True,
            'sleep_interval_requests': 1,  # Jeda aman saat ekstraksi list lagu
            'sleep_interval': 2,           # Jeda acak minimal 2 detik sebelum unduh
            'max_sleep_interval': 5,       # Jeda acak maksimal 5 detik (menghindari deteksi bot)
            'quiet': True,
            'no_warnings': True,
            'logger': YTDLPLogger(),
            'extract_flat': False,
        }
        if anti_duplicate: ydl_opts['download_archive'] = archive_file
        if download_lyrics:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['id', 'en', 'ja', 'ko', 'all']
            ydl_opts['sleep_interval_subtitles'] = 1 # Jeda 1 detik mencegah limitasi YouTube (HTTP 429)

        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': selected_fmt['codec']}]
        if selected_fmt['quality']: pp[0]['preferredquality'] = selected_fmt['quality']
        pp.append({'key': 'FFmpegMetadata', 'add_metadata': True})
        if not is_wav:
            ydl_opts['writethumbnail'] = True
            pp.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
        if download_lyrics: pp.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'})
            
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
                    ydl.download([final_target])
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
