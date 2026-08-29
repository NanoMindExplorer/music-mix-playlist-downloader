"""
Config loader — baca config.toml user (Fase C).

Sebelumnya `AppConfig.config_file` didefinisikan tapi TIDAK PERNAH dibaca.
Sekarang ada loader sungguhan dengan prioritas (tinggi → rendah):

    1. Environment variable   (MMPD_OUTPUT_DIR, SPOTIPY_CLIENT_ID, ...)
    2. File kredensial 0600   (~/.config/mmpd/credentials.toml — hanya
                               [spotify] client_id/secret, tidak pernah
                               di-commit; dibuat otomatis contoh saat
                               pertama kali)
    3. config.toml            (~/.config/mmpd/config.toml)
    4. Default dari AppConfig

Skema config.toml (semua opsional):

    [general]
    output_dir = "~/storage/downloads/YT_Downloader"   # path output
    workers = 2                                        # worker retrofit paralel

    [lyrics]
    bilingual_format = "gabung"      # gabung | pisah | id_only
    translate = true                 # default terjemahan aktif
    transliterate = "auto"           # auto | ja | zh | yue | off
    sync_huawei = false              # copy .lrc ke Musiclrc (Termux)
    embed_id3 = true                 # tanam USLT/SYLT ke audio
    no_overwrite = true              # JANGAN timpa .lrc lama (default safety)

    [spotify]
    client_id = "..."                # atau pakai env SPOTIPY_CLIENT_ID
    client_secret = "..."            # atau pakai env SPOTIPY_CLIENT_SECRET

    [network]
    provider_timeout = 30            # detik, timeout per provider lirik
    translate_backoff = 2            # detik antar retry translate

Python 3.11+ memakai tomllib; 3.9/3.10 mencoba tomli lalu fallback parser
minimal (subset: section + key = value skalar). File kredensial dipaksa
permission 0600.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

from mmpd.config import get_config
from mmpd.logger import get_logger

_log = get_logger()

# Singleton hasil merge
_LOADED: Optional[Dict[str, Any]] = None

# Env var yang di-set oleh loader sendiri (bukan oleh user). Kalau user sudah
# export SPOTIPY_CLIENT_ID sendiri, kita TIDAK PERNAH menimpanya; tapi kalau
# nilai lama berasal dari loader (file config berubah), reload boleh menimpa.
_ENV_SET_BY_LOADER: set = set()

_CREDENTIALS_FILENAME = "credentials.toml"

EXAMPLE_CONFIG = """\
# Contoh config mmpd — salin ke ~/.config/mmpd/config.toml
# Semua kunci opsional; hapus baris yang tidak perlu.
# Prioritas: ENV var > credentials.toml > config.toml > default.

[general]
# output_dir = "~/storage/downloads/YT_Downloader"
# workers = 2

[lyrics]
# bilingual_format = "gabung"     # gabung | pisah | id_only
# translate = true
# transliterate = "auto"          # auto | ja | zh | yue | off
# sync_huawei = false
# embed_id3 = true
# no_overwrite = true

[spotify]
# client_id = "isi-dari-dashboard"
# client_secret = "isi-dari-dashboard"

[network]
# provider_timeout = 30
# translate_backoff = 2
"""


# ============================================================================
# TOML parsing (tomllib → tomli → fallback minimal)
# ============================================================================

def _load_toml(path: Path) -> Dict[str, Any]:
    """Parse file TOML. Return dict kosong kalau gagal/file kosong."""
    if not path.exists():
        return {}
    try:
        raw = path.read_bytes()
    except Exception as e:
        _log.warning("Gagal baca config %s: %s", path, e)
        return {}

    # 1. tomllib (Python 3.11+)
    try:
        import tomllib
        return tomllib.loads(raw.decode("utf-8"))
    except ImportError:
        pass

    # 2. tomli (pip install tomli)
    try:
        import tomli
        return tomli.loads(raw.decode("utf-8"))
    except ImportError:
        pass

    # 3. Fallback parser minimal — subset: [section] + key = value skalar
    return _parse_toml_minimal(raw.decode("utf-8", errors="replace"))


def _parse_toml_minimal(text: str) -> Dict[str, Any]:
    """Parser TOML minimal untuk subset yang didukung (Python 3.9 tanpa tomli)."""
    result: Dict[str, Any] = {}
    current: Dict[str, Any] = result
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            current = result.setdefault(section, {})
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().strip('"').strip("'")
        value = value.strip()
        # Buang komentar inline (hati-hati # di dalam string)
        if value.startswith('"'):
            end = value.find('"', 1)
            if end != -1:
                current[key] = value[1:end]
                continue
        if value.startswith("'"):
            end = value.find("'", 1)
            if end != -1:
                current[key] = value[1:end]
                continue
        value = value.split("#", 1)[0].strip()
        if value.lower() in ("true", "false"):
            current[key] = value.lower() == "true"
        else:
            try:
                current[key] = int(value)
            except ValueError:
                current[key] = value.strip('"').strip("'")
    return result


# ============================================================================
# Loader utama
# ============================================================================

def _expand_path(value: str) -> str:
    """Expand ~ dan $HOME pada path string."""
    return os.path.expanduser(os.path.expandvars(value))


def _get_credentials_path() -> Path:
    return get_config().config_file.parent / _CREDENTIALS_FILENAME


def _load_credentials() -> Dict[str, Any]:
    """Baca credentials.toml (permission dipaksa 0600)."""
    cred_path = _get_credentials_path()
    if not cred_path.exists():
        return {}
    # Pastikan permission ketat (jangan error kalau filesystem read-only)
    try:
        os.chmod(cred_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    return _load_toml(cred_path)


def _apply_env_overrides(merged: Dict[str, Any]) -> None:
    """ENV var menang atas file (kecuali untuk spotify yang sudah env-native)."""
    env_map = {
        "MMPD_OUTPUT_DIR": ("general", "output_dir"),
        "MMPD_BILINGUAL_FORMAT": ("lyrics", "bilingual_format"),
        "MMPD_WORKERS": ("general", "workers"),
    }
    for env_key, (section, key) in env_map.items():
        if env_key in os.environ:
            merged.setdefault(section, {})[key] = os.environ[env_key]

    # Spotify: env yang di-set USER lebih dipercaya daripada file. Env yang
    # di-set loader sendiri (run sebelumnya) boleh ditimpa kalau file berubah.
    spotify_cfg = merged.get("spotify", {})
    if isinstance(spotify_cfg, dict):
        for file_key, env_key in (
            ("client_id", "SPOTIPY_CLIENT_ID"),
            ("client_secret", "SPOTIPY_CLIENT_SECRET"),
        ):
            value = spotify_cfg.get(file_key)
            if not value:
                continue
            if env_key not in os.environ or env_key in _ENV_SET_BY_LOADER:
                os.environ[env_key] = str(value)
                _ENV_SET_BY_LOADER.add(env_key)


def load_config(force: bool = False) -> Dict[str, Any]:
    """
    Muat & merge config (singleton). Urutan: default → config.toml →
    credentials.toml → ENV override.

    Returns:
        Dict nested {section: {key: value}}. Selalu mengembalikan dict
        (kosong kalau tidak ada config sama sekali).
    """
    global _LOADED
    if _LOADED is not None and not force:
        return _LOADED

    config = get_config()
    merged: Dict[str, Any] = {}

    # 1. config.toml utama
    main_cfg = _load_toml(config.config_file)
    for section, values in main_cfg.items():
        if isinstance(values, dict):
            merged.setdefault(section, {}).update(values)

    # 2. credentials.toml (0600) — menang atas config.toml untuk spotify
    creds = _load_credentials()
    for section, values in creds.items():
        if isinstance(values, dict):
            merged.setdefault(section, {}).update(values)

    # 3. ENV override
    _apply_env_overrides(merged)

    _LOADED = merged
    return merged


def get_setting(section: str, key: str, default: Any = None) -> Any:
    """Ambil satu setting dengan default."""
    cfg = load_config()
    try:
        value = cfg[section][key]
        return value if value is not None else default
    except (KeyError, TypeError):
        return default


def get_lyrics_settings() -> Dict[str, Any]:
    """Setting [lyrics] dengan default aman (Fase L: no_overwrite=True)."""
    cfg = load_config()
    lyrics = cfg.get("lyrics", {}) if isinstance(cfg.get("lyrics"), dict) else {}
    return {
        "bilingual_format": lyrics.get("bilingual_format", "gabung"),
        "translate": bool(lyrics.get("translate", False)),
        "transliterate": lyrics.get("transliterate", "off"),
        "sync_huawei": bool(lyrics.get("sync_huawei", False)),
        "embed_id3": bool(lyrics.get("embed_id3", True)),
        "no_overwrite": bool(lyrics.get("no_overwrite", True)),
    }


def get_output_dir_from_config() -> str:
    """Output dir dari config (dengan expand ~), fallback AppConfig."""
    value = get_setting("general", "output_dir")
    if value:
        return _expand_path(str(value))
    return str(get_config().output_dir)


def get_workers(default: int = 1) -> int:
    """Jumlah worker paralel retrofit (default 1 = aman untuk Termux)."""
    value = get_setting("general", "workers", default)
    try:
        n = int(value)
        return max(1, min(n, 4))  # cap 4 — lebih dari itu rawan rate-limit
    except (TypeError, ValueError):
        return default


def create_example_config() -> Path:
    """Tulis contoh config.toml kalau belum ada. Return path-nya."""
    config = get_config()
    config.config_file.parent.mkdir(parents=True, exist_ok=True)
    if not config.config_file.exists():
        config.config_file.write_text(EXAMPLE_CONFIG, encoding="utf-8")
        _log.info("Contoh config dibuat: %s", config.config_file)
    return config.config_file


def reset_config_loader() -> None:
    """Reset singleton (untuk testing)."""
    global _LOADED, _ENV_SET_BY_LOADER
    _LOADED = None
    _ENV_SET_BY_LOADER = set()
