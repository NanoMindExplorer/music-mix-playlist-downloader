"""
Config & Environment Detection terpusat.

Sebelumnya path detection (Termux vs Linux vs Windows) tersebar di banyak
lokasi di downloader.py. Modul ini menyatukan semua logika tersebut agar:
- Mudah di-test
- Konsisten di semua modul
- Single source of truth
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def is_termux() -> bool:
    """Deteksi apakah berjalan di Termux (Android)."""
    return "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", "")


def is_windows() -> bool:
    """Deteksi Windows (NTFS path restrictions apply)."""
    return os.name == "nt"


def is_macos() -> bool:
    """Deteksi macOS."""
    return os.uname().sysname == "Darwin" if hasattr(os, "uname") else False


@dataclass(frozen=True)
class AppConfig:
    """
    Konfigurasi path aplikasi. Semua path diturunkan dari sini agar konsisten.

    Field:
        is_termux    : Berjalan di Termux?
        is_windows   : Berjalan di Windows?
        home_dir     : Home directory user (Path)
        downloads_dir: Folder Downloads default
        output_dir   : Folder output utama (YT_Downloader)
        music_dir    : Folder Music (untuk Huawei/HarmonyOS Musiclrc sync)
        musiclrc_dir : Folder Musiclrc khusus Huawei
        log_dir      : Folder log file (structured logging)
        cache_dir    : Folder cache (translation cache, metadata cache)
        config_file  : Path ke config file TOML opsional (Fase 2.2)
    """

    is_termux: bool = field(default_factory=is_termux)
    is_windows: bool = field(default_factory=is_windows)
    home_dir: Path = field(default_factory=lambda: Path.home())

    downloads_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    music_dir: Path = field(init=False)
    musiclrc_dir: Path = field(init=False)
    log_dir: Path = field(init=False)
    cache_dir: Path = field(init=False)
    config_file: Path = field(init=False)

    def __post_init__(self) -> None:
        # Karena dataclass frozen, kita pakai object.__setattr__ untuk set field
        # turunan di __post_init__. Ini idiom resmi dari dataclasses docs.
        set_attr = object.__setattr__

        if self.is_termux:
            # Termux: ~/storage/downloads (symlink ke /sdcard/Download)
            #         ~/storage/shared/Music (Internal Storage/Music)
            downloads_dir = self.home_dir / "storage" / "downloads"
            output_dir = downloads_dir / "YT_Downloader"
            music_dir = self.home_dir / "storage" / "shared" / "Music"
            musiclrc_dir = music_dir / "Musiclrc"
        elif self.is_windows:
            # Windows: %USERPROFILE%\\Downloads, %LOCALAPPDATA% untuk cache/log
            downloads_dir = self.home_dir / "Downloads"
            output_dir = downloads_dir / "YT_Downloader"
            music_dir = self.home_dir / "Music"
            musiclrc_dir = music_dir / "Musiclrc"
            local_appdata = Path(os.environ.get("LOCALAPPDATA", self.home_dir / "AppData" / "Local"))
            log_dir = local_appdata / "mmpd" / "logs"
            cache_dir = local_appdata / "mmpd" / "cache"
        else:
            # Linux/macOS: ~/Downloads, ~/.local/share/mmpd/ untuk cache/log
            downloads_dir = self.home_dir / "Downloads"
            output_dir = downloads_dir / "YT_Downloader"
            music_dir = self.home_dir / "Music"
            musiclrc_dir = music_dir / "Musiclrc"
            # XDG Base Directory spec
            xdg_data = Path(os.environ.get("XDG_DATA_HOME", self.home_dir / ".local" / "share"))
            log_dir = xdg_data / "mmpd" / "logs"
            cache_dir = xdg_data / "mmpd" / "cache"

        # Untuk Termux, log & cache pakai PREFIX/var (lebih konsisten dengan Termux)
        if self.is_termux:
            prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
            log_dir = prefix / "var" / "log" / "mmpd"
            cache_dir = prefix / "var" / "cache" / "mmpd"

        # Config file: ~/.config/mmpd/config.toml (atau %APPDATA% di Windows)
        if self.is_windows:
            appdata = Path(os.environ.get("APPDATA", self.home_dir / "AppData" / "Roaming"))
            config_file = appdata / "mmpd" / "config.toml"
        else:
            xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", self.home_dir / ".config"))
            config_file = xdg_config / "mmpd" / "config.toml"

        # Set field turunan (frozen-safe via object.__setattr__)
        set_attr(self, "downloads_dir", downloads_dir)
        set_attr(self, "output_dir", output_dir)
        set_attr(self, "music_dir", music_dir)
        set_attr(self, "musiclrc_dir", musiclrc_dir)
        set_attr(self, "log_dir", log_dir)
        set_attr(self, "cache_dir", cache_dir)
        set_attr(self, "config_file", config_file)

    def ensure_dirs(self) -> None:
        """Pastikan semua direktori yang dibutuhkan sudah ada."""
        for path in [
            self.output_dir,
            self.log_dir,
            self.cache_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


# Singleton global config (immutable)
_CONFIG: AppConfig | None = None


def get_config() -> AppConfig:
    """Dapatkan instance AppConfig singleton (lazy init)."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = AppConfig()
    return _CONFIG


def reset_config() -> None:
    """Reset config singleton (untuk testing)."""
    global _CONFIG
    _CONFIG = None


def get_output_dir() -> str:
    """Backward-compat helper: return output_dir as string (seperti get_default_path lama)."""
    return str(get_config().output_dir)


def get_musiclrc_dir() -> str:
    """Backward-compat helper: return musiclrc_dir as string."""
    return str(get_config().musiclrc_dir)
