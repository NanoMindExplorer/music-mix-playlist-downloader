"""
Tests Fase C — CLI argparse + config.toml loader + self-update.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mmpd.cli import build_parser, main, VALID_LRC_FORMATS


# ============================================================================
# Parser CLI
# ============================================================================

class TestCLIParser:
    def test_no_args_means_interactive(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_version_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_download_full_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "download", "https://youtube.com/watch?v=x",
            "--format", "flac",
            "--lyrics", "youtube-cc",
            "--translate",
            "--transliterate", "auto",
            "--lrc-format", "pisah",
            "--sync-huawei",
            "--max", "5",
        ])
        assert args.command == "download"
        assert args.format == "flac"
        assert args.lyrics == "youtube-cc"
        assert args.translate is True
        assert args.transliterate == "auto"
        assert args.lrc_format == "pisah"
        assert args.sync_huawei is True
        assert args.max == 5

    def test_retrofit_lyrics_only_no_overwrite_default(self):
        parser = build_parser()
        args = parser.parse_args([
            "retrofit", "--dir", "/tmp/x",
            "--lyrics-only", "--translate",
        ])
        assert args.command == "retrofit"
        assert args.lyrics_only is True
        assert args.overwrite is False, "Default HARUS no-overwrite (safety Fase L)"

    def test_retrofit_overwrite_opt_in(self):
        parser = build_parser()
        args = parser.parse_args(["retrofit", "--dir", "/tmp/x", "--overwrite"])
        assert args.overwrite is True

    def test_retrofit_mutually_exclusive_targets(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["retrofit", "--dir", "/tmp/x", "--lyrics-only", "--covers-only"])

    def test_lyrics_dir_required(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["lyrics"])

    def test_cache_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["cache", "--stats"])
        assert args.command == "cache"
        assert args.stats is True

    def test_self_update_no_pull(self):
        parser = build_parser()
        args = parser.parse_args(["self-update", "--no-pull"])
        assert args.command == "self-update"
        assert args.no_pull is True

    def test_invalid_lrc_format_rejected(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["retrofit", "--dir", "/tmp/x", "--lrc-format", "gabungan"])

    def test_valid_lrc_formats(self):
        assert set(VALID_LRC_FORMATS) == {"gabung", "pisah", "id_only"}


class TestCLIMain:
    def test_version_prints_and_exits_zero(self, capsys):
        assert main(["--version"]) == 0
        out = capsys.readouterr().out
        assert out.startswith("mmpd ")
        assert "unknown" not in out  # versi asli dari mmpd.__version__

    def test_doctor_dispatch(self, monkeypatch):
        from mmpd import doctor
        monkeypatch.setattr(doctor, "run_doctor", lambda: 0)
        assert main(["doctor"]) == 0

    def test_cache_stats_dispatch(self, capsys):
        assert main(["cache", "--stats"]) == 0
        out = capsys.readouterr().out
        assert "Statistik Cache" in out


# ============================================================================
# Config loader
# ============================================================================

class TestConfigLoader:
    @pytest.fixture(autouse=True)
    def _reset(self, tmp_path, monkeypatch):
        """Arahkan config_file ke tmp_path supaya test terisolasi.

        Cleanup env dilakukan di SETUP (bukan cuma teardown) supaya kebocoran
        dari test manapun tidak mempengaruhi test ini.
        """
        from mmpd import config as config_mod
        from mmpd import config_loader

        for key in (
            "MMPD_OUTPUT_DIR", "MMPD_BILINGUAL_FORMAT", "MMPD_WORKERS",
            "SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET",
        ):
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        config_mod.reset_config()
        config_loader.reset_config_loader()
        yield
        config_mod.reset_config()
        config_loader.reset_config_loader()
        for key in (
            "MMPD_OUTPUT_DIR", "MMPD_BILINGUAL_FORMAT", "MMPD_WORKERS",
            "SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET",
        ):
            monkeypatch.delenv(key, raising=False)

    def _write_config(self, tmp_path: Path, content: str) -> Path:
        cfg_path = tmp_path / ".config" / "mmpd" / "config.toml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(content, encoding="utf-8")
        return cfg_path

    def test_empty_when_no_config(self, tmp_path):
        from mmpd.config_loader import load_config
        assert load_config(force=True) == {}

    def test_parse_full_config(self, tmp_path):
        from mmpd.config_loader import load_config, get_lyrics_settings

        self._write_config(tmp_path, """
[general]
output_dir = "~/music"
workers = 2

[lyrics]
bilingual_format = "pisah"
translate = true
sync_huawei = true
no_overwrite = false

[spotify]
client_id = "abc123"
client_secret = "xyz789"
""")
        cfg = load_config(force=True)
        assert cfg["general"]["workers"] == 2
        assert cfg["lyrics"]["bilingual_format"] == "pisah"

        lyrics = get_lyrics_settings()
        assert lyrics["bilingual_format"] == "pisah"
        assert lyrics["translate"] is True
        assert lyrics["sync_huawei"] is True
        assert lyrics["no_overwrite"] is False
        # embed_id3 default True
        assert lyrics["embed_id3"] is True

    def test_defaults_are_safe(self, tmp_path):
        """Default [lyrics] HARUS no_overwrite=True (safety Fase L)."""
        from mmpd.config_loader import get_lyrics_settings
        lyrics = get_lyrics_settings()
        assert lyrics["no_overwrite"] is True
        assert lyrics["translate"] is False
        assert lyrics["transliterate"] == "off"

    def test_credentials_beat_config_and_env_populated(self, tmp_path, monkeypatch):
        """credentials.toml menang atas config.toml; env var SPOTIPY_* diisi otomatis."""
        from mmpd.config_loader import load_config

        self._write_config(tmp_path, """
[spotify]
client_id = "from-config"
client_secret = "from-config-secret"
""")
        cred_path = tmp_path / ".config" / "mmpd" / "credentials.toml"
        cred_path.write_text(
            '[spotify]\nclient_id = "from-creds"\nclient_secret = "from-creds-secret"\n',
            encoding="utf-8",
        )
        cfg = load_config(force=True)
        assert cfg["spotify"]["client_id"] == "from-creds"
        assert os.environ.get("SPOTIPY_CLIENT_ID") == "from-creds"
        assert os.environ.get("SPOTIPY_CLIENT_SECRET") == "from-creds-secret"

    def test_env_overrides_beat_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MMPD_BILINGUAL_FORMAT", "id_only")
        self._write_config(tmp_path, '[lyrics]\nbilingual_format = "gabung"\n')
        from mmpd.config_loader import load_config
        cfg = load_config(force=True)
        assert cfg["lyrics"]["bilingual_format"] == "id_only"

    def test_minimal_fallback_parser(self, tmp_path):
        """Parser fallback (Python 3.9 tanpa tomli) memahami subset yang sama."""
        from mmpd import config_loader

        self._write_config(tmp_path, """
[general]
workers = 3

[lyrics]
translate = true
bilingual_format = "pisah"
""")
        parsed = config_loader._parse_toml_minimal(
            (tmp_path / ".config" / "mmpd" / "config.toml").read_text(encoding="utf-8")
        )
        assert parsed["general"]["workers"] == 3
        assert parsed["lyrics"]["translate"] is True
        assert parsed["lyrics"]["bilingual_format"] == "pisah"

    def test_create_example_config(self, tmp_path):
        from mmpd.config_loader import create_example_config
        path = create_example_config()
        assert path.exists()
        assert "[lyrics]" in path.read_text(encoding="utf-8")

    def test_get_workers_clamped(self, tmp_path):
        from mmpd.config_loader import get_workers
        assert get_workers() == 1  # default aman
        self._write_config(tmp_path, "[general]\nworkers = 99\n")
        from mmpd.config_loader import load_config
        load_config(force=True)
        assert get_workers() == 4  # cap di 4


# ============================================================================
# Self-update
# ============================================================================

class TestSelfUpdate:
    def test_find_repo_root(self):
        from mmpd.self_update import _find_repo_root
        root = _find_repo_root()
        assert root is not None, "Test jalan dari dalam repo — root harus ketemu"
        # Marker project root: pyproject.toml ( CI container tanpa git
        # melakukan checkout tarball → .git bisa absen, pyproject tetap ada)
        assert (root / "pyproject.toml").exists(), "Root harus berisi pyproject.toml"

    def test_find_repo_root_without_git_marker_fallback(self, tmp_path, monkeypatch):
        """Source tree tanpa .git (tarball/zip) → root tetap ketemu via marker."""
        from mmpd import self_update as su

        src = tmp_path / "src"
        pkg = src / "mmpd"
        pkg.mkdir(parents=True)
        (src / "pyproject.toml").write_text(
            '[project]\nname = "music-mix-playlist-downloader"\n', encoding="utf-8"
        )
        (pkg / "__init__.py").touch()
        # __file__ dipalsukan seolah mmpd terpasang di src/mmpd/
        monkeypatch.setattr(su, "__file__", str(pkg / "self_update.py"))

        root = su._find_repo_root()
        assert root == src, "Fallback marker pyproject+mmpd harus menemukan root"

    def test_find_repo_root_none_for_plain_dir(self, tmp_path, monkeypatch):
        """Instalasi wheel biasa di site-packages → None (self-update tak berlaku)."""
        from mmpd import self_update as su

        sp = tmp_path / "lib" / "python3.14" / "site-packages" / "mmpd"
        sp.mkdir(parents=True)
        monkeypatch.setattr(su, "__file__", str(sp / "self_update.py"))

        assert su._find_repo_root() is None

    def test_run_is_safe_function(self):
        from mmpd.self_update import self_update
        assert callable(self_update)

    def test_dirty_tree_blocks_update(self, tmp_path, monkeypatch):
        """Working tree kotor → update DIBATALKAN (exit 3), bukan force pull."""
        from mmpd import self_update as su

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        monkeypatch.setattr(su, "_find_repo_root", lambda: repo)

        calls = []
        monkeypatch.setattr(
            su, "_run",
            lambda cmd, cwd=None: calls.append(cmd) or (
                (0, " M dirty_file.py") if cmd[:2] == ["git", "status"] else (0, "")
            ),
        )
        code = su.self_update()
        assert code == 3, "Tree kotor harus ditolak dengan kode 3"
        # Tidak boleh sampai ke git pull
        assert not any(c[:2] == ["git", "pull"] for c in calls)
