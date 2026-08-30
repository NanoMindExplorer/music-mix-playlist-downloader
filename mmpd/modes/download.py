"""
Mode 1, 4, 5: Download runners (Fase A — thin re-export + non-interactive).

File ini dulunya modul 29KB berisi semuanya. Sekarang:
- UI interaktif    → mmpd/modes/menu.py
- Helper Spotify   → mmpd/modes/spotify_download.py
- Runner CLI       → run_download_noninteractive (di sini)
- Semua nama lama  → di-re-export agar import path lama tetap jalan
"""

from __future__ import annotations

import os
from typing import Optional

import yt_dlp
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from mmpd.logger import get_logger
from mmpd.lyrics import (
    fetch_synced_lyrics,
    process_translation,
    process_transliteration,
    sync_huawei_lrc,
)

# Re-export dari modul hasil pecahan (backward compat — import path lama)
from mmpd.modes.menu import (  # noqa: F401
    _ask_max_songs,
    _check_dependencies,
    _cleanup_yt_subtitle_lrc,
    _gather_spotify_targets,
    _gather_youtube_or_soundcloud_target,
    _print_config_table,
    _process_lyrics_for_all_audio,
    _run_download_loop,
    run_cli,
)
from mmpd.modes.spotify_download import (  # noqa: F401
    _download_spotify_concurrent,
    _download_spotify_with_isrc,
    _find_track_by_id,
    _gather_spotify_tracks_v2,
)
from mmpd.ui import console
from mmpd.ytdlp import build_download_opts

_log = get_logger()


# ============================================================================
# Fase C/R: Non-interactive download runner (dipakai `mmpd download`)
# ============================================================================

def _snapshot_audio_files(output_dir: str) -> dict:
    """Snapshot {path: mtime} semua file audio — untuk deteksi batch baru."""
    snapshot = {}
    if not os.path.isdir(output_dir):
        return snapshot
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.lower().endswith((".mp3", ".flac", ".wav", ".m4a", ".lrc")):
                p = os.path.join(root, f)
                try:
                    snapshot[p] = os.path.getmtime(p)
                except OSError:
                    pass
    return snapshot


def _find_new_audio_files(output_dir: str, before: dict) -> list[str]:
    """File audio yang baru muncul / berubah sejak snapshot (Fase R: hanya batch baru)."""
    new_files = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            if not f.lower().endswith((".mp3", ".flac", ".m4a")):
                continue
            p = os.path.join(root, f)
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if p not in before or mtime > before.get(p, 0):
                new_files.append(p)
    return sorted(new_files)


def run_download_noninteractive(
    url: str,
    output_dir: str,
    codec: str = "mp3",
    quality: Optional[str] = "320",
    max_songs: Optional[int] = None,
    lyrics_mode: str = "🎧 1",
    transliterate: str = "❌ 1",
    translate_id: bool = False,
    sync_huawei: bool = False,
    embed_id3: bool = True,
    anti_duplicate: bool = True,
    use_isrc: bool = True,
    use_concurrent: bool = False,
    quiet: bool = False,
) -> int:
    """
    Download non-interaktif untuk CLI `mmpd download` (Fase C).

    Alur:
        1. Snapshot isi output_dir (deteksi "batch baru" — Fase R:
           hanya file BARU yang diproses liriknya, bukan seluruh folder)
        2. Download via yt-dlp (YouTube/SoundCloud URL atau pencarian;
           Spotify URL → parse dulu ke ytsearch per-track)
        3. Post-process lirik HANYA untuk file batch baru
        4. Embed USLT/SYLT ke file audio baru

    Returns:
        Exit code (0 sukses, 1 gagal fatal).
    """
    from mmpd.id3_embed import embed_lyrics_to_audio
    from mmpd.spotify import (
        build_ytsearch_query,
        is_spotify_url,
        parse_spotify_url_safe,
        parse_spotify_url_v2,
    )

    download_lyrics = not lyrics_mode.startswith("❌ 4")

    if not quiet:
        console.print(f"\n[bold cyan]📥 Download:[/bold cyan] {url}")
        console.print(f"[dim]Format: {codec}{f' {quality}kbps' if quality else ''} → {output_dir}[/dim]\n")

    os.makedirs(output_dir, exist_ok=True)
    before = _snapshot_audio_files(output_dir)
    archive_file = os.path.join(output_dir, "archive.txt")

    # --- Spotify URL → daftar query ytsearch / ISRC ---
    targets: list[str] = [url]
    display_target = url
    spotify_tracks_v2 = None
    if is_spotify_url(url):
        try:
            spotify_tracks_v2 = parse_spotify_url_v2(url) or None
        except Exception:
            spotify_tracks_v2 = None
        try:
            tracks = parse_spotify_url_safe(url)
        except Exception as e:
            console.print(f"[bold red]❌ Gagal parse URL Spotify: {e}[/bold red]")
            return 1
        if not tracks and not spotify_tracks_v2:
            console.print(
                "[bold red]❌ Tidak bisa ambil track Spotify.[/bold red]\n"
                "[dim]Pastikan spotipy terinstal + SPOTIPY_CLIENT_ID/SECRET di-set "
                "(lihat `mmpd doctor`), atau pakai URL YouTube.[/dim]"
            )
            return 1
        if spotify_tracks_v2:
            if max_songs:
                spotify_tracks_v2 = spotify_tracks_v2[:max_songs]
            targets = [t.to_ytsearch_query() for t in spotify_tracks_v2]
        else:
            targets = [build_ytsearch_query(t, limit=1) for t in tracks]
            if max_songs:
                targets = targets[:max_songs]
        display_target = f"Spotify ({len(targets)} lagu)"
        if not quiet:
            isrc_n = sum(1 for t in (spotify_tracks_v2 or []) if getattr(t, "isrc", None))
            extra = f", {isrc_n} punya ISRC" if isrc_n else ""
            console.print(f"[green]✅ {len(targets)} track dari Spotify{extra}[/green]")
    elif not (url.startswith("http://") or url.startswith("https://")):
        limit = max_songs if max_songs else 1
        targets = [f"ytsearch{limit}:{url}"]
        display_target = f"Pencarian YouTube: '{url}' (top {limit})"

    # --- Build opts ---
    if is_spotify_url(url):
        outtmpl_path = f"{output_dir}/Spotify_Downloads/%(title)s.%(ext)s"
    elif "soundcloud.com" in url.lower():
        outtmpl_path = f"{output_dir}/SoundCloud_Downloads/%(playlist_title)s/%(title)s.%(ext)s"
    else:
        outtmpl_path = f"{output_dir}/%(playlist_title)s/%(title)s.%(ext)s"
    ydl_opts = build_download_opts(
        outtmpl=outtmpl_path,
        codec=codec,
        quality=quality,
        archive_file=archive_file if anti_duplicate else None,
        lyrics_from_youtube_cc=lyrics_mode.startswith("📺 3"),
        max_songs=max_songs,
    )

    # --- Download ---
    exit_code = 0
    with Progress(
        SpinnerColumn(spinner_name="dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="green"),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        main_task = progress.add_task(f"[cyan]Mengunduh: {display_target[:60]}", total=len(targets))
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                used_isrc = bool(
                    use_isrc and spotify_tracks_v2 and any(getattr(t, "isrc", None) for t in spotify_tracks_v2)
                )
                if used_isrc:
                    from mmpd.modes.spotify_download import _download_spotify_with_isrc
                    _download_spotify_with_isrc(
                        ydl=ydl,
                        tracks=spotify_tracks_v2,
                        use_concurrent=use_concurrent,
                        progress=progress,
                        main_task=main_task,
                    )
                elif use_concurrent and spotify_tracks_v2:
                    from mmpd.modes.spotify_download import _download_spotify_concurrent
                    _download_spotify_concurrent(
                        ydl_opts=ydl_opts,
                        tracks=spotify_tracks_v2,
                        progress=progress,
                        main_task=main_task,
                    )
                else:
                    for target in targets:
                        try:
                            ydl.download([target])
                        except Exception as e:
                            _log.error("Download gagal '%s': %s", target[:60], e)
                            if not quiet:
                                console.print(f"[dim red]❌ Gagal: {target[:60]} — {e}[/dim red]")
                        progress.advance(main_task)
        except Exception as e:
            console.print(f"\n[bold red]❌ Kegagalan fatal:[/bold red] {e}")
            _log.error("Download fatal: %s", e, exc_info=True)
            exit_code = 1

    # --- Post-process lirik: HANYA batch baru (Fase R) ---
    if download_lyrics:
        if not quiet:
            console.print("\n[cyan]🎤 Memproses lirik untuk batch baru...[/cyan]")
        new_audio = _find_new_audio_files(output_dir, before)
        if not new_audio and not quiet:
            console.print("[dim]Tidak ada file baru yang perlu diproses lirik.[/dim]")
        for audio_path in new_audio:
            song_title = os.path.splitext(os.path.basename(audio_path))[0]
            lrc_path = os.path.join(os.path.dirname(audio_path), f"{song_title}.lrc")
            if not os.path.exists(lrc_path):
                fetch_synced_lyrics(
                    title=song_title,
                    lrc_path=lrc_path,
                    sync_huawei=sync_huawei,
                    transliterate_mode=transliterate,
                    translate_mode=translate_id,
                )
            if os.path.exists(lrc_path):
                source_lines = None
                try:
                    with open(lrc_path, encoding="utf-8") as f:
                        source_lines = f.readlines()
                except Exception:
                    pass
                snapshot = process_transliteration(lrc_path, transliterate)
                if snapshot:
                    source_lines = snapshot
                process_translation(lrc_path, translate_id, source_lines=source_lines)
                if sync_huawei:
                    sync_huawei_lrc(lrc_path)
                if embed_id3 and not audio_path.lower().endswith(".wav"):
                    embed_lyrics_to_audio(audio_path, lrc_path)
            if not os.path.exists(lrc_path):
                console.print(
                    f"[yellow]⚠️ Lirik tidak ditemukan: {song_title[:40]}...[/yellow]"
                )

    if not quiet:
        console.print("\n[bold green]✅ Selesai.[/bold green]")
    return exit_code

