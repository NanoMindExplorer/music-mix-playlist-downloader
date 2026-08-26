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
    banner.append("Interactive CLI - Download audio MP3 320kbps", style="italic white")
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))

def download_audio(url, max_songs=None, output_dir="downloads"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': f'{output_dir}/%(playlist_title)s/%(title)s.%(ext)s',
        'noplaylist': False,
        'ignoreerrors': True,
        'quiet': False, # Membiarkan yt-dlp menampilkan progress bar bawaannya yang cukup informatif
    }
    
    if max_songs:
        ydl_opts['playlistend'] = max_songs

    console.print(f"\n[bold green][*] Menghubungkan ke YouTube...[/bold green]")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        console.print("\n[bold green]✅ Selesai! Semua lagu berhasil diunduh dan dikonversi.[/bold green]")
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
        
        # Panel Ringkasan
        summary = Text()
        summary.append("URL Target  : ", style="bold white")
        summary.append(f"{url}\n", style="cyan")
        summary.append("Batas Lagu  : ", style="bold white")
        summary.append(f"{max_songs if max_songs else 'Semua (Tanpa Batas)'}\n", style="green")
        summary.append("Kualitas    : ", style="bold white")
        summary.append("MP3 320kbps\n", style="magenta")
        summary.append("Folder      : ", style="bold white")
        summary.append("./downloads/", style="yellow")
        
        console.print(Panel(summary, title="[bold blue]Ringkasan Tugas[/bold blue]", border_style="blue"))
        
        start = Confirm.ask("[bold green]▶️  Mulai proses unduhan sekarang?[/bold green]", default=True)
        
        if start:
            download_audio(url, max_songs)
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
