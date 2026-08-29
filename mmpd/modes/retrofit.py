"""
Mode 2: Retrofit Engine — perbaiki file MP3/FLAC lama.

Skenario: User punya koleksi MP3 lama tanpa lirik/cover art. Mode ini akan:
    1. Scan folder untuk file MP3/FLAC
    2. Cari metadata di YouTube (judul → ytsearch) — download thumbnail + subs
    3. Suntik cover art ke file audio (via FFmpeg)
    4. Cari & tulis lirik via LyricsChain (LRCLIB → syncedlyrics)
    5. Apply transliterasi (Romaji/Pinyin/Latin) jika diminta
    6. Apply translation bilingual ke Indonesia jika diminta
    7. Sync ke folder Huawei Musiclrc jika di Termux
"""

from __future__ import annotations

import glob
import os
import re
import shutil
from pathlib import Path

import yt_dlp
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from mmpd.config import is_termux
from mmpd.logger import get_logger
from mmpd.lyrics import fetch_synced_lyrics, process_translation, process_transliteration, sync_huawei_lrc
from mmpd.ui import (
    LYRICS_MODE_CHOICES,
    RETROFIT_TARGET_CHOICES,
    TRANSLITERATE_CHOICES,
    ask_confirm,
    ask_select,
    ask_text,
    console,
    custom_theme,
)
from mmpd.utils.ffmpeg import inject_cover_to_audio
from mmpd.utils.fs import cleanup_temp_files, find_audio_files
from mmpd.ytdlp import build_retrofit_opts

import questionary

_log = get_logger()


def run_retrofit() -> None:
    """Jalankan Mode 2: Retrofit Otomatis."""
    from mmpd.config import get_config

    config = get_config()
    folder = str(config.output_dir)

    console.print(f"\n[bold cyan]🛠️ Mode Perbaikan / Retrofit Otomatis[/bold cyan]")
    console.print(
        "[white]Sistem akan memindai folder Anda, mencari lagu tanpa lirik/cover, "
        "mencarinya di YouTube, lalu menyuntikkannya ke file asli![/white]\n"
    )

    target_folder = ask_text("Masukkan path folder yang ingin diperbaiki:", default=folder)
    if not target_folder or not os.path.exists(target_folder):
        console.print("[bold red]❌ Folder tidak ditemukan![/bold red]")
        return

    # Prompt khusus Termux/Huawei
    sync_huawei = False
    if is_termux():
        sync_huawei = ask_confirm(
            "📱 Aktifkan Sinkronisasi Lirik khusus Huawei/HarmonyOS (Kopi ke folder Music/Musiclrc)?",
            default=False,
        )

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
            selected_bilingual_fmt = ask_select("Pilih Format Lirik Bilingual:", list(format_choices.keys()))
            if selected_bilingual_fmt:
                os.environ["MMPD_BILINGUAL_FORMAT"] = format_choices[selected_bilingual_fmt]

    # === Langkah 0: Bersihkan & rename file LRC lama ===
    fixed_lrc_count = _cleanup_old_lrc_files(target_folder, transliterate, sync_huawei, translate_id)

    # Bersihkan file sampah sisa timeout sebelumnya
    cleanup_temp_files(target_folder, prefix="temp_meta_")

    if fixed_lrc_count > 0:
        console.print(
            f"[bold green]✅ Berhasil memperbaiki penamaan & sinkronisasi "
            f"{fixed_lrc_count} file Lirik lama secara instan![/bold green]"
        )

    # === Kumpulkan file audio ===
    audio_files = find_audio_files(target_folder, recursive=True)
    if not audio_files:
        console.print("[bold yellow]⚠️ Tidak ada file MP3/FLAC yang ditemukan di folder tersebut.[/bold yellow]")
        return

    console.print(f"[bold green]✅ Ditemukan {len(audio_files)} file musik.[/bold green]")

    target_mode = ask_select("🎯 Pilih Target Injeksi / Perbaikan:", RETROFIT_TARGET_CHOICES)
    if target_mode is None:
        return

    force_overwrite_lrc = False
    if target_mode.startswith("✨ 1") or target_mode.startswith("📝 2"):
        force_overwrite_lrc = ask_confirm(
            "⚠️ Hapus & Timpa file lirik (.lrc) lama yang mungkin salah timing?",
            default=False,
        )

    if not ask_confirm("▶️ Mulai eksekusi sekarang?", default=True):
        return

    # === Eksekusi per-file dengan progress bar ===
    with Progress(
        SpinnerColumn(spinner_name="dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="green"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task("[cyan]Memulai Retrofit Engine...", total=len(audio_files))

        for audio_path in audio_files:
            _process_single_audio(
                audio_path=audio_path,
                progress=progress,
                main_task=main_task,
                lyrics_mode=lyrics_mode,
                download_lyrics=download_lyrics,
                target_mode=target_mode,
                force_overwrite_lrc=force_overwrite_lrc,
                transliterate=transliterate,
                translate_id=translate_id,
                sync_huawei=sync_huawei,
            )
            progress.advance(main_task)
            import time
            time.sleep(1)  # D3: jeda 1 detik antar lagu agar tidak rate-limit API

        progress.update(main_task, description="[bold green]✨ Proses Retrofit Selesai!", completed=len(audio_files))


def _cleanup_old_lrc_files(target_folder: str, transliterate: str, sync_huawei: bool, translate_id: bool = False) -> int:
    """Rename file LRC dengan suffix bahasa (mis. song.ja.lrc) ke nama bersih, apply translit & sync."""
    fixed_count = 0
    for lrc_file in glob.glob(os.path.join(target_folder, "**", "*.lrc"), recursive=True):
        parts = lrc_file.rsplit(".", 2)
        if len(parts) == 3 and len(parts[1]) <= 3:
            # Pattern: name.lang.lrc → rename to name.lrc
            new_name = f"{parts[0]}.lrc"
            new_path = os.path.join(os.path.dirname(lrc_file), new_name)
            if os.path.exists(new_path):
                if parts[1] != "id" and os.path.getsize(new_path) > 0:
                    os.remove(lrc_file)
                    continue
                os.remove(new_path)
            shutil.move(lrc_file, new_path)
            orig_lines = None
            try:
                with open(new_path, "r", encoding="utf-8") as f:
                    orig_lines = f.readlines()
            except Exception:
                pass
            process_transliteration(new_path, transliterate)
            process_translation(new_path, translate_id, source_lines=orig_lines)
            if sync_huawei:
                sync_huawei_lrc(new_path)
            fixed_count += 1
        else:
            # Sudah benar — apply transliterasi + terjemahan jika belum bilingual
            orig_lines = None
            try:
                with open(lrc_file, "r", encoding="utf-8") as f:
                    orig_lines = f.readlines()
            except Exception:
                pass
            process_transliteration(lrc_file, transliterate)
            process_translation(lrc_file, translate_id, source_lines=orig_lines)
            if sync_huawei:
                sync_huawei_lrc(lrc_file)
    return fixed_count


def _process_single_audio(
    audio_path: Path,
    progress: Progress,
    main_task,
    lyrics_mode: str,
    download_lyrics: bool,
    target_mode: str,
    force_overwrite_lrc: bool,
    transliterate: str,
    translate_id: bool,
    sync_huawei: bool,
) -> None:
    """Proses satu file audio: ambil metadata YouTube + suntik cover + cari lirik."""
    filename = os.path.basename(audio_path)
    title = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    dir_path = os.path.dirname(audio_path)

    progress.update(main_task, description=f"[cyan]Menyelidiki: [bold white]{title[:20]}...")

    lrc_path = os.path.join(dir_path, f"{title}.lrc")
    temp_outtmpl = os.path.join(dir_path, f"temp_meta_{title}.%(ext)s")

    # Build ydl_opts untuk retrofit (skip download, only metadata + thumbnail + subs)
    ydl_opts = build_retrofit_opts(
        outtmpl=temp_outtmpl,
        lyrics_from_youtube_cc=lyrics_mode.startswith("📺 3"),
    )

    # Cari metadata YouTube (untuk Cover Art) dengan membersihkan judul lagu
    from mmpd.utils.matching import clean_search_query
    is_cover = bool(re.search(r"(?i)\b(cover|翻唱|歌ってみた|커버|คัฟเวอร์)\b", title))
    clean_title_for_yt = clean_search_query(title) or title
    
    if is_cover:
        search_query = f"ytsearch1:{title}"  # Pakai judul asli agar match dengan cover
    else:
        search_query = f"ytsearch1:{clean_title_for_yt} official audio"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([search_query])
    except Exception as e:
        _log.warning("Gagal ambil metadata YouTube untuk '%s...': %s", title[:30], e)

    # Backup lirik lama sebelum overwrite. Kalau fetch gagal, file asli
    # (yang sudah latin) dikembalikan lalu hanya disuntik terjemahan.
    backup_lrc = lrc_path + ".bak"
    if force_overwrite_lrc:
        if os.path.exists(lrc_path):
            try:
                shutil.copy2(lrc_path, backup_lrc)
            except Exception as e:
                _log.warning("Gagal backup LRC %s: %s", title[:30], e)
            os.remove(lrc_path)
        huawei_lrc_path = os.path.join(
            str(Path.home()), "storage", "shared", "Music", "Musiclrc", f"{title}.lrc"
        )
        if os.path.exists(huawei_lrc_path):
            os.remove(huawei_lrc_path)
    else:
        backup_lrc = ""

    # === BLOK 1: Pemrosesan Lirik ===
    if not target_mode.startswith("🖼️ 3"):
        _process_lyrics_for_audio(
            title=title,
            lrc_path=lrc_path,
            dir_path=dir_path,
            lyrics_mode=lyrics_mode,
            progress=progress,
            main_task=main_task,
            transliterate=transliterate,
            translate_id=translate_id,
            sync_huawei=sync_huawei,
            backup_lrc=backup_lrc,
        )

    # === BLOK 2: Pemrosesan Cover Art ===
    if not target_mode.startswith("📝 2"):
        _process_cover_art_for_audio(
            title=title,
            filename=filename,
            audio_path=audio_path,
            dir_path=dir_path,
            ext=ext,
            progress=progress,
            main_task=main_task,
        )

    # Bersihkan sampah sementara
    cleanup_temp_files(dir_path, prefix=f"temp_meta_{title}")


def _process_lyrics_for_audio(
    title: str,
    lrc_path: str,
    dir_path: str,
    lyrics_mode: str,
    progress: Progress,
    main_task,
    transliterate: str,
    translate_id: bool,
    sync_huawei: bool,
    backup_lrc: str = "",
) -> None:
    """Tangani pencarian & penulisan lirik untuk satu audio."""
    # Tangani lirik hasil unduhan YouTube (jika Mode 3)
    if lyrics_mode.startswith("📺 3"):
        for yt_lrc in glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.lrc")):
            if os.path.exists(lrc_path):
                os.remove(lrc_path)
            shutil.move(yt_lrc, lrc_path)

    # Jika lirik belum ada dan pakai Mode 1/2 (Spotify/Spotify+manual)
    huawei_lrc_path = os.path.join(
        str(Path.home()), "storage", "shared", "Music", "Musiclrc", f"{title}.lrc"
    )
    if (lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")) and not os.path.exists(lrc_path):
        if sync_huawei and os.path.exists(huawei_lrc_path):
            shutil.copy2(huawei_lrc_path, lrc_path)
        else:
            query = None
            if lyrics_mode.startswith("✍️ 2"):
                progress.stop()
                query = ask_text(f"📝 Masukkan judul Spotify untuk '{title}':")
                progress.start()
            fetch_synced_lyrics(
                title=title,
                lrc_path=lrc_path,
                sync_huawei=sync_huawei,
                transliterate_mode=transliterate,
                override_query=query,
                translate_mode=translate_id,
            )
    elif os.path.exists(lrc_path):
        # Lirik sudah ada. Jika sudah latin, coba ambil aksara asli
        # HANYA sebagai sumber terjemahan (file tampilan tidak ditimpa).
        source_lines = _peek_original_source_lines(title, lrc_path) if translate_id else None
        process_transliteration(lrc_path, transliterate)
        process_translation(lrc_path, translate_id, source_lines=source_lines)
        if sync_huawei:
            sync_huawei_lrc(lrc_path)

    # Jika fetch gagal tapi ada backup LRC latin, kembalikan lalu suntik terjemahan.
    if not os.path.exists(lrc_path) and backup_lrc and os.path.exists(backup_lrc):
        shutil.move(backup_lrc, lrc_path)
        _log.info("Restore LRC backup (fetch gagal): %s", os.path.basename(lrc_path))
        orig_lines = None
        try:
            with open(lrc_path, "r", encoding="utf-8") as f:
                orig_lines = f.readlines()
        except Exception:
            pass
        process_transliteration(lrc_path, transliterate)
        process_translation(lrc_path, translate_id, source_lines=orig_lines)
        if sync_huawei:
            sync_huawei_lrc(lrc_path)
    elif backup_lrc and os.path.exists(backup_lrc):
        try:
            os.remove(backup_lrc)
        except OSError:
            pass

    # Peringatan jika lirik tidak ditemukan
    if not os.path.exists(lrc_path):
        progress.stop()
        if lyrics_mode.startswith("📺 3"):
            msg = f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {title[:30]}...[/bold yellow]"
        else:
            msg = f"[bold yellow]⚠️ Lirik dilewati: Tidak ditemukan di database lirik untuk {title[:30]}...[/bold yellow]"
        console.print(msg)
        progress.start()



def _peek_original_source_lines(title: str, lrc_path: str):
    """Ambil lirik aksara asli dari database tanpa menimpa file latin yang sudah ada."""
    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            current = f.read()
        from mmpd.lyrics import detect_script
        if detect_script(current) != "latin":
            return current.splitlines(keepends=True)

        from mmpd.lyrics_providers import build_default_chain
        from mmpd.types import TrackInfo
        from mmpd.utils.matching import clean_search_query

        q = clean_search_query(title) or title
        result = build_default_chain(q).search(TrackInfo(title=q))
        if result and result.best_lyrics and detect_script(result.best_lyrics) != "latin":
            _log.info("Sumber asli didapat untuk terjemahan akurat: %s", title[:40])
            return [
                (ln if ln.endswith("\n") else ln + "\n")
                for ln in result.best_lyrics.splitlines()
            ]
    except Exception as e:
        _log.debug("peek original lyrics gagal untuk %s: %s", title[:30], e)
    return None


def _process_cover_art_for_audio(
    title: str,
    filename: str,
    audio_path: Path,
    dir_path: str,
    ext: str,
    progress: Progress,
    main_task,
) -> None:
    """Suntik cover art ke file audio via FFmpeg."""
    temp_cover_glob = (
        glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.webp"))
        + glob.glob(os.path.join(dir_path, f"temp_meta_{title}*.jpg"))
    )
    from mmpd.cover_providers import download_cover_art
    from mmpd.utils.ffmpeg import crop_cover_to_square
    
    temp_api_cover = os.path.join(dir_path, f"api_cover_{title}.jpg")
    cover_path = None
    
    if download_cover_art(title, "", temp_api_cover):
        cover_path = temp_api_cover
    elif temp_cover_glob:
        yt_cover = temp_cover_glob[0]
        temp_crop_cover = os.path.join(dir_path, f"cropped_{title}.jpg")
        if crop_cover_to_square(yt_cover, temp_crop_cover):
            cover_path = temp_crop_cover
        else:
            cover_path = yt_cover
            
    if not cover_path:
        return

    temp_audio = os.path.join(dir_path, f"temp_{filename}")
    progress.update(main_task, description=f"[magenta]Menyuntikkan Cover: [bold white]{title[:20]}...")

    # Pakai helper Fase 2.2 (subprocess.run, bukan os.system)
    success = inject_cover_to_audio(
        audio_path=str(audio_path),
        cover_path=cover_path,
        output_path=temp_audio,
        audio_format=ext.lstrip("."),  # "mp3" or "flac"
    )

    if success and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
        os.remove(audio_path)
        shutil.move(temp_audio, audio_path)
        _log.info("Cover injected: %s", filename)
