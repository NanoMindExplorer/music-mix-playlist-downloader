import os
import sys
import shutil
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
    DownloadColumn, 
    TransferSpeedColumn, 
    TimeRemainingColumn,
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
        # Abaikan error dari metadata/thumbnail jika format tidak mendukung
        if "metadata" not in msg.lower() and "thumbnail" not in msg.lower():
            console.print(f"[bold red]❌ Error yt-dlp:[/bold red] {msg}")

def check_dependencies():
    missing = []
    if not shutil.which('ffmpeg'):
        missing.append("FFmpeg")
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
        banner, 
        box=box.DOUBLE, 
        border_style="bold magenta", 
        padding=(1, 4),
        title="[bold bright_white on magenta] 🎵 YT AUDIO DOWNLOADER PRO [/bold bright_white on magenta]",
        title_align="center",
        subtitle="[bold white]v2.0[/bold white] [dim]• Interactive CLI[/dim]",
        subtitle_align="center"
    ))
    console.print()

def run_cli():
    # 1. Pengecekan Dependensi
    missing_deps = check_dependencies()
    if missing_deps:
        console.print(Panel(
            f"[bold red]Dependensi Sistem Hilang![/bold red]\n\n"
            f"Aplikasi ini membutuhkan [bold yellow]{', '.join(missing_deps)}[/bold yellow] untuk melakukan konversi audio.\n"
            f"Silakan install FFmpeg terlebih dahulu.",
            title="⚠️ Sistem Belum Siap", border_style="red"
        ))
        sys.exit(1)

    # Styling modern untuk Menu Questionary (Cyberpunk / Modern Theme)
    custom_theme = questionary.Style([
        ('qmark', 'fg:#00ffff bold'),       # Simbol ? (Cyan)
        ('question', 'bold white'),         # Teks Pertanyaan (Putih)
        ('answer', 'fg:#00ff00 bold'),      # Jawaban (Hijau)
        ('pointer', 'fg:#ff00ff bold'),     # Panah pilihan (Magenta)
        ('highlighted', 'fg:#ff00ff bold'), # Pilihan saat ini tersorot (Magenta)
        ('selected', 'fg:#00ff00'),         # Pilihan terpilih
        ('instruction', 'fg:#808080 italic')# Instruksi tambahan (Abu-abu)
    ])

    while True:
        print_banner()

        # 1. URL / Pencarian (Input Teks Interaktif)
        url_or_search = questionary.text(
            "Masukkan URL YouTube ATAU Ketik Judul Lagu:",
            style=custom_theme
        ).ask()
        
        if not url_or_search:
            console.print("[red]⚠️ Input tidak boleh kosong![/red]")
            import time; time.sleep(1)
            continue
            
        url_or_search = url_or_search.strip()
        is_search = not (url_or_search.startswith("http://") or url_or_search.startswith("https://") or url_or_search.startswith("www."))
            
        # 2. Batasan Lagu (Konfirmasi Y/N)
        limit_choice = questionary.confirm(
            f"Batasi jumlah lagu yang diunduh {'dari hasil pencarian' if is_search else 'dari playlist'} ini?",
            default=False,
            style=custom_theme
        ).ask()
        
        max_songs = None
        if limit_choice:
            while True:
                limit_input = questionary.text("Berapa maksimal lagu yang ingin diunduh? (Masukkan Angka):", style=custom_theme).ask()
                if limit_input and limit_input.isdigit() and int(limit_input) > 0:
                    max_songs = int(limit_input)
                    break
                else:
                    console.print("[red]⚠️ Harap masukkan angka yang valid![/red]")
        
        if is_search:
            search_limit = max_songs if max_songs else 1
            final_target = f"ytsearch{search_limit}:{url_or_search}"
            display_target = f"Pencarian: '{url_or_search}' (Top {search_limit} Hasil)"
        else:
            final_target = url_or_search
            display_target = url_or_search
        
        # 3. Kualitas Audio menggunakan Selektor Interaktif (Arrow keys)
        console.print()
        format_options = {
            "MP3 (320kbps) - Default (Kualitas Tinggi, Ukuran Ringan)": {"codec": "mp3", "quality": "320", "name": "MP3 (320kbps)"},
            "FLAC (Lossless) - Best Quality murni tanpa kompresi": {"codec": "flac", "quality": None, "name": "FLAC (Lossless)"},
            "WAV (Uncompressed) - Kualitas Mentah/Studio": {"codec": "wav", "quality": None, "name": "WAV (Uncompressed)"},
            "Original Audio - Format bawaan YouTube (Opus/M4A)": {"codec": "best", "quality": None, "name": "Original Audio (Best)"}
        }
        
        selected_key = questionary.select(
            "Pilih Kualitas Audio yang diinginkan (Gunakan Arrow Keys ⬆️ ⬇️):",
            choices=list(format_options.keys()),
            style=custom_theme,
            use_indicator=True
        ).ask()
        
        selected_fmt = format_options[selected_key]

        # 4. Fitur Anti-Duplikat
        console.print()
        anti_duplicate = questionary.confirm(
            "🛡️ Aktifkan fitur Anti-Duplikat (Lewati otomatis lagu yang pernah diunduh)?",
            default=True,
            style=custom_theme
        ).ask()

        # Path Logika
        if "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", ""):
            output_dir = str(Path.home() / "storage" / "downloads" / "YT_Downloader")
        else:
            output_dir = str(Path.home() / "Downloads" / "YT_Downloader")
            
        archive_file = os.path.join(output_dir, "archive.txt")
        
        # 5. Tabel Dashboard Ringkasan
        console.print("\n")
        table = Table(title="📋 [bold bright_white]Konfigurasi Sistem Unduhan[/bold bright_white]", box=box.ROUNDED, border_style="cyan")
        table.add_column("Parameter", justify="right", style="cyan", no_wrap=True)
        table.add_column("Nilai", style="magenta")

        table.add_row("🎯 Target", display_target)
        table.add_row("🔢 Batas Lagu", str(max_songs) if max_songs else "Semua (Tanpa Batas)")
        table.add_row("🎵 Format Audio", selected_fmt['name'])
        
        is_wav = selected_fmt['codec'] == 'wav'
        table.add_row("🖼️ ID3 & Cover Art", "[green]✅ Aktif[/green]" if not is_wav else "[yellow]⚠️ Tidak Mendukung (WAV)[/yellow]")
        table.add_row("🛡️ Anti-Duplikat", "[green]✅ Aktif[/green]" if anti_duplicate else "[red]❌ Nonaktif[/red]")
        table.add_row("📁 Folder Simpan", f"[yellow]{output_dir}[/yellow]")
        
        console.print(table)
        console.print()
        
        start = questionary.confirm("▶️ Mulai eksekusi unduhan sekarang?", default=True, style=custom_theme).ask()
        if not start:
            console.print("[yellow]Unduhan dibatalkan pengguna.[/yellow]\n")
            import time; time.sleep(1)
            continue

        # Eksekusi yt-dlp
        os.makedirs(output_dir, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s',
            'noplaylist': False,
            'ignoreerrors': True,
            'geo_bypass': True,
            'quiet': True,
            'no_warnings': True,
            'logger': YTDLPLogger(),
            'extract_flat': False,
        }
        if anti_duplicate:
            ydl_opts['download_archive'] = archive_file

        pp = [{'key': 'FFmpegExtractAudio', 'preferredcodec': selected_fmt['codec']}]
        if selected_fmt['quality']:
            pp[0]['preferredquality'] = selected_fmt['quality']
            
        pp.append({'key': 'FFmpegMetadata', 'add_metadata': True})
        if not is_wav:
            ydl_opts['writethumbnail'] = True
            pp.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
            
        ydl_opts['postprocessors'] = pp
        if max_songs:
            ydl_opts['playlistend'] = max_songs

        console.print("")
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
            
            main_task = progress.add_task("[cyan]Menganalisis URL & Metadata...", total=None)
            
            def download_hook(d):
                status = d['status']
                if status == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    if len(filename) > 35:
                        filename = filename[:32] + "..."
                    progress.update(main_task, description=f"[cyan]Mengunduh: [bold white]{filename}", total=total if total > 0 else None, completed=downloaded)
                elif status == 'finished':
                    filename = os.path.basename(d.get('filename', 'Lagu'))
                    if len(filename) > 35:
                        filename = filename[:32] + "..."
                    progress.update(main_task, description=f"[green]Memproses Media: [bold white]{filename}", total=None, completed=0)

            ydl_opts['progress_hooks'] = [download_hook]

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([final_target])
                progress.update(main_task, description="[bold green]✨ Seluruh tugas selesai!", completed=100, total=100)
            except Exception as e:
                progress.stop()
                console.print(f"\n[bold red]❌ Terjadi kegagalan fatal:[/bold red] {e}")

        console.print()
        if not questionary.confirm("🔄 Ingin mengunduh sesuatu yang lain?", default=False, style=custom_theme).ask():
            console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! Sampai jumpa 👋[/bold magenta]\n")
            break

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Aplikasi dihentikan secara paksa (Ctrl+C).[/bold red]")
        sys.exit(0)
