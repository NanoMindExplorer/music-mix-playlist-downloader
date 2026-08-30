"""
Argparse CLI untuk mmpd — non-interaktif + backward compatible.

Subcommand:
    mmpd                                # menu interaktif (perilaku lama)
    mmpd download URL [opsi]            # download non-interaktif
    mmpd retrofit --dir DIR [opsi]      # perbaiki koleksi lama
    mmpd lyrics --dir DIR [opsi]        # suntik terjemahan ke .lrc existing
    mmpd organize --dir DIR [--dry-run] # rapikan audio + LRC
    mmpd cache [--stats|--clear]        # kelola cache SQLite
    mmpd config [--create-example]      # kelola config.toml
    mmpd doctor                         # diagnostik
    mmpd self-update                    # update non-destruktif
    mmpd completion bash|zsh|fish       # cetak skrip tab-completion
    mmpd --version                      # versi
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional, Sequence

# ============================================================================
# Mapping CLI ↔ nilai internal lama (string pilihan menu)
# Kontrak: jangan ubah VALUE tanpa audit startswith() di modes/*.
# ============================================================================

_LYRICS_MODE_MAP = {
    "musixmatch": "🎧 1",
    "chain": "🎧 1",
    "manual": "✍️ 2",
    "youtube-cc": "📺 3",
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
VALID_COMPLETION_SHELLS = ("bash", "zsh", "fish")


def _bool_optional(parser: Any, *flags: str, **kwargs: Any):
    """--flag / --no-flag dengan default None (artinya: pakai config.toml)."""
    kwargs.setdefault("default", None)
    return parser.add_argument(*flags, action=argparse.BooleanOptionalAction, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mmpd",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Music Mix & Playlist Downloader — download YouTube/Spotify/SoundCloud "
            "dengan Lyrics Engine (transliterasi + terjemahan + LRC karaoke)."
        ),
        epilog=(
            "Tanpa subcommand → menu interaktif (perilaku lama, backward compatible).\n"
            "Flag --no-* memaksa OFF meski config.toml mengaktifkan opsi yang sama.\n"
            "Contoh: mmpd retrofit --dir ~/storage/downloads/YT_Downloader --lyrics-only --translate"
        ),
    )
    parser.add_argument(
        "--version", "-V", action="store_true",
        help="cetak versi lalu keluar",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="kurangi output ke terminal (error tetap tampil)",
    )

    sub = parser.add_subparsers(dest="command")

    p_dl = sub.add_parser(
        "download",
        help="download lagu/playlist (YouTube/SoundCloud/Spotify URL) non-interaktif",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    _bool_optional(
        p_dl, "--translate",
        help="terjemahkan lirik ke Bahasa Indonesia (default: dari config.toml)",
    )
    p_dl.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default=None,
                      help="aksara asing → Latin (default: dari config.toml, fallback off)")
    p_dl.add_argument("--lrc-format", choices=list(VALID_LRC_FORMATS), default=None,
                      help="format LRC bilingual (default: dari config.toml, fallback gabung)")
    _bool_optional(
        p_dl, "--sync-huawei",
        help="copy .lrc ke folder Music/Musiclrc (Termux/Huawei)",
    )
    p_dl.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")
    p_dl.add_argument("--no-dedup", action="store_true",
                      help="matikan anti-duplikat (archive.txt)")
    p_dl.add_argument(
        "--isrc", action=argparse.BooleanOptionalAction, default=True,
        help="untuk URL Spotify: pakai ISRC matching (default: ya, fallback fuzzy)",
    )
    p_dl.add_argument(
        "--concurrent", action="store_true",
        help="untuk playlist Spotify: unduh paralel (lebih cepat, rawan rate-limit)",
    )

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
    _bool_optional(
        p_rf, "--translate",
        help="suntik terjemahan bilingual (default: dari config.toml)",
    )
    p_rf.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default=None,
                      help="aksara asing → Latin (default: dari config.toml, fallback off)")
    p_rf.add_argument("--lrc-format", choices=list(VALID_LRC_FORMATS), default=None,
                      help="format LRC bilingual (default: dari config.toml, fallback gabung)")
    p_rf.add_argument("--overwrite", action="store_true",
                      help="IZINKAN timpa .lrc lama dengan fetch baru (default: TIDAK, "
                           "lirik lama hanya ditambah terjemahan; backup .bak dibuat)")
    p_rf.add_argument("--fetch-missing", action="store_true", default=True,
                      help="cari lirik untuk file yang belum punya .lrc (default: ya)")
    p_rf.add_argument("--no-fetch", dest="fetch_missing", action="store_false",
                      help="jangan fetch lirik baru — hanya proses .lrc yang sudah ada")
    p_rf.add_argument("--workers", type=int, default=None, metavar="N",
                      help="jumlah worker paralel 1-4 (default: dari config / 1)")
    _bool_optional(
        p_rf, "--sync-huawei",
        help="copy .lrc ke folder Music/Musiclrc (Termux/Huawei)",
    )
    p_rf.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")

    p_ly = sub.add_parser(
        "lyrics",
        help="proses file .lrc di folder (default: suntik terjemahan saja)",
    )
    p_ly.add_argument("--dir", "-d", required=True, help="folder berisi file .lrc")
    p_ly.add_argument("--translate-only", action="store_true", default=True,
                      help="suntik terjemahan TANPA fetch ulang (default: ya)")
    p_ly.add_argument("--transliterate", choices=list(_TRANSLITERATE_MAP), default=None,
                      help="aksara asing → Latin (default: dari config.toml, fallback off)")
    p_ly.add_argument("--lrc-format", choices=list(VALID_LRC_FORMATS), default=None,
                      help="format LRC bilingual (default: dari config.toml, fallback gabung)")
    _bool_optional(
        p_ly, "--sync-huawei",
        help="copy .lrc ke folder Music/Musiclrc",
    )
    p_ly.add_argument("--no-embed", action="store_true",
                      help="jangan tanam lirik USLT/SYLT ke file audio")

    p_org = sub.add_parser(
        "organize",
        help="rapikan file audio + .lrc: rename match & pindah ke Music/Musiclrc",
    )
    p_org.add_argument("--dir", "-d", required=True, help="folder yang ingin dirapikan")
    p_org.add_argument("--no-recursive", action="store_true",
                       help="scan hanya root folder (default: rekursif)")
    p_org.add_argument("--dry-run", action="store_true",
                       help="preview rencana tanpa memindahkan file apa pun")

    p_cache = sub.add_parser("cache", help="kelola cache SQLite (lirik + terjemahan)")
    p_cache.add_argument("--stats", action="store_true", help="tampilkan statistik")
    p_cache.add_argument("--clear", action="store_true",
                         help="hapus SEMUA cache (lirik + terjemahan + negatif)")
    p_cache.add_argument("--clear-expired", action="store_true",
                         help="hapus hanya entry expired")
    p_cache.add_argument("--clear-negative", action="store_true",
                         help="hapus hanya negative cache (paksa cari ulang lirik)")

    p_cfg = sub.add_parser("config", help="kelola config.toml")
    p_cfg.add_argument("--create-example", action="store_true",
                       help="tulis contoh config.toml kalau belum ada")
    p_cfg.add_argument("--path", action="store_true", help="cetak path config.toml")
    p_cfg.add_argument("--credentials-path", action="store_true",
                       help="cetak path credentials.toml (0600)")

    sub.add_parser("doctor", help="diagnostik dependency, network, storage")
    p_up = sub.add_parser("self-update", help="update mmpd non-destruktif (git pull + pip install -U -e .)")
    p_up.add_argument("--no-pull", action="store_true",
                      help="skip git pull (hanya reinstall dependencies)")

    p_comp = sub.add_parser("completion", help="cetak skrip tab-completion untuk shell")
    p_comp.add_argument(
        "shell",
        nargs="?",
        choices=list(VALID_COMPLETION_SHELLS),
        default="bash",
        help="shell target (default: bash)",
    )

    return parser


def _lyrics_defaults() -> dict:
    from mmpd.config_loader import get_lyrics_settings
    return get_lyrics_settings()


def _resolve_bool(flag: Optional[bool], config_value: bool) -> bool:
    return config_value if flag is None else bool(flag)


def _resolve_transliterate(raw: Optional[str]) -> str:
    key = raw or str(_lyrics_defaults().get("transliterate") or "off")
    if key not in _TRANSLITERATE_MAP:
        key = "off"
    return _TRANSLITERATE_MAP[key]


def _resolve_lrc_format(raw: Optional[str]) -> str:
    value = raw or str(_lyrics_defaults().get("bilingual_format") or "gabung")
    return value if value in VALID_LRC_FORMATS else "gabung"


def _apply_lrc_format(raw: Optional[str]) -> str:
    fmt = _resolve_lrc_format(raw)
    os.environ["MMPD_BILINGUAL_FORMAT"] = fmt
    return fmt


def _cmd_download(args) -> int:
    from mmpd.config_loader import get_output_dir_from_config
    from mmpd.ui import console
    from mmpd.utils.ffmpeg import check_ffmpeg_available

    if not check_ffmpeg_available():
        console.print(
            "[bold red]❌ FFmpeg tidak ditemukan di PATH.[/bold red]\n"
            "[dim]Install dulu: pkg install ffmpeg  (Termux) / apt install ffmpeg  (Linux)[/dim]"
        )
        return 1

    lyrics_mode = _LYRICS_MODE_MAP[args.lyrics]
    if lyrics_mode == "✍️ 2":
        console.print(
            "[bold red]❌ Mode lirik 'manual' butuh prompt interaktif per lagu.[/bold red]\n"
            "Gunakan --lyrics musixmatch atau youtube-cc untuk CLI non-interaktif."
        )
        return 2

    lyrics_cfg = _lyrics_defaults()
    transliterate = _resolve_transliterate(args.transliterate)
    translate_id = _resolve_bool(args.translate, bool(lyrics_cfg.get("translate", False)))
    sync_huawei = _resolve_bool(args.sync_huawei, bool(lyrics_cfg.get("sync_huawei", False)))
    embed_id3 = (not args.no_embed) and bool(lyrics_cfg.get("embed_id3", True))
    _apply_lrc_format(args.lrc_format)

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
        translate_id=translate_id,
        sync_huawei=sync_huawei,
        embed_id3=embed_id3,
        anti_duplicate=not args.no_dedup,
        use_isrc=bool(args.isrc),
        use_concurrent=bool(args.concurrent),
        quiet=bool(getattr(args, "quiet", False)),
    )


def _cmd_retrofit(args) -> int:
    from mmpd.config_loader import get_workers
    from mmpd.modes.retrofit import run_retrofit_noninteractive

    target = "full"
    if args.lyrics_only:
        target = "lyrics"
    elif args.covers_only:
        target = "covers"

    lyrics_cfg = _lyrics_defaults()
    _apply_lrc_format(args.lrc_format)
    workers = args.workers if args.workers is not None else get_workers(default=1)
    translate_id = _resolve_bool(args.translate, bool(lyrics_cfg.get("translate", False)))
    sync_huawei = _resolve_bool(args.sync_huawei, bool(lyrics_cfg.get("sync_huawei", False)))
    embed_id3 = (not args.no_embed) and bool(lyrics_cfg.get("embed_id3", True))

    return run_retrofit_noninteractive(
        folder=args.dir,
        target=target,
        translate_id=translate_id,
        transliterate=_resolve_transliterate(args.transliterate),
        overwrite_lrc=args.overwrite,
        fetch_missing=args.fetch_missing,
        workers=workers,
        sync_huawei=sync_huawei,
        embed_id3=embed_id3,
    )


def _cmd_lyrics(args) -> int:
    from mmpd.modes.retrofit import run_translate_only

    lyrics_cfg = _lyrics_defaults()
    _apply_lrc_format(args.lrc_format)
    processed = run_translate_only(
        folder=args.dir,
        transliterate=_resolve_transliterate(args.transliterate),
        sync_huawei=_resolve_bool(args.sync_huawei, bool(lyrics_cfg.get("sync_huawei", False))),
        embed_id3=(not args.no_embed) and bool(lyrics_cfg.get("embed_id3", True)),
    )
    # run_translate_only mengembalikan JUMLAH file, bukan exit code.
    return 0 if int(processed or 0) >= 0 else 1


def _cmd_organize(args) -> int:
    from mmpd.modes.organizer import run_organizer_noninteractive
    return run_organizer_noninteractive(
        folder=args.dir,
        recursive=not args.no_recursive,
        dry_run=args.dry_run,
    )


def _cmd_cache(args) -> int:
    from mmpd import cache as cache_mod
    from mmpd.ui import console

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
    from mmpd.config import get_config
    from mmpd.config_loader import create_example_config, load_config
    from mmpd.ui import console

    if args.create_example:
        path = create_example_config()
        console.print(f"[bold green]✅ Contoh config:[/bold green] {path}")
        return 0
    if args.path:
        console.print(str(get_config().config_file))
        return 0
    if getattr(args, "credentials_path", False):
        console.print(str(get_config().config_file.parent / "credentials.toml"))
        return 0
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


def _cmd_completion(args) -> int:
    from mmpd.completions import render_completion
    text = render_completion(args.shell)
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point CLI. Return exit code (int)."""
    argv = list(sys.argv[1:] if argv is None else argv)

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

    try:
        from mmpd.config_loader import load_config
        load_config()
    except Exception:
        pass

    if args.command == "download":
        return _cmd_download(args)
    if args.command == "retrofit":
        return _cmd_retrofit(args)
    if args.command == "lyrics":
        return _cmd_lyrics(args)
    if args.command == "organize":
        return _cmd_organize(args)
    if args.command == "cache":
        return _cmd_cache(args)
    if args.command == "config":
        return _cmd_config(args)
    if args.command == "doctor":
        from mmpd.doctor import run_doctor
        return run_doctor()
    if args.command == "self-update":
        return _cmd_self_update(args)
    if args.command == "completion":
        return _cmd_completion(args)

    from mmpd.modes.download import run_cli
    try:
        run_cli()
        return 0
    except KeyboardInterrupt:
        print("\n\nAplikasi dihentikan secara paksa (Ctrl+C).")
        return 130


if __name__ == "__main__":
    sys.exit(main())
