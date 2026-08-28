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
from mmpd.spotify import (
    build_ytsearch_query,
    is_spotify_url,
    parse_spotify_url_safe,
    parse_spotify_url_v2,
    spotipy_available,
)
from mmpd.types import TrackInfo
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
    spotify_targets: list[str] = []  # backward compat untuk display
    spotify_tracks_v2 = None  # List[SpotifyTrack] untuk Fase 2.3 ISRC matching

    if is_spotify_mode:
        # Fase 2.3: coba v2 (dengan ISRC) dulu, fallback ke v1 (string)
        spotify_tracks_v2 = _gather_spotify_tracks_v2()
        if not spotify_tracks_v2:
            return
        spotify_targets = [t.to_ytsearch_query() for t in spotify_tracks_v2]
        max_songs = _ask_max_songs(spotify_tracks_v2, "dari playlist")
        if max_songs:
            spotify_tracks_v2 = spotify_tracks_v2[:max_songs]
            spotify_targets = spotify_targets[:max_songs]
        final_target = None
        display_target = f"Spotify Playlist/Track ({len(spotify_tracks_v2)} lagu)"
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

    # === Fase 2.3: Prompt concurrent downloads untuk Spotify playlist ===
    use_concurrent = False
    use_isrc_matching = False
    if is_spotify_mode and len(spotify_tracks_v2 or []) > 1:
        console.print()
        use_concurrent = ask_confirm(
            f"⚡ Aktifkan download paralel untuk {len(spotify_tracks_v2)} lagu Spotify? "
            "(3x lebih cepat, tapi rawan rate limit YouTube)",
            default=False,
        )

        # ISRC matching kalau spotipy available + ada ISRC
        has_isrc = any(t.isrc for t in (spotify_tracks_v2 or []))
        if has_isrc:
            use_isrc_matching = ask_confirm(
                "🎯 Aktifkan ISRC matching (akurasi 99%+ via Spotify ISRC)? "
                "(lebih akurat tapi lebih lambat, ambil 3 kandidat YouTube per lagu)",
                default=True,
            )

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
        if translate_id:
            format_choices = {
                "🔤 1. Gabung 1 baris (Teraman, Default)": "gabung",
                "⏱️ 2. Pisah 2 baris (Micro-offset) - Terbaik untuk Poweramp": "pisah",
                "📁 3. File terpisah (.id.lrc)": "id_only"
            }
            selected_fmt = ask_select("Pilih Format Lirik Bilingual:", list(format_choices.keys()))
            if selected_fmt:
                os.environ["MMPD_BILINGUAL_FORMAT"] = format_choices[selected_fmt]

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
        use_concurrent=use_concurrent,
        use_isrc_matching=use_isrc_matching,
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
                    if use_isrc_matching and spotify_tracks_v2:
                        _download_spotify_with_isrc(
                            ydl=ydl,
                            tracks=spotify_tracks_v2,
                            use_concurrent=use_concurrent,
                            progress=progress,
                            main_task=main_task,
                        )
                    elif use_concurrent and spotify_tracks_v2:
                        _download_spotify_concurrent(
                            ydl_opts=ydl_opts,
                            tracks=spotify_tracks_v2,
                            progress=progress,
                            main_task=main_task,
                        )
                    else:
                        # Sequential fallback — Fix: filter instrumental + fallback
                        for track in spotify_targets:
                            try:
                                search_q = build_ytsearch_query(track, limit=1)
                                ydl.download([search_q])
                            except Exception as e:
                                # Fallback: coba tanpa filter (kalau filter terlalu ketat)
                                try:
                                    from mmpd.utils.matching import clean_search_query
                                    fallback_q = f"ytsearch1:{clean_search_query(track)}"
                                    ydl.download([fallback_q])
                                except Exception as e2:
                                    console.print(f"[dim red]❌ Gagal unduh '{track[:40]}...': {e2}[/dim red]")
                                    _log.error("Spotify track failed '%s': %s (fallback: %s)", track, e, e2)
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
    use_concurrent: bool = False,
    use_isrc_matching: bool = False,
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
    # Fase 2.3: tampilkan status concurrent & ISRC matching
    if use_concurrent:
        table.add_row("⚡ Concurrent", "[green]✅ Aktif (3 worker)[/green]")
    if use_isrc_matching:
        table.add_row("🎯 ISRC Matching", "[green]✅ Aktif (akurasi 99%+)[/green]")
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


# ============================================================================
# Fase 2.3: Helper baru untuk ISRC matching + concurrent downloads
# ============================================================================

def _gather_spotify_tracks_v2():
    """
    Fase 2.3: Prompt URL Spotify, parse dengan v2 (return List[SpotifyTrack]).

    SpotifyTrack punya:
        - title, artist, album
        - isrc (untuk YouTube matching 99%+ akurat)
        - duration_ms (untuk duration verification)
        - spotify_url (untuk debugging)
    """
    url = ask_text("🎵 Masukkan URL Track/Playlist/Album Spotify:")
    if not url or not is_spotify_url(url):
        console.print("[red]⚠️ URL Spotify tidak valid![/red]")
        time.sleep(1)
        return []

    # Tampilkan info spotipy availability
    if spotipy_available():
        console.print("[cyan]🔍 Membaca metadata dari Spotify via official API (spotipy)...[/cyan]")
    else:
        console.print("[cyan]🔍 Membaca metadata dari Spotify via legacy scraping...[/cyan]")
        console.print("[dim]   (untuk ISRC matching, install spotipy + set SPOTIPY_CLIENT_ID/SECRET)[/dim]")

    tracks = parse_spotify_url_v2(url)
    if not tracks:
        try:
            from mmpd.spotify_client import get_spotify_client
            client = get_spotify_client()
            if client.last_error:
                console.print(f"\n[bold red]❌ Gagal mengambil data Spotify![/bold red]")
                console.print(f"[yellow]   {client.last_error}[/yellow]")
                console.print("\n[dim]Solusi:[/dim]")
                if "403" in client.last_error and "Premium" in client.last_error:
                    console.print("[dim]   1. Upgrade Spotify Premium untuk app owner (dapat ISRC)[/dim]")
                    console.print("[dim]   2. Atau gunakan embed scraping (otomatis, tanpa ISRC)[/dim]")
                elif "401" in client.last_error:
                    console.print("[dim]   Cek SPOTIPY_CLIENT_ID dan SPOTIPY_CLIENT_SECRET di ~/.bashrc[/dim]")
                elif "404" in client.last_error:
                    console.print("[dim]   Pastikan URL benar dan playlist tidak private[/dim]")
                console.print("[dim]   3. Atau coba download via YouTube: ketik judul lagu di Mode 1[/dim]")
                console.print()
            else:
                console.print("[red]⚠️ Gagal mengambil data Spotify atau playlist kosong![/red]")
                console.print("[dim]   Coba cek URL atau gunakan Mode 1 (YouTube search)[/dim]")
        except Exception:
            console.print("[red]⚠️ Gagal mengambil data Spotify![/red]")
        time.sleep(2)
        return []

    isrc_count = sum(1 for t in tracks if t.isrc)

    try:
        from mmpd.spotify_client import get_spotify_client
        client = get_spotify_client()
        if client.last_error and "fallback" in client.last_error.lower():
            console.print(f"\n[yellow]⚠️ {client.last_error.split(chr(10))[0]}[/yellow]")
            console.print()
    except Exception:
        pass

    console.print(f"[bold green]✅ Ditemukan {len(tracks)} lagu dari Spotify![/bold green]")
    if isrc_count > 0:
        console.print(f"[dim cyan]   📊 {isrc_count}/{len(tracks)} lagu punya ISRC (siap untuk matching akurat)[/dim cyan]")
    elif tracks:
        console.print(f"[dim yellow]   ⚠️ Tidak ada ISRC (embed scraping fallback) — matching pakai fuzzy title[/dim yellow]")
    return tracks


def _download_spotify_with_isrc(ydl, tracks, use_concurrent: bool, progress, main_task) -> None:
    """
    Fase 2.3: Download Spotify tracks dengan ISRC matching.

    Strategi:
        1. Untuk setiap track, search 3 kandidat YouTube via yt-dlp
        2. Extract ISRC dari metadata YouTube
        3. Match ISRC track == ISRC YouTube → pilih itu
        4. Fallback: fuzzy match judul+artist dengan duration verification
        5. Download video yang dipilih

    Kalau use_concurrent=True, jalankan secara paralel (3 worker).
    """
    from mmpd.isrc_matcher import search_youtube_with_isrc

    console.print(f"[cyan]🎯 ISRC matching aktif untuk {len(tracks)} lagu...[/cyan]")
    progress.update(main_task, total=len(tracks), completed=0)

    def _process_single_track(track):
        """Worker function: match + download satu track."""
        try:
            track_info = track.to_track_info()
            duration_sec = track.duration_ms / 1000.0 if track.duration_ms else None

            # Search via ISRC matcher (return YouTubeMatchResult)
            match = search_youtube_with_isrc(
                track=track_info,
                max_candidates=3,
                target_duration_sec=duration_sec,
            )

            if not match:
                return False, "No YouTube match found", {}

            # Download video yang dipilih
            try:
                ydl.download([match.video_url])
                return True, None, {
                    "video_url": match.video_url,
                    "video_title": match.video_title,
                    "isrc_match": match.isrc_match,
                    "fuzzy_score": match.fuzzy_score,
                }
            except Exception as e:
                return False, str(e), {"video_url": match.video_url}

        except Exception as e:
            return False, str(e), {}

    if use_concurrent:
        # === Concurrent ISRC matching + download ===
        from mmpd.concurrent import run_concurrent

        track_ids = [t.spotify_url or f"{t.artist} {t.title}" for t in tracks]

        def _progress_callback(completed: int, total: int, current: str):
            progress.update(
                main_task,
                completed=completed,
                description=f"[cyan]🎯 ISRC matching: [bold white]{completed}/{total}",
            )

        results = run_concurrent(
            items=track_ids,
            worker_fn=lambda item_id: _process_single_track(_find_track_by_id(tracks, item_id)),
            max_workers=3,
            description="ISRC matching",
            progress_callback=_progress_callback,
        )

        # Print summary
        success_count = sum(1 for r in results if r.success)
        isrc_match_count = sum(1 for r in results if r.extra.get("isrc_match"))
        console.print(
            f"[bold green]✅ {success_count}/{len(results)} berhasil "
            f"({isrc_match_count} via ISRC, {success_count - isrc_match_count} via fuzzy)[/bold green]"
        )
    else:
        # === Sequential ISRC matching ===
        for idx, track in enumerate(tracks, 1):
            progress.update(
                main_task,
                completed=idx - 1,
                description=f"[cyan]🎯 ISRC matching {idx}/{len(tracks)}: {track.title[:30]}...",
            )
            success, error, extra = _process_single_track(track)
            if not success:
                console.print(f"[dim red]❌ '{track.title[:40]}': {error}[/dim red]")
                _log.error("ISRC matching failed for '%s': %s", track.title, error)
            elif extra.get("isrc_match"):
                console.print(
                    f"[dim green]   ✅ ISRC MATCH: {track.title[:40]} → "
                    f"{extra.get('video_title', '')[:30]}[/dim green]"
                )
            progress.update(main_task, completed=idx)


def _find_track_by_id(tracks, item_id: str):
    """Helper: cari track berdasarkan spotify_url atau 'Artist Title'."""
    for t in tracks:
        if t.spotify_url == item_id:
            return t
        if f"{t.artist} {t.title}" == item_id:
            return t
    return tracks[0] if tracks else None


def _download_spotify_concurrent(ydl_opts: dict, tracks, progress, main_task) -> None:
    """
    Fase 2.3: Download Spotify tracks secara paralel (tanpa ISRC matching).

    Pakai simple ytsearch1:{query} seperti Fase 1, tapi dengan 3 worker paralel.
    """
    import yt_dlp
    from mmpd.concurrent import run_concurrent

    console.print(f"[cyan]⚡ Download paralel {len(tracks)} lagu (3 worker)...[/cyan]")
    progress.update(main_task, total=len(tracks), completed=0)

    def _worker(item_query: str):
        """Download satu track via ytsearch1 dengan filter instrumental."""
        try:
            search_q = build_ytsearch_query(item_query, limit=1)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_q])
            return True, None, {}
        except Exception as e:
            # Fallback: coba tanpa filter exclusion
            try:
                from mmpd.utils.matching import clean_search_query
                fallback_q = f"ytsearch1:{clean_search_query(item_query)}"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([fallback_q])
                return True, None, {"used_fallback": True}
            except Exception as e2:
                return False, str(e2), {}

    queries = [t.to_ytsearch_query() for t in tracks]

    def _progress_callback(completed: int, total: int, current: str):
        progress.update(
            main_task,
            completed=completed,
            description=f"[cyan]⚡ Concurrent: [bold white]{completed}/{total}",
        )

    results = run_concurrent(
        items=queries,
        worker_fn=_worker,
        max_workers=3,
        description="Spotify concurrent download",
        progress_callback=_progress_callback,
    )

    success_count = sum(1 for r in results if r.success)
    console.print(
        f"[bold green]✅ {success_count}/{len(results)} berhasil diunduh[/bold green]"
    )
