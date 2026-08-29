"""
Spotify download helpers — ISRC matching + concurrent (Fase A).

Dipecah dari download.py supaya:
- Logika Spotify (metadata v2, ISRC matching, concurrent 3 worker) terpisah
  dari UI menu interaktif
- Bisa di-test terpisah tanpa mock seluruh menu
"""

from __future__ import annotations

import time

import yt_dlp

from mmpd.logger import get_logger
from mmpd.spotify import (
    build_ytsearch_query,
    is_spotify_url,
    parse_spotify_url_v2,
    spotipy_available,
)
from mmpd.ui import ask_text, console

_log = get_logger()

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
                console.print("\n[bold red]❌ Gagal mengambil data Spotify![/bold red]")
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
        console.print("[dim yellow]   ⚠️ Tidak ada ISRC (embed scraping fallback) — matching pakai fuzzy title[/dim yellow]")
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
        except Exception:
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
