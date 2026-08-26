import os
import sys
import yt_dlp
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text

console = Console()

def clear_screen():
    # Membersihkan layar terminal
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    banner = Text("🎵 YT Mix & Playlist Downloader 🎵\n", style="bold cyan", justify="center")
    banner.append("Interactive CLI - Download audio MP3/FLAC/WAV", style="italic white")
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))

def download_audio(url, max_songs=None, output_dir="downloads", format_choice="1"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Konfigurasi codec berdasarkan pilihan pengguna
    if format_choice == "2":
        codec = 'flac'
        quality_val = None
        format_desc = "FLAC (Lossless/Best Quality)"
    elif format_choice == "3":
        codec = 'wav'
        quality_val = None
        format_desc = "WAV (Uncompressed/Best Quality)"
    elif format_choice == "4":
        codec = 'best' # Mempertahankan format original terbaik dari YouTube (biasanya Opus/M4A)
        quality_val = None
        format_desc = "Original (Opus/M4A/Best)"
    else:
        codec = 'mp3'
        quality_val = '320'
        format_desc = "MP3 (320kbps)"

    postprocessors_config = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': codec,
    }]
    
    if quality_val:
        postprocessors_config[0]['preferredquality'] = quality_val

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': postprocessors_config,
        'outtmpl': f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s',
        'noplaylist': False,
        'ignoreerrors': True,
        'quiet': False, # Membiarkan yt-dlp menampilkan progress bar bawaannya
    }
    
    if max_songs:
        ydl_opts['playlistend'] = max_songs

    console.print(f"\n[bold green][*] Menghubungkan ke YouTube...[/bold green]")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        console.print(f"\n[bold green]✅ Selesai! Semua lagu berhasil diunduh dalam format {format_desc}.[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Terjadi kesalahan:[/bold red] {e}")

def main():
    while True:
        clear_screen()
        show_banner()
        
        url = Prompt.ask("\n[bold yellow]🔗 Masukkan URL YouTube (Playlist/Mix)[/bold yellow]")
        
        if not url.strip():
            console.print("[red]URL tidak boleh kosong! Silakan coba lagi.[/red]")
            Confirm.ask("Tekan Enter untuk mengulang...", default=True)
            continue
            
        limit_choice = Confirm.ask("[bold yellow]❓ Apakah Anda ingin membatasi jumlah lagu yang diunduh?[/bold yellow]", default=False)
        
        max_songs = None
        if limit_choice:
            max_songs = IntPrompt.ask("[bold yellow]🎵 Masukkan jumlah maksimal lagu[/bold yellow]", default=10)
        
        # Pilihan Kualitas Audio
        console.print("\n[bold cyan]Pilihan Kualitas Audio:[/bold cyan]")
        console.print("  [1] MP3 (320kbps) - Kualitas tinggi, ukuran ringan (Default)")
        console.print("  [2] FLAC (Lossless) - Best Quality murni, ukuran besar")
        console.print("  [3] WAV (Uncompressed) - Kualitas CD/Studio, ukuran sangat besar")
        console.print("  [4] Original - Format audio asli (Opus/M4A) tanpa konversi")
        
        format_choice = Prompt.ask("[bold yellow]Pilih format (1/2/3/4)[/bold yellow]", choices=["1", "2", "3", "4"], default="1")
        
        if format_choice == "2":
            format_name = "FLAC (Lossless/Best Quality)"
        elif format_choice == "3":
            format_name = "WAV (Uncompressed/Best Quality)"
        elif format_choice == "4":
            format_name = "Original Audio (Best)"
        else:
            format_name = "MP3 (320kbps)"

        # Panel Ringkasan
        summary = Text()
        summary.append("URL Target  : ", style="bold white")
        summary.append(f"{url}\n", style="cyan")
        summary.append("Batas Lagu  : ", style="bold white")
        summary.append(f"{max_songs if max_songs else 'Semua (Tanpa Batas)'}\n", style="green")
        summary.append("Kualitas    : ", style="bold white")
        summary.append(f"{format_name}\n", style="magenta")
        summary.append("Folder      : ", style="bold white")
        summary.append("./downloads/", style="yellow")
        
        console.print(Panel(summary, title="[bold blue]Ringkasan Tugas[/bold blue]", border_style="blue"))
        
        start = Confirm.ask("[bold green]▶️  Mulai proses unduhan sekarang?[/bold green]", default=True)
        
        if start:
            download_audio(url, max_songs, format_choice=format_choice)
        else:
            console.print("[yellow]Unduhan dibatalkan.[/yellow]")
            
        again = Confirm.ask("\n[bold cyan]🔄 Ingin mendownload playlist lain?[/bold cyan]", default=False)
        if not again:
            console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! Sampai jumpa 👋[/bold magenta]\n")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Aplikasi dihentikan secara paksa (Ctrl+C).[/bold red]")
        sys.exit(0)
