"""
Mode 1, 4, 5: Main Download Loop (YouTube / Spotify / SoundCloud).

Ini modul terbesar — berisi:
- Main menu loop
- Format selection (MP3/FLAC/WAV)
- Lyrics mode selection
- Spotify URL parsing → ytsearch per-track
- YouTube/SoundCloud URL atau search
- Konfigurasi table + eksekusi unduhan via yt-dlp
- Post-download lyrics processing (transliteration + translation + sync)

Dipisah dari downloader.py untuk Fase 2.2 module extraction.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
import time
from pathlib import Path

import questionary
import yt_dlp
from rich import box
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from mmpd.config import get_config, get_output_dir, is_termux
from mmpd.logger import get_logger
from mmpd.lyrics import fetch_synced_lyrics, process_translation, process_transliteration, sync_huawei_lrc
from mmpd.spotify import build_ytsearch_query, is_spotify_url, parse_spotify_url_safe
from mmpd.ui import (
    FORMAT_OPTIONS,
    LYRICS_MODE_CHOICES,
    MODE_CHOICES,
    TRANSLITERATE_CHOICES,
    ask_confirm,
    ask_int,
    ask_select,
    ask_text,
    console,
    custom_theme,
    print_banner,
)
from mmpd.utils.ffmpeg import check_ffmpeg_available
from mmpd.utils.fs import atomic_write_text
from mmpd.ytdlp import YTDLPLogger, build_download_opts, default_download_hook

_log = get_logger()


def _check_dependencies() -> bool:
    """Cek ffmpeg. Tampilkan Panel error jika missing."""
    if check_ffmpeg_available():
        return True
    console.print(
        Panel(
            "[bold red]Dependensi Sistem Hilang![/bold red]\n\n"
            "Aplikasi ini membutuhkan [bold yellow]FFmpeg[/bold yellow] untuk melakukan konversi audio.\n"
            "Silakan install FFmpeg terlebih dahulu.",
            title="⚠️ Sistem Belum Siap",
            border_style="red",
        )
    )
    return False


def run_cli() -> None:
    """Main interactive CLI loop."""
    if not _check_dependencies():
        sys.exit(1)

    while True:
        print_banner()

        # === PILIH MODE ===
        selected_mode = ask_select("Pilih Mode Operasi Aplikasi:", list(MODE_CHOICES.keys()))
        if selected_mode is None:
            break  # user cancel
        mode = MODE_CHOICES[selected_mode]

        if mode == 2:
            from mmpd.modes.retrofit import run_retrofit
            run_retrofit()
            if not ask_confirm("\n🔄 Kembali ke menu utama?", default=True):
                console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
                break
            continue
        elif mode == 3:
            from mmpd.modes.organizer import run_organizer
            run_organizer()
            if not ask_confirm("\n🔄 Kembali ke menu utama?", default=True):
                console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")
                break
            continue

        # === MODE DOWNLOAD UTAMA (1/4/5) ===
        _run_download_loop(mode)


def _run_download_loop(mode: int) -> None:
    """Mode 1 (YouTube) / 4 (Spotify) / 5 (SoundCloud) — prompt + eksekusi."""
    is_spotify_mode = mode == 4
    is_soundcloud_mode = mode == 5
    spotify_targets: list[str] = []

    if is_spotify_mode:
        spotify_targets = _gather_spotify_targets()
        if not spotify_targets:
            return
        max_songs = _ask_max_songs(spotify_targets, "dari playlist")
        if max_songs:
            spotify_targets = spotify_targets[:max_songs]
        final_target = None
        display_target = f"Spotify Playlist/Track ({len(spotify_targets)} lagu)"
    else:
        final_target, display_target, max_songs = _gather_youtube_or_soundcloud_target(is_soundcloud_mode)
        if final_target is None and not display_target:
            return

    # === PILIH FORMAT AUDIO ===
    selected_key = ask_select("Pilih Kualitas Audio:", list(FORMAT_OPTIONS.keys()))
    if selected_key is None:
        return
    selected_fmt = FORMAT_OPTIONS[selected_key]

    # === ANTI-DUPLICATE ===
    console.print()
    anti_duplicate = ask_confirm("🛡️ Aktifkan Anti-Duplikat (Lewati lagu lama)?", default=True)

    # === LYRICS CONFIG ===
    console.print()
    lyrics_mode = ask_select("📝 Pilih Sumber & Mesin Lirik (Sangat Penting):", LYRICS_MODE_CHOICES)
    if lyrics_mode is None:
        return
    download_lyrics = not lyrics_mode.startswith("❌ 4")

    transliterate = "❌ 1"
    translate_id = False
    if download_lyrics:
        console.print()
        transliterate = ask_select(
            "🔤 Ubah Huruf Asing (Jepang/Mandarin/Korea/Thai dll) ke Tulisan Biasa (Romaji/Pinyin/Latin)?",
            TRANSLITERATE_CHOICES,
        )
        if transliterate is None:
            return
        translate_id = ask_confirm(
            "🌐 Terjemahkan Lirik ke Bahasa Indonesia (Otomatis ditambahkan di bawah teks asli)?",
            default=False,
        )

    sync_huawei = False
    if download_lyrics and is_termux():
        console.print()
        sync_huawei = ask_confirm(
            "📱 Aktifkan Sinkronisasi Lirik khusus Huawei/HarmonyOS (Kopi ke folder Music/Musiclrc)?",
            default=False,
        )

    output_dir = get_output_dir()
    archive_file = os.path.join(output_dir, "archive.txt")

    # === TAMPILKAN TABEL KONFIGURASI ===
    _print_config_table(
        display_target=display_target,
        max_songs=max_songs,
        fmt_name=selected_fmt["name"],
        fmt_codec=selected_fmt["codec"],
        anti_duplicate=anti_duplicate,
        download_lyrics=download_lyrics,
        output_dir=output_dir,
    )

    if not ask_confirm("▶️ Mulai eksekusi unduhan sekarang?", default=True):
        return

    # === EKSEKUSI UNDUHAN ===
    os.makedirs(output_dir, exist_ok=True)
    if is_spotify_mode:
        outtmpl_path = f"{output_dir}/Spotify_Downloads/%(title)s.%(ext)s"
    elif is_soundcloud_mode:
        outtmpl_path = f"{output_dir}/SoundCloud_Downloads/%(playlist_title)s/%(title)s.%(ext)s"
    else:
        outtmpl_path = f"{output_dir}/%(playlist_title)s/%(title)s.%(ext)s"

    ydl_opts = build_download_opts(
        outtmpl=outtmpl_path,
        codec=selected_fmt["codec"],
        quality=selected_fmt.get("quality"),
        archive_file=archive_file if anti_duplicate else None,
        lyrics_from_youtube_cc=lyrics_mode.startswith("📺 3"),
        max_songs=max_songs,
    )

    # === PROGRESS BAR + DOWNLOAD ===
    console.print("")
    with Progress(
        SpinnerColumn(spinner_name="dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="green"),
        TaskProgressColumn(),
        console=console,
        expand=False,
    ) as progress:
        main_task = progress.add_task("[cyan]Menganalisis URL & Metadata...", total=None)
        hook = default_download_hook(progress, main_task)
        ydl_opts["progress_hooks"] = [hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if is_spotify_mode:
                    for track in spotify_targets:
                        try:
                            search_q = build_ytsearch_query(track, limit=1)
                            ydl.download([search_q])
                        except Exception as e:
                            console.print(f"[dim red]❌ Gagal unduh '{track[:40]}...': {e}[/dim red]")
                            _log.error("Spotify track failed '%s': %s", track, e)
                else:
                    ydl.download([final_target])

            # === POST-DOWNLOAD LYRICS PROCESSING ===
            if download_lyrics:
                progress.update(main_task, description="[cyan]Memproses Lirik & Transliterasi...", total=None)

                # 1. Bersihkan file lirik dengan suffix bahasa
                if lyrics_mode.startswith("📺 3"):
                    _cleanup_yt_subtitle_lrc(output_dir)

                # 2. Cari lirik untuk setiap file audio
                _process_lyrics_for_all_audio(
                    output_dir=output_dir,
                    lyrics_mode=lyrics_mode,
                    transliterate=transliterate,
                    translate_id=translate_id,
                    sync_huawei=sync_huawei,
                    progress=progress,
                    main_task=main_task,
                )

            progress.update(main_task, description="[bold green]✨ Seluruh tugas selesai!", completed=100, total=100)
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red]❌ Kegagalan fatal:[/bold red] {e}")
            _log.error("Download fatal: %s", e, exc_info=True)

    console.print()
    if not ask_confirm("🔄 Ingin mengunduh sesuatu yang lain?", default=False):
        console.print("\n[bold magenta]Terima kasih telah menggunakan aplikasi ini! 👋[/bold magenta]\n")


# ============================================================================
# HELPER FUNCTIONS (private)
# ============================================================================

def _gather_spotify_targets() -> list[str]:
    """Prompt URL Spotify, parse, return list of "Artist Title" queries."""
    url = ask_text("🎵 Masukkan URL Track/Playlist/Album Spotify:")
    if not url or not is_spotify_url(url):
        console.print("[red]⚠️ URL Spotify tidak valid![/red]")
        time.sleep(1)
        return []

    console.print("[cyan]🔍 Membaca metadata dari Spotify...[/cyan]")
    targets = parse_spotify_url_safe(url)
    if not targets:
        console.print("[red]⚠️ Gagal mengambil data Spotify atau playlist kosong![/red]")
        time.sleep(1)
        return []

    console.print(f"[bold green]✅ Ditemukan {len(targets)} lagu dari Spotify![/bold green]")
    return targets


def _ask_max_songs(targets: list, source_label: str) -> int | None:
    """Tanya apakah user mau batasi jumlah lagu."""
    if not ask_confirm(
        f"Batasi jumlah lagu yang diunduh (dari {len(targets)} lagu)?", default=False
    ):
        return None
    return ask_int("Berapa maksimal lagu? (Angka):", min_value=1)


def _gather_youtube_or_soundcloud_target(is_soundcloud_mode: bool):
    """Prompt URL atau search query untuk YouTube/SoundCloud."""
    prompt_text = (
        "☁️ Masukkan URL SoundCloud ATAU Ketik Judul Lagu:"
        if is_soundcloud_mode
        else "Masukkan URL YouTube ATAU Ketik Judul Lagu:"
    )
    url = ask_text(prompt_text)
    if not url:
        console.print("[red]⚠️ Input tidak boleh kosong![/red]")
        time.sleep(1)
        return None, "", None

    url = url.strip()
    is_search = not (url.startswith("http://") or url.startswith("https://") or url.startswith("www."))

    max_songs = None
    if ask_confirm(
        f"Batasi jumlah lagu yang diunduh "
        f"{'dari hasil pencarian' if is_search else 'dari playlist'} ini?",
        default=False,
    ):
        max_songs = ask_int("Berapa maksimal lagu? (Angka):", min_value=1)

    if is_search:
        search_limit = max_songs if max_songs else 1
        search_prefix = "scsearch" if is_soundcloud_mode else "ytsearch"
        final_target = f"{search_prefix}{search_limit}:{url}"
        platform_name = "SoundCloud" if is_soundcloud_mode else "YouTube"
        display_target = f"Pencarian {platform_name}: '{url}' (Top {search_limit})"
    else:
        final_target = url
        display_target = url

    return final_target, display_target, max_songs


def _print_config_table(
    display_target: str,
    max_songs: int | None,
    fmt_name: str,
    fmt_codec: str,
    anti_duplicate: bool,
    download_lyrics: bool,
    output_dir: str,
) -> None:
    """Tampilkan tabel ringkasan konfigurasi sebelum eksekusi."""
    console.print("\n")
    table = Table(
        title="📋 [bold bright_white]Konfigurasi Sistem Unduhan[/bold bright_white]",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Parameter", justify="right", style="cyan", no_wrap=True)
    table.add_column("Nilai", style="magenta")

    table.add_row("🎯 Target", display_target)
    table.add_row("🔢 Batas Lagu", str(max_songs) if max_songs else "Semua (Tanpa Batas)")
    table.add_row("🎵 Format Audio", fmt_name)
    is_wav = fmt_codec == "wav"
    table.add_row("🖼️ ID3 & Cover Art", "[green]✅ Aktif[/green]" if not is_wav else "[yellow]⚠️ Tidak (WAV)[/yellow]")
    table.add_row("🛡️ Anti-Duplikat", "[green]✅ Aktif[/green]" if anti_duplicate else "[red]❌ Nonaktif[/red]")
    table.add_row(
        "🎤 Download Lirik",
        "[green]✅ Aktif (.lrc)[/green]" if download_lyrics else "[red]❌ Nonaktif[/red]",
    )
    table.add_row("📁 Folder Simpan", f"[yellow]{output_dir}[/yellow]")

    console.print(table)
    console.print()


def _cleanup_yt_subtitle_lrc(output_dir: str) -> None:
    """Rename file .en.lrc / .ja.lrc menjadi .lrc (yt-dlp output default)."""
    for lrc_file in glob.glob(os.path.join(output_dir, "**", "*.lrc"), recursive=True):
        parts = lrc_file.rsplit(".", 2)
        if len(parts) == 3 and len(parts[1]) <= 3:
            new_path = f"{parts[0]}.lrc"
            if os.path.exists(new_path):
                os.remove(new_path)
            try:
                shutil.move(lrc_file, new_path)
            except Exception as e:
                _log.warning("Gagal rename LRC %s: %s", lrc_file, e)


def _process_lyrics_for_all_audio(
    output_dir: str,
    lyrics_mode: str,
    transliterate: str,
    translate_id: bool,
    sync_huawei: bool,
    progress: Progress,
    main_task,
) -> None:
    """Cari & proses lirik untuk semua file audio yang baru diunduh."""
    for root, _, files in os.walk(output_dir):
        for file in files:
            if not (file.endswith(".mp3") or file.endswith(".flac") or file.endswith(".wav")):
                continue

            song_title = os.path.splitext(file)[0]
            lrc_path = os.path.join(root, f"{song_title}.lrc")

            # Jika lirik belum ada dan pakai Mode 1/2 (Spotify/syncedlyrics via chain)
            if (
                lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")
            ) and not os.path.exists(lrc_path):
                query = None
                if lyrics_mode.startswith("✍️ 2"):
                    progress.stop()
                    query = ask_text(f"📝 Masukkan judul Spotify untuk '{song_title}':")
                    progress.start()
                fetch_synced_lyrics(
                    title=song_title,
                    lrc_path=lrc_path,
                    sync_huawei=sync_huawei,
                    transliterate_mode=transliterate,
                    override_query=query,
                    translate_mode=translate_id,
                )
            elif os.path.exists(lrc_path):
                # Lirik sudah ada (dari YouTube CC) — apply post-processing
                process_transliteration(lrc_path, transliterate)
                process_translation(lrc_path, translate_id)
                if sync_huawei:
                    sync_huawei_lrc(lrc_path)

            # Peringatan jika lirik tidak ditemukan
            if not os.path.exists(lrc_path):
                progress.stop()
                console.print(
                    f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {song_title[:30]}...[/bold yellow]"
                )
                progress.start()
