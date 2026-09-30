"""
mmpd.web — Modern Web Browser Interface for Music Mix & Playlist Downloader.
Provides an interactive GUI in any web browser with live progress,
built-in streaming audio player, bilingual karaoke lyrics view, and Discord notifications.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from flask import Flask, Response, abort, jsonify, render_template_string, request, send_file
except ImportError:
    print("\n❌ Modul 'flask' belum terinstal!")
    print("Silakan jalankan: pip install flask --break-system-packages\n")
    sys.exit(1)

from mmpd import __version__
from mmpd.config import get_config, get_output_dir, is_termux, is_windows
from mmpd.config_loader import get_output_dir_from_config
from mmpd.id3_embed import embed_lyrics_to_audio, parse_lrc_to_lines
from mmpd.logger import get_logger
from mmpd.lyrics import (
    fetch_synced_lyrics,
    process_translation,
    process_transliteration,
    sync_huawei_lrc,
)
from mmpd.spotify import build_ytsearch_query, is_spotify_url, parse_spotify_url_safe
from mmpd.web_template import HTML_TEMPLATE
from mmpd.ytdlp import YTDLPLogger, build_download_opts

_log = get_logger()

DEFAULT_DISCORD_WEBHOOK = os.environ.get(
    "MMPD_DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1554679149459935418/eZvLqvhcOypINbSiwCvOQVnKJ0KeV_qP_wmQiHw_wTeWxmmmc6wxjZRktzodeX2Mkldo"
)


# ============================================================================
# Discord Webhook Helper
# ============================================================================

def send_discord_notification(title: str, description: str, fields: Optional[List[Dict[str, Any]]] = None, color: int = 3719160) -> bool:
    """Send rich embed to Discord webhook."""
    webhook_url = DEFAULT_DISCORD_WEBHOOK
    if not webhook_url:
        return False
    
    payload = {
        "embeds": [
            {
                "title": f"🎵 {title}",
                "description": description,
                "color": color,
                "fields": fields or [],
                "footer": {"text": f"MMPD v{__version__} Web Engine"},
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        ]
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "MMPD-Web/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        _log.warning("Gagal kirim notifikasi Discord: %s", e)
        return False


# ============================================================================
# Task Model & Background Task Manager
# ============================================================================

@dataclass
class TaskLog:
    time: str
    msg: str
    level: str = "info"


@dataclass
class JobTask:
    task_id: str
    task_type: str  # "download" | "retrofit"
    status: str     # "queued" | "running" | "completed" | "error" | "cancelled"
    url: str
    options: Dict[str, Any]
    progress: float = 0.0
    stage_message: str = "Menyiapkan tugas..."
    speed: str = "--"
    eta: str = "--"
    downloaded_files: List[str] = field(default_factory=list)
    logs: List[TaskLog] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    _cancel_requested: bool = False

    def add_log(self, msg: str, level: str = "info") -> None:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append(TaskLog(time=now_str, msg=msg, level=level))
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "url": self.url,
            "progress": self.progress,
            "stage_message": self.stage_message,
            "speed": self.speed,
            "eta": self.eta,
            "downloaded_files": [os.path.basename(f) for f in self.downloaded_files],
            "logs": [asdict(l) for l in self.logs],
            "error": self.error,
            "created_at": self.created_at,
        }


class TaskManager:
    """Thread-safe background task manager."""

    def __init__(self) -> None:
        self.tasks: Dict[str, JobTask] = {}
        self.lock = threading.Lock()

    def create_download_task(self, url: str, options: Dict[str, Any]) -> JobTask:
        task_id = str(uuid.uuid4())[:8]
        task = JobTask(
            task_id=task_id,
            task_type="download",
            status="queued",
            url=url,
            options=options,
        )
        with self.lock:
            self.tasks[task_id] = task
        
        thread = threading.Thread(target=self._run_download_worker, args=(task,), daemon=True)
        thread.start()
        return task

    def create_retrofit_task(self, options: Dict[str, Any]) -> JobTask:
        task_id = str(uuid.uuid4())[:8]
        task = JobTask(
            task_id=task_id,
            task_type="retrofit",
            status="queued",
            url=options.get("dir", ""),
            options=options,
        )
        with self.lock:
            self.tasks[task_id] = task

        thread = threading.Thread(target=self._run_retrofit_worker, args=(task,), daemon=True)
        thread.start()
        return task

    def get_task(self, task_id: str) -> Optional[JobTask]:
        with self.lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status in ("queued", "running"):
                task._cancel_requested = True
                task.status = "cancelled"
                task.add_log("Tugas dibatalkan oleh pengguna.", level="warn")
                return True
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [t.to_dict() for t in sorted(self.tasks.values(), key=lambda x: x.created_at, reverse=True)[:20]]

    # ------------------------------------------------------------------------
    # Worker: Download
    # ------------------------------------------------------------------------
    def _run_download_worker(self, task: JobTask) -> None:
        task.status = "running"
        task.stage_message = "Menganalisis URL & Target..."
        task.add_log(f"Memulai tugas unduhan untuk: {task.url}", level="cyan")

        output_dir = task.options.get("output_dir") or get_output_dir_from_config()
        codec = task.options.get("codec", "mp3")
        quality = task.options.get("quality", "320")
        max_songs = task.options.get("max_songs")
        lyrics_mode = task.options.get("lyrics_mode", "🎧 1")
        transliterate = task.options.get("transliterate", "❌ 1")
        translate_id = bool(task.options.get("translate_id", True))
        embed_id3 = bool(task.options.get("embed_id3", True))
        anti_duplicate = bool(task.options.get("anti_duplicate", True))
        sync_huawei = bool(task.options.get("sync_huawei", False))
        notify_discord = bool(task.options.get("notify_discord", True))

        os.makedirs(output_dir, exist_ok=True)
        archive_file = os.path.join(output_dir, "archive.txt") if anti_duplicate else None

        # 1. Snapshot file sebelum download
        before_files: Dict[str, float] = {}
        for root, _, files in os.walk(output_dir):
            for f in files:
                p = os.path.join(root, f)
                try:
                    before_files[p] = os.path.getmtime(p)
                except OSError:
                    pass

        # 2. Resolusi Target (Spotify vs SoundCloud vs YouTube vs Search)
        targets: List[str] = [task.url]
        target_platform = "Universal"

        if is_spotify_url(task.url):
            target_platform = "Spotify"
            task.add_log("Mendeteksi URL Spotify. Mengurai daftar trek...", level="cyan")
            try:
                tracks = parse_spotify_url_safe(task.url)
                if not tracks:
                    raise ValueError("Tidak ditemukan lagu dari URL Spotify yang diberikan.")
                task.add_log(f"Berhasil mengurai {len(tracks)} lagu dari Spotify!", level="success")
                targets = [build_ytsearch_query(t, limit=1) for t in tracks]
                if max_songs:
                    targets = targets[:max_songs]
            except Exception as e:
                task.status = "error"
                task.error = f"Gagal membaca URL Spotify: {e}"
                task.add_log(str(e), level="error")
                return
        elif "soundcloud.com" in task.url.lower():
            target_platform = "SoundCloud"
            task.add_log("Mendeteksi URL SoundCloud.", level="cyan")
            targets = [task.url]
        elif not (task.url.startswith("http://") or task.url.startswith("https://")):
            target_platform = "Search"
            limit = max_songs if max_songs else 1
            targets = [f"ytsearch{limit}:{task.url}"]
            task.add_log(f"Pencarian kata kunci: '{task.url}' (Top {limit})", level="cyan")

        # 3. Setup yt-dlp Hook & Options
        def progress_hook(d: Dict[str, Any]) -> None:
            if task._cancel_requested:
                raise KeyboardInterrupt("Tugas dibatalkan.")
            
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = (downloaded / total) * 100.0
                    task.progress = round(pct, 1)
                
                speed = d.get("speed")
                if speed:
                    task.speed = f"{speed / 1024 / 1024:.1f} MB/s"
                
                eta = d.get("eta")
                if eta:
                    task.eta = f"{int(eta)}s"
                
                filename = os.path.basename(d.get("filename", "Audio"))
                task.stage_message = f"Mengunduh: {filename}"
            elif status == "finished":
                filename = os.path.basename(d.get("filename", "Audio"))
                task.stage_message = f"Memproses konversi: {filename}"
                task.add_log(f"Selesai mengunduh raw audio: {filename}", level="green")

        class WebYTDLPLogger:
            def debug(self, msg: str) -> None: pass
            def warning(self, msg: str) -> None: pass
            def error(self, msg: str) -> None:
                if not any(k in msg.lower() for k in ["metadata", "thumbnail", "subtitles", "429"]):
                    task.add_log(f"yt-dlp: {msg}", level="error")

        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
        if target_platform == "Spotify":
            outtmpl = os.path.join(output_dir, "Spotify_Downloads", "%(title)s.%(ext)s")
        elif target_platform == "SoundCloud":
            outtmpl = os.path.join(output_dir, "SoundCloud_Downloads", "%(title)s.%(ext)s")

        ydl_opts = build_download_opts(
            outtmpl=outtmpl,
            codec=codec,
            quality=quality,
            archive_file=archive_file,
            lyrics_from_youtube_cc=lyrics_mode.startswith("📺 3"),
            max_songs=max_songs,
            progress_hook=progress_hook,
        )
        ydl_opts["logger"] = WebYTDLPLogger()

        # 4. Eksekusi yt-dlp
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for idx, t in enumerate(targets):
                    if task._cancel_requested:
                        break
                    task.stage_message = f"Mengunduh item {idx+1}/{len(targets)}..."
                    try:
                        ydl.download([t])
                    except Exception as yt_err:
                        task.add_log(f"Peringatan download ({t}): {yt_err}", level="yellow")
        except KeyboardInterrupt:
            task.status = "cancelled"
            task.add_log("Tugas dibatalkan oleh pengguna.", level="warn")
            return
        except Exception as e:
            task.status = "error"
            task.error = str(e)
            task.add_log(f"Error yt-dlp: {e}", level="error")
            return

        # 5. Cari file audio baru yang dihasilkan
        new_audio_files: List[str] = []
        for root, _, files in os.walk(output_dir):
            for f in files:
                if f.lower().endswith((".mp3", ".flac", ".wav", ".m4a")):
                    p = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(p)
                        if p not in before_files or mtime > before_files.get(p, 0):
                            new_audio_files.append(p)
                    except OSError:
                        pass
        new_audio_files.sort()
        task.downloaded_files = new_audio_files

        # 6. Post-processing Lirik, Transliterasi, Terjemahan, ID3
        download_lyrics = not lyrics_mode.startswith("❌ 4")
        if download_lyrics and new_audio_files:
            task.progress = 90.0
            task.stage_message = "Memproses lirik sinkron & transliterasi..."
            task.add_log(f"Memproses lirik untuk {len(new_audio_files)} file audio baru...", level="cyan")

            for audio_path in new_audio_files:
                if task._cancel_requested:
                    break
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                dir_path = os.path.dirname(audio_path)
                lrc_path = os.path.join(dir_path, f"{base_name}.lrc")

                # Fetch synced lyrics
                if not os.path.exists(lrc_path):
                    task.add_log(f"Mencari lirik studio untuk '{base_name}'...", level="dim")
                    fetch_synced_lyrics(
                        title=base_name,
                        lrc_path=lrc_path,
                        sync_huawei=sync_huawei,
                        transliterate_mode=transliterate,
                        translate_mode=translate_id,
                    )
                else:
                    # Kalau lirik sudah ada, jalankan transliterasi & terjemahan
                    process_transliteration(lrc_path, transliterate)
                    if translate_id:
                        process_translation(lrc_path, True)
                    if sync_huawei:
                        sync_huawei_lrc(lrc_path)

                # Embed ID3
                if embed_id3 and os.path.exists(lrc_path):
                    try:
                        embed_lyrics_to_audio(audio_path, lrc_path)
                        task.add_log(f"Lirik & Cover tertanam ke ID3: {base_name}", level="dim")
                    except Exception as emb_e:
                        task.add_log(f"Embed ID3 gagal ({base_name}): {emb_e}", level="yellow")

        # 7. Selesai
        task.progress = 100.0
        task.status = "completed"
        task.stage_message = "Unduhan & Pemrosesan Selesai!"
        task.add_log(f"🎉 Selesai! {len(new_audio_files)} lagu berhasil diunduh.", level="success")

        # Kirim notifikasi Discord jika diaktifkan
        if notify_discord and new_audio_files:
            song_list = "\n".join([f"• {os.path.basename(f)}" for f in new_audio_files[:8]])
            if len(new_audio_files) > 8:
                song_list += f"\n*...dan {len(new_audio_files) - 8} lagu lainnya*"
            
            fields = [
                {"name": "Total Lagu", "value": str(len(new_audio_files)), "inline": True},
                {"name": "Format", "value": f"{codec.upper()} {quality}k", "inline": True},
                {"name": "Platform", "value": target_platform, "inline": True},
                {"name": "Lirik & Terjemahan", "value": "✅ Aktif" if download_lyrics else "❌ Nonaktif", "inline": True},
            ]
            if song_list:
                fields.append({"name": "Daftar Lagu", "value": song_list, "inline": False})
            
            send_discord_notification(
                title=f"Unduhan Berhasil: {target_platform}",
                description=f"Unduhan dari `{task.url[:80]}` telah berhasil diproses oleh Web Engine.",
                fields=fields,
                color=3447003  # Greenish
            )

    # ------------------------------------------------------------------------
    # Worker: Retrofit
    # ------------------------------------------------------------------------
    def _run_retrofit_worker(self, task: JobTask) -> None:
        task.status = "running"
        target_dir = task.options.get("dir") or get_output_dir_from_config()
        task.stage_message = f"Memindai folder: {target_dir}"
        task.add_log(f"Memulai Retrofit Engine pada folder: {target_dir}", level="cyan")

        if not os.path.exists(target_dir):
            task.status = "error"
            task.error = f"Folder tidak ditemukan: {target_dir}"
            task.add_log(task.error, level="error")
            return

        try:
            from mmpd.modes.retrofit import run_retrofit_noninteractive
            ret_code = run_retrofit_noninteractive(
                target_dir=target_dir,
                target=task.options.get("target", "full"),
                transliterate=task.options.get("transliterate", "❌ 1"),
                translate=bool(task.options.get("translate", True)),
                overwrite=bool(task.options.get("overwrite", False)),
                fetch_missing=True,
                sync_huawei=bool(task.options.get("sync_huawei", False)),
                embed_id3=True,
            )
            if ret_code == 0:
                task.status = "completed"
                task.progress = 100.0
                task.stage_message = "Retrofit Selesai!"
                task.add_log("✨ Seluruh file lama berhasil diperbaiki.", level="success")
            else:
                task.status = "error"
                task.error = "Retrofit selesai dengan beberapa catatan error."
                task.add_log("Retrofit selesai dengan peringatan.", level="yellow")
        except Exception as e:
            task.status = "error"
            task.error = str(e)
            task.add_log(f"Fatal error pada retrofit: {e}", level="error")


# Singleton TaskManager
task_manager = TaskManager()


# ============================================================================
# Flask Application Setup
# ============================================================================

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    # ------------------------------------------------------------------------
    # Route: Main Single Page App
    # ------------------------------------------------------------------------
    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    # ------------------------------------------------------------------------
    # API: Download & Tasks
    # ------------------------------------------------------------------------
    @app.route("/api/download", methods=["POST"])
    def api_download():
        data = request.get_json() or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"error": "URL atau kata kunci tidak boleh kosong"}), 400

        task = task_manager.create_download_task(url=url, options=data)
        return jsonify({"task_id": task.task_id, "status": task.status})

    @app.route("/api/task/<task_id>")
    def api_get_task(task_id: str):
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({"error": "Task tidak ditemukan"}), 404
        return jsonify(task.to_dict())

    @app.route("/api/task/<task_id>/cancel", methods=["POST"])
    def api_cancel_task(task_id: str):
        ok = task_manager.cancel_task(task_id)
        return jsonify({"ok": ok})

    @app.route("/api/tasks")
    def api_list_tasks():
        return jsonify(task_manager.list_tasks())

    # ------------------------------------------------------------------------
    # API: Retrofit
    # ------------------------------------------------------------------------
    @app.route("/api/retrofit", methods=["POST"])
    def api_retrofit():
        data = request.get_json() or {}
        task = task_manager.create_retrofit_task(options=data)
        return jsonify({"task_id": task.task_id, "status": task.status})

    # ------------------------------------------------------------------------
    # API: Music Library & Streaming Player
    # ------------------------------------------------------------------------
    @app.route("/api/library")
    def api_library():
        output_dir = get_output_dir_from_config()
        items = []

        if os.path.exists(output_dir):
            for root, _, files in os.walk(output_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".mp3", ".flac", ".wav", ".m4a"):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, output_dir)
                        base_no_ext = os.path.splitext(full_path)[0]
                        lrc_path = f"{base_no_ext}.lrc"
                        has_lrc = os.path.exists(lrc_path)
                        
                        has_id_lyrics = False
                        if has_lrc:
                            try:
                                with open(lrc_path, "r", encoding="utf-8", errors="ignore") as lf:
                                    content = lf.read()
                                    if "(" in content and ")" in content:
                                        has_id_lyrics = True
                            except OSError:
                                pass

                        try:
                            st = os.stat(full_path)
                            size_mb = round(st.st_size / (1024 * 1024), 2)
                        except OSError:
                            size_mb = 0.0

                        # Title & Artist
                        title = os.path.splitext(f)[0]
                        artist = ""
                        try:
                            import mutagen
                            mf = mutagen.File(full_path)
                            if mf and hasattr(mf, "tags") and mf.tags:
                                if "TIT2" in mf.tags:
                                    title = str(mf.tags["TIT2"])
                                elif "title" in mf.tags:
                                    title = str(mf.tags["title"][0])
                                if "TPE1" in mf.tags:
                                    artist = str(mf.tags["TPE1"])
                                elif "artist" in mf.tags:
                                    artist = str(mf.tags["artist"][0])
                        except Exception:
                            pass

                        items.append({
                            "title": title,
                            "artist": artist,
                            "ext": ext.replace(".", ""),
                            "size_mb": size_mb,
                            "rel_path": rel_path,
                            "lrc_rel_path": os.path.relpath(lrc_path, output_dir) if has_lrc else "",
                            "has_lrc": has_lrc,
                            "has_id_lyrics": has_id_lyrics,
                        })

        return jsonify(items)

    @app.route("/api/stream/<path:relpath>")
    def api_stream(relpath: str):
        output_dir = get_output_dir_from_config()
        full_path = os.path.abspath(os.path.join(output_dir, relpath))
        if not full_path.startswith(os.path.abspath(output_dir)):
            abort(403)
        if not os.path.exists(full_path):
            abort(404)
        return send_file(full_path, conditional=True)

    @app.route("/api/download-file/<path:relpath>")
    def api_download_file(relpath: str):
        output_dir = get_output_dir_from_config()
        full_path = os.path.abspath(os.path.join(output_dir, relpath))
        if not full_path.startswith(os.path.abspath(output_dir)):
            abort(403)
        if not os.path.exists(full_path):
            abort(404)
        return send_file(full_path, as_attachment=True)

    @app.route("/api/lyrics/<path:relpath>")
    def api_lyrics(relpath: str):
        output_dir = get_output_dir_from_config()
        full_path = os.path.abspath(os.path.join(output_dir, relpath))
        if not full_path.startswith(os.path.abspath(output_dir)):
            abort(403)
        
        # If passed an audio file, check for matching .lrc
        if not full_path.endswith(".lrc"):
            full_path = f"{os.path.splitext(full_path)[0]}.lrc"

        if not os.path.exists(full_path):
            return jsonify({"lines": [], "raw": ""}), 404

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except OSError as e:
            return jsonify({"error": str(e)}), 500

        # Parse bilingual synced lyrics
        # Pattern: [mm:ss.xx] Original text (Translation text)
        ts_re = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
        lines = []
        for line in raw_text.splitlines():
            line = line.strip()
            m = ts_re.match(line)
            if not m:
                continue
            ts = int(m.group(1)) * 60 + float(m.group(2))
            text = ts_re.sub("", line).strip()
            
            # Check translation pattern
            translation = None
            paren_match = re.search(r"\(([^)]+)\)$", text)
            if paren_match:
                translation = paren_match.group(1).strip()
                text = text[:paren_match.start()].strip()

            lines.append({
                "time": ts,
                "text": text,
                "translation": translation,
            })

        lines.sort(key=lambda x: x["time"])
        return jsonify({"lines": lines, "raw": raw_text})

    # ------------------------------------------------------------------------
    # API: Doctor Diagnostics & Config
    # ------------------------------------------------------------------------
    @app.route("/api/doctor")
    def api_doctor():
        output_dir = get_output_dir_from_config()
        ffmpeg_ok = False
        import shutil
        if shutil.which("ffmpeg"):
            ffmpeg_ok = True

        ytdlp_ver = "unknown"
        try:
            import yt_dlp
            ytdlp_ver = getattr(yt_dlp, "__version__", "installed")
        except ImportError:
            pass

        storage_ok = os.access(output_dir, os.W_OK) if os.path.exists(output_dir) else True

        return jsonify({
            "ffmpeg_ok": ffmpeg_ok,
            "python_version": sys.version.split()[0],
            "ytdlp_version": ytdlp_ver,
            "output_dir": output_dir,
            "storage_ok": storage_ok,
            "is_termux": is_termux(),
            "version": __version__,
        })

    @app.route("/api/config")
    def api_config():
        return jsonify({
            "version": __version__,
            "output_dir": get_output_dir_from_config(),
            "is_termux": is_termux(),
        })

    @app.route("/api/webhook/test", methods=["POST"])
    def api_webhook_test():
        ok = send_discord_notification(
            title="Uji Coba Koneksi Webhook Berhasil!",
            description="Antarmuka Web Browser MMPD berhasil terhubung ke server Discord Anda.",
            fields=[
                {"name": "Status", "value": "200 OK / Active", "inline": True},
                {"name": "Waktu", "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
            ],
            color=5793266
        )
        return jsonify({"ok": ok, "error": None if ok else "Gagal mengirim webhook. Cek URL atau koneksi internet."})

    return app


# ============================================================================
# Server Runner Helper
# ============================================================================

def get_lan_ip() -> str:
    """Deteksi IP address lokal untuk akses perangkat lain di LAN/WiFi yang sama."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # tidak perlu benar-benar terhubung ke internet, hanya untuk bind interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server(host: str = "0.0.0.0", port: int = 5000, open_browser: bool = True) -> None:
    """Jalankan web server Flask dan buka browser."""
    app = create_app()
    lan_ip = get_lan_ip()

    print("\n" + "=" * 60)
    print(" 🎵 MUSIC MIX & PLAYLIST DOWNLOADER — WEB BROWSER EDITION")
    print(f" Versi: v{__version__} | Crafted by NanoMindExplorer")
    print("=" * 60)
    print(f" 👉 Lokal (perangkat ini):  http://localhost:{port}")
    if lan_ip != "127.0.0.1":
        print(f" 👉 Jaringan WiFi / LAN:   http://{lan_ip}:{port}")
    print("=" * 60)
    print(" Tekan Ctrl+C di terminal ini untuk mematikan server.\n")

    if open_browser:
        def _open():
            time.sleep(1.2)
            try:
                webbrowser.open(f"http://localhost:{port}")
            except Exception:
                pass
        threading.Thread(target=_open, daemon=True).start()

    # Matikan log default Werkzeug yang berisik
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    run_server()
