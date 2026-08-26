import os
import sys
import shutil
from pathlib import Path
import yt_dlp
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    DownloadColumn, 
    TransferSpeedColumn, 
    TimeRemainingColumn
)

console = Console()

class YTDLPLogger:
    """Custom Logger untuk membisukan log bawaan yt-dlp agar UI tetap bersih"""
    def debug(self, msg):
        pass # Sembunyikan debug
    def warning(self, msg):
        pass # Sembunyikan warning
    def error(self, msg):
        # Abaikan error dari metadata/thumbnail jika format tidak mendukung (seperti WAV)
        if "metadata" not in msg.lower() and "thumbnail" not in msg.lower():
            console.print(f"[bold red]❌ Error yt-dlp:[/bold red] {msg}")

def check_dependencies():
    """Mengecek apakah sistem memiliki dependensi yang diwajibkan"""
    missing = []
    if not shutil.which('ffmpeg'):
        missing.append("FFmpeg")
    return missing

def run_cli():
    # 1. Pengecekan Dependensi Secara Proaktif
    missing_deps = check_dependencies()
    if missing_deps:
        console.print(Panel(
            f"[bold red]Dependensi Sistem Hilang![/bold red]\n\n"
            f"Aplikasi ini membutuhkan [bold yellow]{', '.join(missing_deps)}[/bold yellow] untuk melakukan konversi audio.\n"
            f"Silakan install terlebih dahulu.\n\n"
            f"- Ubuntu/Debian: sudo apt install ffmpeg\n"
            f"- Windows: winget install ffmpeg\n"
            f"- Mac: brew install ffmpeg",
            title="⚠️ Sistem Belum Siap", border_style="red"
        ))
        sys.exit(1)

    while True:
        # 2. UI yang Bersih dan Terorganisir
        console.clear()
        
        banner = Text()
        banner.append("🚀 YT Mix & Playlist Downloader Pro 🚀\n", style="bold cyan")
        banner.append("Ultimate Performance & Lossless Quality Edition\n\n", style="italic white")
        banner.append("Created by ", style="white")
        banner.append("NanoMindExplorer", style="bold yellow")
        banner.justify = "center"
        
        console.print(Panel(
            banner, 
            border_style="bold blue", 
            padding=(1, 2),
            title="[bold magenta]v1.1 - Cover Art Editon[/bold magenta]",
            title_align="right",
            subtitle="[dim]Open Source CLI Tool[/dim]",
            subtitle_align="center"
        ))

        # 3. Validasi URL / Pencarian
        url_or_search = Prompt.ask("\n[bold yellow]🔗 Masukkan URL YouTube ATAU Ketik Judul Lagu[/bold yellow]").strip()
        if not url_or_search:
            console.print("[red]⚠️ Input tidak boleh kosong![/red]")
            Confirm.ask("Tekan Enter untuk mengulang...", default=True)
            continue
            
        is_search = not (url_or_search.startswith("http://") or url_or_search.startswith("https://") or url_or_search.startswith("www."))
            
        limit_choice = Confirm.ask(f"[bold yellow]❓ Batasi jumlah lagu yang diunduh {'dari hasil pencarian ' if is_search else 'dari playlist '}ini?[/bold yellow]", default=False)
        max_songs = IntPrompt.ask("[bold yellow]🎵 Berapa maksimal lagu yang ingin diunduh?[/bold yellow]", default=10) if limit_choice else None
        
        if is_search:
            # Jika berupa teks, format menggunakan sintaks ytsearch bawaan yt-dlp
            search_limit = max_songs if max_songs else 1
            final_target = f"ytsearch{search_limit}:{url_or_search}"
            display_target = f"Pencarian: '{url_or_search}' (Top {search_limit} Hasil)"
        else:
            final_target = url_or_search
            display_target = url_or_search
        
        # 4. Pilihan Format Menggunakan Data Structure yang Solid
        console.print("\n[bold cyan]Pilihan Kualitas Audio:[/bold cyan]")
        console.print("  [1] MP3 (320kbps)  - Default (Kualitas Tinggi, Ukuran Ringan)")
        console.print("  [2] FLAC (Lossless)- Best Quality murni tanpa kompresi (Ukuran Besar)")
        console.print("  [3] WAV (Uncompressed) - Kualitas Mentah/Studio (Sangat Besar, No Cover Art)")
        console.print("  [4] Original Audio - Format bawaan YouTube (Opus/M4A) tanpa konversi")
        
        format_choice = Prompt.ask("[bold yellow]Pilih format (1/2/3/4)[/bold yellow]", choices=["1", "2", "3", "4"], default="1")
        
        format_map = {
            "1": {"codec": "mp3", "quality": "320", "name": "MP3 (320kbps)"},
            "2": {"codec": "flac", "quality": None, "name": "FLAC (Lossless)"},
            "3": {"codec": "wav", "quality": None, "name": "WAV (Uncompressed)"},
            "4": {"codec": "best", "quality": None, "name": "Original Audio (Best)"},
        }
        selected_fmt = format_map[format_choice]

        # 5. Fitur Anti-Duplikat
        console.print("")
        anti_duplicate = Confirm.ask("[bold yellow]🛡️ Aktifkan fitur Anti-Duplikat (Lewati otomatis lagu yang pernah diunduh)?[/bold yellow]", default=True)

        # Menetapkan path ke folder Download utama
        # Deteksi pintar jika dijalankan di dalam Termux (Android)
        if "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
            output_dir = str(Path.home() / "storage" / "downloads" / "YT_Downloader")
        else:
            output_dir = str(Path.home() / "Downloads" / "YT_Downloader")
            
        archive_file = os.path.join(output_dir, "archive.txt")
        
        # Panel Ringkasan
        summary = Text()
        summary.append("Target       : ", style="bold white")
        summary.append(f"{display_target}\n", style="cyan")
        summary.append("Batas Lagu   : ", style="bold white")
        summary.append(f"{max_songs if max_songs else 'Semua (Tanpa Batas)'}\n", style="green")
        summary.append("Format       : ", style="bold white")
        summary.append(f"{selected_fmt['name']}\n", style="magenta")
        summary.append("ID3 & Cover  : ", style="bold white")
        summary.append("✅ Aktif (Embed Metadata & Thumbnail)\n" if selected_fmt['codec'] != 'wav' else "⚠️ Tidak Aktif (WAV tidak mendukung Cover)\n", style="green" if selected_fmt['codec'] != 'wav' else "yellow")
        summary.append("Anti-Duplikat: ", style="bold white")
        summary.append("✅ Aktif\n" if anti_duplicate else "❌ Tidak Aktif\n", style="green" if anti_duplicate else "red")
        summary.append("Folder       : ", style="bold white")
        summary.append(f"{output_dir}\n", style="yellow")
        
        console.print(Panel(summary, title="[bold blue]Ringkasan Tugas[/bold blue]", border_style="blue"))
        
        if not Confirm.ask("[bold green]▶️ Mulai unduhan sekarang?[/bold green]", default=True):
            console.print("[yellow]Unduhan dibatalkan pengguna.[/yellow]")
            continue

        # 5. Persiapan Engine yt-dlp
        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s',
            'noplaylist': False,
            'ignoreerrors': True,     # Lanjutkan walau ada video private/copyright
            'quiet': True,            # Matikan log default yang berantakan
            'no_warnings': True,      # Sembunyikan warning
            'logger': YTDLPLogger(),  # Gunakan custom logger
            'extract_flat': False,
        }
        
        if anti_duplicate:
            ydl_opts['download_archive'] = archive_file

        # --- KONFIGURASI METADATA & COVER ART (THUMBNAIL) ---
        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': selected_fmt['codec']}]
        
        # Set bitrate jika tersedia (contoh: MP3 320k)
        if selected_fmt['quality']:
            pp[0]['preferredquality'] = selected_fmt['quality']
            
        # 1. Selalu tambahkan ID3 Metadata (Judul, Artis, Channel)
        pp.append({'key': 'FFmpegMetadata', 'add_metadata': True})
        
        # 2. Tambahkan Embed Cover Art (Thumbnail) jika formatnya mendukung
        # WAV format sangat tidak disarankan menggunakan embedded album art karena standar yang tidak baku
        if selected_fmt['codec'] != 'wav':
            ydl_opts['writethumbnail'] = True
            pp.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
            
        ydl_opts['postprocessors'] = pp
        
        if max_songs:
            ydl_opts['playlistend'] = max_songs

        # 6. Render UI Progress Bar yang Sangat Modern
        console.print("") # Spasi
        with Progress(
            SpinnerColumn(spinner_name="dots2", style="cyan"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40, style="blue", complete_style="green"),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=False
        ) as progress:
            
            # Task indeterminate untuk fase analisis playlist
            main_task = progress.add_task("[cyan]Menganalisis URL & Metadata...", total=None)
            
            # Hook untuk mengupdate Progress Bar secara Real-Time
            def download_hook(d):
                status = d['status']
                if status == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    if len(filename) > 35:
                        filename = filename[:32] + "..."
                        
                    progress.update(
                        main_task,
                        description=f"[cyan]Mengunduh: [bold white]{filename}",
                        total=total if total > 0 else None,
                        completed=downloaded
                    )
                elif status == 'finished':
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    if len(filename) > 35:
                        filename = filename[:32] + "..."
                    # Ubah status ke indeterminate saat merender audio, cover art, dan metadata
                    progress.update(main_task, description=f"[green]Menyematkan Metadata & Cover Art: [bold white]{filename}", total=None, completed=0)

            ydl_opts['progress_hooks'] = [download_hook]

            # Eksekusi yt-dlp
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([final_target])
                
                # Selesaikan task progress
                progress.update(main_task, description="[bold green]✨ Seluruh tugas selesai!", completed=100, total=100)
                
            except Exception as e:
                progress.stop()
                console.print(f"\n[bold red]❌ Terjadi kegagalan fatal pada engine unduhan:[/bold red] {e}")

        # Pilihan Looping
        if not Confirm.ask("\n[bold cyan]🔄 Ingin mendownload URL/Playlist lain?[/bold cyan]", default=False):
            console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! Sampai jumpa 👋[/bold magenta]\n")
            break

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Aplikasi dihentikan secara paksa (Ctrl+C).[/bold red]")
        sys.exit(0)
