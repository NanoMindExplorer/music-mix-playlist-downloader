"""
Argparse CLI untuk mmpd (Fase C) — non-interaktif + backward compatible.

Subcommand:
    mmpd                                # menu interaktif (perilaku lama)
    mmpd download URL [opsi]            # download non-interaktif
    mmpd retrofit --dir DIR [opsi]      # perbaiki koleksi lama
    mmpd lyrics --dir DIR [opsi]        # suntik terjemahan ke .lrc existing
    mmpd cache [--stats|--clear]        # kelola cache SQLite
    mmpd config [--create-example]      # kelola config.toml
    mmpd doctor                         # diagnostik
    mmpd self-update                    # update non-destruktif
    mmpd --version                      # versi

Contoh pemakaian nyata (koleksi 79 lagu di Termux):
    mmpd retrofit --dir ~/storage/downloads/YT_Downloader \
        --lyrics-only --translate --lrc-format pisah
    mmpd download "https://youtube.com/..." --format flac --lyrics musixmatch --translate
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence

# ============================================================================
# Mapping CLI ↔ nilai internal lama (string pilihan menu)
# ============================================================================

_LYRICS_MODE_MAP = {
    "musixmatch": "🎧 1",      # LyricsChain (Musixmatch/LRCLIB/NetEase)
    "chain": "🎧 1",
    "manual": "✍️ 2",          # input judul manual (hanya mode interaktif)
    "youtube-cc": "📺 3",      # YouTube closed captions
    "cc": "📺 3",
    "off": "❌ 4",
    "none": "❌ 4",
}

_TRANSLITERATE_MAP = {
    "auto": "🤖 5",
    "ja": "🇯🇵 2",
    "zh": "🇨🇳 3",
    "yue": "🇭🇰 4",
    "off": "❌ 1",
}

_FORMAT_MAP = {
    "mp3": ("mp3", "320"),
    "flac": ("flac", None),
    "wav": ("wav", None),
    "best": ("best", None),
}

VALID_LRC_FORMATS = ("gabung", "pisah", "id_only")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mmpd",
        description=(
            "Music Mix & Playlist Downloader — download YouTube/Spotify/SoundCloud "
            "dengan Lyrics Engine (transliterasi + terjemahan + LRC karaoke)."
        ),
        epilog=(
            "Tanpa subcommand → menu interaktif (perilaku lama, backward compatible).\n"
            "Contoh: mmpd retrofit --dir ~/storage/downloads/YT_Downloader --lyrics-only --translate"
        ),
    )
    parser.add_argument(
        "--version", "-V", action="store_true",
        help="cetak versi lalu keluar",
    )

    sub = parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------
    p_dl = sub.add_parser(
        "download",
        help="download lagu/playlist (YouTube/SoundCloud/Spotify URL) non-interaktif",
    )
    p_dl.add_argument("url", help="URL YouTube/SoundCloud/Spotify atau judul lagu")
    p_dl.add_argument("--format", "-f", choices=list(_FORMAT_MAP), default="mp3",
                      help="format audio (default: mp3 320kbps)")
    p_dl.add_argument("--output", "-o", default=None,
                      help="folder output (default: dari config.toml / AppConfig)")
    p_dl.add_argument("--max", type=int, default=None, metavar="N",
                      help="batasi jumlah lagu (playlist/pencarian)")
    p_dl.add_argument("--lyrics", choices=list(_LYRICS_MODE_MAP), default="musixmatch",
                      help="mesin lirik (default: musixmatch/chain)")
    p_dl.add_argument("--translate", action="store_true",
                      help="terjemahkan lirik ke Bahasa Indonesia (bilingual)")
    p_dl.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default="off",
                      help="aksara asing → Latin (default: off)")
    p_dl.add_argument("--lrc-format", choices=list(VALID_LRC_FORMATS), default="gabung",
                      help="format LRC bilingual (default: gabung)")
    p_dl.add_argument("--sync-huawei", action="store_true",
                      help="copy .lrc ke folder Music/Musiclrc (Termux/Huawei)")
    p_dl.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")
    p_dl.add_argument("--no-dedup", action="store_true",
                      help="matikan anti-duplikat (archive.txt)")

    # ------------------------------------------------------------------
    # retrofit
    # ------------------------------------------------------------------
    p_rf = sub.add_parser(
        "retrofit",
        help="perbaiki koleksi lama: suntik lirik/cover/terjemahan ke file existing",
    )
    p_rf.add_argument("--dir", "-d", required=True,
                      help="folder koleksi musik (scan rekursif)")
    group = p_rf.add_mutually_exclusive_group()
    group.add_argument("--lyrics-only", action="store_true",
                       help="hanya proses lirik (JANGAN sentuh cover art)")
    group.add_argument("--covers-only", action="store_true",
                       help="hanya suntik cover art (JANGAN sentuh lirik)")
    p_rf.add_argument("--translate", action="store_true",
                      help="suntik terjemahan bilingual")
    p_rf.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default="off",
                      help="aksara asing → Latin (default: off — aman)")
    p_rf.add_argument("--lrc-format", choices=list(VALID_LRC_FORMATS), default="gabung",
                      help="format LRC bilingual (default: gabung)")
    p_rf.add_argument("--overwrite", action="store_true",
                      help="IZINKAN timpa .lrc lama dengan fetch baru (default: TIDAK, "
                           "lirik lama hanya ditambah terjemahan; backup .bak dibuat)")
    p_rf.add_argument("--fetch-missing", action="store_true", default=True,
                      help="cari lirik untuk file yang belum punya .lrc (default: ya)")
    p_rf.add_argument("--no-fetch", dest="fetch_missing", action="store_false",
                      help="jangan fetch lirik baru — hanya proses .lrc yang sudah ada")
    p_rf.add_argument("--workers", type=int, default=None, metavar="N",
                      help="jumlah worker paralel 1-4 (default: dari config / 1)")
    p_rf.add_argument("--sync-huawei", action="store_true",
                      help="copy .lrc ke folder Music/Musiclrc (Termux/Huawei)")
    p_rf.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")

    # ------------------------------------------------------------------
    # lyrics (alias ringkas translate-only)
    # ------------------------------------------------------------------
    p_ly = sub.add_parser(
        "lyrics",
        help="proses file .lrc di folder (default: suntik terjemahan saja)",
    )
    p_ly.add_argument("--dir", "-d", required=True, help="folder berisi file .lrc")
    p_ly.add_argument("--translate-only", action="store_true", default=True,
                      help="suntik terjemahan TANPA fetch ulang (default: ya)")
    p_ly.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default="off",
                      help="aksara asing → Latin (default: off)")
    p_ly.add_argument("--sync-huawei", action="store_true",
                      help="copy .lrc ke folder Music/Musiclrc")
    p_ly.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")

    # ------------------------------------------------------------------
    # cache
    # ------------------------------------------------------------------
    p_cache = sub.add_parser("cache", help="kelola cache SQLite (lirik + terjemahan)")
    p_cache.add_argument("--stats", action="store_true", help="tampilkan statistik")
    p_cache.add_argument("--clear", action="store_true",
                         help="hapus SEMUA cache (lirik + terjemahan + negatif)")
    p_cache.add_argument("--clear-expired", action="store_true",
                         help="hapus hanya entry expired")
    p_cache.add_argument("--clear-negative", action="store_true",
                         help="hapus hanya negative cache (paksa cari ulang lirik)")

    # ------------------------------------------------------------------
    # config
    # ------------------------------------------------------------------
    p_cfg = sub.add_parser("config", help="kelola config.toml")
    p_cfg.add_argument("--create-example", action="store_true",
                       help="tulis contoh config.toml kalau belum ada")
    p_cfg.add_argument("--path", action="store_true", help="cetak path config.toml")

    # ------------------------------------------------------------------
    # doctor & self-update
    # ------------------------------------------------------------------
    sub.add_parser("doctor", help="diagnostik dependency, network, storage")
    p_up = sub.add_parser("self-update", help="update mmpd non-destruktif (git pull + pip install -U -e .)")
    p_up.add_argument("--no-pull", action="store_true",
                      help="skip git pull (hanya reinstall dependencies)")

    return parser


# ============================================================================
# Runner subcommand
# ============================================================================

def _cmd_download(args) -> int:
    from mmpd.ui import console
    from mmpd.config_loader import get_output_dir_from_config

    lyrics_mode = _LYRICS_MODE_MAP[args.lyrics]
    if lyrics_mode == "✍️ 2":
        console.print(
            "[bold red]❌ Mode lirik 'manual' butuh prompt interaktif per lagu.[/bold red]\n"
            "Gunakan --lyrics musixmatch atau youtube-cc untuk CLI non-interaktif."
        )
        return 2

    transliterate = _TRANSLITERATE_MAP[args.transliterate]
    os.environ["MMPD_BILINGUAL_FORMAT"] = args.lrc_format

    output_dir = args.output or get_output_dir_from_config()
    codec, quality = _FORMAT_MAP[args.format]

    from mmpd.modes.download import run_download_noninteractive
    return run_download_noninteractive(
        url=args.url,
        output_dir=output_dir,
        codec=codec,
        quality=quality,
        max_songs=args.max,
        lyrics_mode=lyrics_mode,
        transliterate=transliterate,
        translate_id=args.translate,
        sync_huawei=args.sync_huawei,
        embed_id3=not args.no_embed,
        anti_duplicate=not args.no_dedup,
    )


def _cmd_retrofit(args) -> int:
    from mmpd.modes.retrofit import run_retrofit_noninteractive
    from mmpd.config_loader import get_workers

    target = "full"
    if args.lyrics_only:
        target = "lyrics"
    elif args.covers_only:
        target = "covers"

    os.environ["MMPD_BILINGUAL_FORMAT"] = args.lrc_format
    workers = args.workers if args.workers is not None else get_workers(default=1)

    return run_retrofit_noninteractive(
        folder=args.dir,
        target=target,
        translate_id=args.translate,
        transliterate=_TRANSLITERATE_MAP[args.transliterate],
        overwrite_lrc=args.overwrite,
        fetch_missing=args.fetch_missing,
        workers=workers,
        sync_huawei=args.sync_huawei,
        embed_id3=not args.no_embed,
    )


def _cmd_lyrics(args) -> int:
    from mmpd.modes.retrofit import run_translate_only
    return run_translate_only(
        folder=args.dir,
        transliterate=_TRANSLITERATE_MAP[args.transliterate],
        sync_huawei=args.sync_huawei,
        embed_id3=not args.no_embed,
    ) or 0


def _cmd_cache(args) -> int:
    from mmpd.ui import console
    from mmpd import cache as cache_mod

    if args.clear:
        cache_mod.clear_all_cache()
        console.print("[bold green]✅ Semua cache dihapus.[/bold green]")
        return 0
    if args.clear_expired:
        n = cache_mod.clear_expired_entries()
        console.print(f"[bold green]✅ {n} entry expired dihapus.[/bold green]")
        return 0
    if args.clear_negative:
        n = cache_mod.clear_negative_cache()
        console.print(f"[bold green]✅ {n} entry negative cache dihapus.[/bold green]")
        return 0
    # default: stats
    stats = cache_mod.get_cache_stats()
    console.print("\n[bold cyan]📊 Statistik Cache mmpd[/bold cyan]")
    console.print(f"  Terjemahan    : {stats.get('translation_count', 0)} entry")
    console.print(f"  Lirik         : {stats.get('lyrics_count', 0)} entry")
    console.print(f"  Negative      : {stats.get('negative_count', 0)} entry (lirik tidak ditemukan)")
    size = stats.get("db_size_bytes", 0)
    console.print(f"  Ukuran DB     : {size / 1024:.1f} KB")
    console.print(f"  Lokasi        : {stats.get('db_path', '-')}\n")
    return 0


def _cmd_config(args) -> int:
    from mmpd.ui import console
    from mmpd.config import get_config
    from mmpd.config_loader import create_example_config, load_config

    if args.create_example:
        path = create_example_config()
        console.print(f"[bold green]✅ Contoh config:[/bold green] {path}")
        return 0
    if args.path:
        console.print(str(get_config().config_file))
        return 0
    # default: tampilkan config aktif
    cfg = load_config()
    console.print(f"\n[bold cyan]⚙️ Config aktif[/bold cyan] ({get_config().config_file})")
    if not cfg:
        console.print("  [dim](kosong — semua setting pakai default)[/dim]")
        console.print("  [dim]buat contoh: mmpd config --create-example[/dim]")
    for section, values in cfg.items():
        console.print(f"  [{section}]")
        for key, value in values.items():
            shown = "•••" if "secret" in key or "token" in key else value
            console.print(f"    {key} = {shown}")
    console.print()
    return 0


def _cmd_self_update(args) -> int:
    from mmpd.self_update import self_update
    return self_update(pull=not args.no_pull)


# ============================================================================
# Entry point
# ============================================================================

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point CLI. Return exit code (int)."""
    argv = list(sys.argv[1:] if argv is None else argv)

    # --version di posisi pertama → cepat (tanpa import berat)
    if argv and argv[0] in ("--version", "-V"):
        from mmpd import __version__
        print(f"mmpd {__version__}")
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from mmpd import __version__
        print(f"mmpd {__version__}")
        return 0

    if args.command == "download":
        return _cmd_download(args)
    if args.command == "retrofit":
        return _cmd_retrofit(args)
    if args.command == "lyrics":
        return _cmd_lyrics(args)
    if args.command == "cache":
        return _cmd_cache(args)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "doctor":
        from mmpd.doctor import run_doctor
        return run_doctor()
    if args.command == "self-update":
        return _cmd_self_update(args)

    # Tanpa subcommand → menu interaktif (backward compatible)
    from mmpd.modes.download import run_cli
    try:
        run_cli()
        return 0
    except KeyboardInterrupt:
        print("\n\nAplikasi dihentikan secara paksa (Ctrl+C).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
