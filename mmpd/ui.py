"""
UI helpers — banner, theme, common questionary helpers.

Memisahkan konstanta UI dan helper dari downloader.py agar:
- Theme bisa di-override tanpa modif entry point
- Helper questionary reusable
- Banner mudah di-update
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Singleton console untuk semua output
console = Console()

# Theme questionary bergaya Cyberpunk (sama dengan Fase 1)
custom_theme = questionary.Style([
    ("qmark", "fg:#00ffff bold"),
    ("question", "bold white"),
    ("answer", "fg:#00ff00 bold"),
    ("pointer", "fg:#ff00ff bold"),
    ("highlighted", "fg:#ff00ff bold"),
    ("selected", "fg:#00ff00"),
    ("instruction", "fg:#808080 italic"),
])


def print_banner() -> None:
    """Cetak banner Cyberpunk di console (clear screen first)."""
    console.clear()
    banner = Text()
    banner.append("✦ ════════════════════════════════════════════ ✦\n", style="bold cyan")
    banner.append(" High-Fidelity & Lossless Audio Engine \n", style="italic bright_white")
    banner.append("✦ ════════════════════════════════════════════ ✦\n\n", style="bold cyan")
    banner.append("Artfully Crafted by\n", style="dim white")
    banner.append("✦ NanoMindExplorer ✦", style="bold bright_yellow")
    banner.justify = "center"
    console.print(
        Panel(
            banner,
            box=box.DOUBLE,
            border_style="bold magenta",
            padding=(1, 4),
            title="[bold bright_white on magenta] 🎵 YT AUDIO DOWNLOADER PRO [/bold bright_white on magenta]",
            title_align="center",
            subtitle="[bold white]v3.1[/bold white] [dim]• Interactive CLI & Retrofit Engine[/dim]",
            subtitle_align="center",
        )
    )
    console.print()


def ask_text(message: str, default: str = "") -> Optional[str]:
    """Helper: prompt text input dengan theme."""
    return questionary.text(message, default=default, style=custom_theme).ask()


def ask_select(message: str, choices: List[str], use_indicator: bool = True) -> Optional[str]:
    """Helper: prompt select dengan theme."""
    return questionary.select(
        message,
        choices=choices,
        style=custom_theme,
        use_indicator=use_indicator,
    ).ask()


def ask_confirm(message: str, default: bool = False) -> bool:
    """Helper: prompt yes/no dengan theme."""
    return questionary.confirm(message, default=default, style=custom_theme).ask()


def ask_int(message: str, min_value: int = 1) -> Optional[int]:
    """Helper: prompt integer input dengan validation loop."""
    while True:
        raw = questionary.text(message, style=custom_theme).ask()
        if not raw:
            return None
        if raw.isdigit() and int(raw) >= min_value:
            return int(raw)
        console.print(f"[red]⚠️ Masukkan angka valid (>= {min_value})![/red]")


# Pilihan untuk menu utama
MODE_CHOICES: Dict[str, int] = {
    "📥 1. Mode Utama (Download Lagu/Playlist dari YouTube)": 1,
    "🛠️ 2. Mode Retrofit (Otomatis Cari & Suntik Lirik/Cover ke File Lama)": 2,
    "📁 3. Mode Pengatur Otomatis (Rapikan File Lirik/MP3 Unduhan Manual)": 3,
    "🎵 4. Mode Spotify (Download Lagu/Playlist dari Spotify)": 4,
    "☁️  5. Mode SoundCloud (Download Lagu/Playlist dari SoundCloud)": 5,
}

# Pilihan sumber lirik
LYRICS_MODE_CHOICES: List[str] = [
    "🎧 1. Mesin Spotify/Musixmatch (Anti-Blokir YT) - Terbaik untuk Lagu Asli (Original)",
    "✍️ 2. Mesin Spotify (Input Judul Manual) - Terbaik jika judul Spotify berbeda dari YouTube",
    "📺 3. Mesin YouTube Subtitles (Rawan 429) - Terbaik untuk Lagu Cover (Timing 100% Akurat)",
    "❌ 4. Jangan download lirik",
]

# Pilihan transliterasi
TRANSLITERATE_CHOICES: List[str] = [
    "❌ 1. Biarkan Aslinya (Jangan diubah)",
    "🇯🇵 2. Ya, Ubah Huruf Jepang ke Romaji (Khusus Lagu Jepang/Anime)",
    "🇨🇳 3. Ya, Ubah Huruf Mandarin ke Pinyin (Khusus Lagu China)",
    "🤖 4. Deteksi Otomatis & Ubah Semua (Khusus Playlist Campur/Berbagai Negara)",
]

# Pilihan format audio
FORMAT_OPTIONS: Dict[str, Dict[str, Any]] = {
    "MP3 (320kbps) - Default (Tinggi)": {"codec": "mp3", "quality": "320", "name": "MP3 (320kbps)"},
    "FLAC (Lossless) - Best Quality murni": {"codec": "flac", "quality": None, "name": "FLAC (Lossless)"},
    "WAV (Uncompressed) - Mentah": {"codec": "wav", "quality": None, "name": "WAV (Uncompressed)"},
    "Original Audio - Bawaan YouTube": {"codec": "best", "quality": None, "name": "Original Audio"},
}

# Pilihan target retrofit (apa yang akan di-inject)
RETROFIT_TARGET_CHOICES: List[str] = [
    "✨ 1. Perbaiki Lirik & Cover Art (Lengkap)",
    "📝 2. Perbaiki Lirik Saja (Abaikan Cover)",
    "🖼️ 3. Perbaiki Cover Art Saja (Abaikan Lirik)",
]
