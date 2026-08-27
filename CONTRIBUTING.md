# 🤝 Contributing to Music Mix Playlist Downloader

Terima kasih sudah tertarik berkontribusi! Dokumen ini akan membantu Anda mulai.

## 🚀 Quick Start untuk Developer

### 1. Fork & Clone

```bash
# Fork repo di GitHub (klik tombol Fork)
# Lalu clone fork Anda:
git clone https://github.com/USERNAME-ANDA/music-mix-playlist-downloader.git
cd music-mix-playlist-downloader
```

### 2. Setup Environment

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies (testing, linting, type checking)
pip install -r requirements-dev.txt

# Install package dalam editable mode
pip install -e .

# Setup pre-commit hooks (auto-lint sebelum commit)
pip install pre-commit
pre-commit install
```

### 3. Setup Spotify API (opsional, untuk ISRC matching)

```bash
# Buka https://developer.spotify.com/dashboard → Create app
# Dapatkan Client ID + Client Secret, lalu:
export SPOTIPY_CLIENT_ID="your_client_id"
export SPOTIPY_CLIENT_SECRET="your_client_secret"
```

### 4. Verify Setup

```bash
# Run tests
pytest tests/ -v

# Run dengan coverage
pytest tests/ --cov=mmpd

# Run mmpd doctor
mmpd doctor
```

## 📁 Struktur Proyek

```
music-mix-playlist-downloader/
├── downloader.py              # Thin entry point (142 baris)
├── pyproject.toml             # PEP 621 packaging config
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Dev dependencies (pytest, mypy, ruff)
│
├── mmpd/                      # Package modular
│   ├── __init__.py            # Version + exports
│   ├── __main__.py            # `python -m mmpd` entry
│   ├── config.py              # Path & env detection (Termux/Linux/Windows)
│   ├── logger.py              # Structured logging + rotation
│   ├── cache.py               # SQLite cache (translation + lyrics)
│   ├── types.py               # TrackInfo, LyricsResult, LyricsProvider Protocol
│   ├── ui.py                  # Banner, theme, questionary helpers
│   ├── ytdlp.py               # yt-dlp wrapper (opts builder, hooks)
│   ├── lyrics.py              # Transliteration + translation pipeline
│   ├── lyrics_providers.py    # LRCLIB + syncedlyrics + fallback chain
│   ├── spotify.py             # Spotify URL parser (spotipy)
│   ├── spotify_client.py      # SpotifyClient (official API)
│   ├── isrc_matcher.py        # ISRC-based YouTube matching (99%+ accuracy)
│   ├── concurrent.py          # ThreadPoolExecutor wrapper
│   ├── doctor.py              # `mmpd doctor` diagnostics
│   ├── utils/                 # Stateless utilities
│   │   ├── ffmpeg.py          # FFmpeg subprocess wrapper
│   │   ├── fs.py              # Atomic write, file ops
│   │   └── matching.py        # rapidfuzz wrapper, query cleaning
│   └── modes/                 # Mode handlers (CLI menus)
│       ├── download.py        # Mode 1/4/5 (YouTube/Spotify/SoundCloud)
│       ├── retrofit.py        # Mode 2 (Perbaiki file lama)
│       └── organizer.py       # Mode 3 (Auto-organizer)
│
├── tests/                     # 376 unit tests, 79% coverage
│   ├── conftest.py            # Shared fixtures
│   ├── test_*.py              # Test files (14 files)
│   └── README.md             # Test documentation
│
├── .github/workflows/ci.yml   # GitHub Actions CI/CD
└── .pre-commit-config.yaml    # Pre-commit hooks
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_cache.py -v

# Specific test class
pytest tests/test_utils_fs.py::TestAtomicWriteText -v

# Specific test function
pytest tests/test_utils_fs.py::TestAtomicWriteText::test_basic_write -v

# With coverage
pytest tests/ --cov=mmpd --cov-report=term

# HTML coverage report
pytest tests/ --cov=mmpd --cov-report=html
# Buka: htmlcov/index.html
```

### Test Guidelines

1. **Mock external dependencies** — no real network calls in tests
   - Mock `yt_dlp.YoutubeDL` via `patch("mmpd.isrc_matcher.yt_dlp.YoutubeDL")`
   - Mock `spotipy` via `patch.dict("sys.modules", {"spotipy": mock})`
   - Mock `requests` via `patch.dict("sys.modules", {"requests": mock})`
   - Use `tmp_path` fixture for filesystem tests

2. **Test naming**: `test_{what}_{condition}_{expected_result}`
   - Example: `test_atomic_write_preserves_timestamps`
   - Example: `test_isrc_match_returns_true_for_exact_match`

3. **Group tests in classes** for readability:
   ```python
   class TestAtomicWriteText:
       def test_basic_write(self, tmp_path):
           ...
   ```

4. **Use fixtures from `conftest.py`** — don't duplicate setup:
   - `mock_track_info` — TrackInfo dengan data realistis
   - `mock_spotify_track` — SpotifyTrack dengan ISRC
   - `mock_termux_env` / `mock_linux_env` — environment mocking
   - `reset_mmpd_singletons` — auto-reset between tests

5. **Coverage target**: 78%+ (current: 79%)

## 🎨 Code Style

### Formatting

Pre-commit hooks akan auto-format dengan **black** dan **ruff**:
```bash
# Run manual
pre-commit run --all-files
```

### Type Hints

Semua public API harus punya type hints:
```python
def fetch_synced_lyrics(
    title: str,
    lrc_path: str,
    sync_huawei: bool,
    transliterate_mode: str = "❌ 1",
    override_query: Optional[str] = None,
    translate_mode: bool = False,
) -> bool:
```

### Docstrings

Semua public functions harus punya docstring (Google style):
```python
def search_youtube_with_isrc(
    track: TrackInfo,
    max_candidates: int = 3,
    target_duration_sec: Optional[float] = None,
) -> Optional[YouTubeMatchResult]:
    """
    Cari video YouTube untuk track Spotify, prioritaskan ISRC match.

    Strategi (urutan):
        1. ISRC match: extract ISRC dari metadata top-3 YouTube candidates,
           bandingkan dengan track.isrc. Match → return.
        2. Fuzzy + duration: kalau tidak ada ISRC match, fuzzy title match
           dengan verification durasi (selisih <5 detik).
        3. Pure fuzzy: kalau tidak ada duration, fuzzy match saja (threshold 80%).

    Args:
        track:                TrackInfo dengan title, artist, isrc, duration
        max_candidates:       Jumlah top YouTube results untuk di-evaluate
        target_duration_sec:  Durasi track Spotify (untuk verification)

    Returns:
        YouTubeMatchResult kalau ada match, None kalau tidak.
    """
```

## 🔄 Workflow Kontribusi

### 1. Buat Branch

```bash
git checkout -b feature/nama-fitur
# atau
git checkout -b fix/nama-bug
```

### 2. Commit dengan Conventional Commits

```bash
git commit -m "feat(cache): tambah translation cache TTL config"
git commit -m "fix(lyrics): perbaiki transliteration skip baris dengan timestamp"
git commit -m "test(spotify): tambah test parse_spotify_url_v2 dengan mock spotipy"
git commit -m "docs(readme): update install instructions untuk Termux"
git commit -m "refactor(modes): extract helper function untuk readability"
```

Prefix yang dipakai:
- `feat:` — fitur baru
- `fix:` — bug fix
- `test:` — tambah/modifikasi tests
- `docs:` — dokumentasi
- `refactor:` — refactor tanpa perubahan behavior
- `ci:` — CI/CD config
- `chore:` — maintenance

### 3. Push & PR

```bash
git push origin feature/nama-fitur
```

Buka Pull Request di GitHub. Pastikan:
- ✅ Semua tests pass: `pytest tests/`
- ✅ Coverage tidak turun: `pytest tests/ --cov=mmpd`
- ✅ Pre-commit hooks pass: `pre-commit run --all-files`
- ✅ Tidak ada conflict dengan main

## 🐛 Bug Reports

Saat melaporkan bug, sertakan:

1. **`mmpd doctor` output** — ini akan menunjukkan environment, dependencies, network status
2. **Langkah reproduksi** — step-by-step cara trigger bug
3. **Expected vs actual behavior**
4. **Log file** — `~/.local/share/mmpd/logs/mmpd.log` (atau `$PREFIX/var/log/mmpd/mmpd.log` di Termux)
5. **Environment info**:
   - OS (Termux Android, Ubuntu, macOS, Windows)
   - Python version (`python --version`)
   - mmpd version (`mmpd --version`)

## 💡 Fitur Suggestions

Ide fitur baru → buka **GitHub Issue** dengan label `enhancement`. Diskusikan dulu sebelum implementasi besar.

## 📋 Release Process

Maintainer only:
1. Update version di `mmpd/__init__.py` dan `pyproject.toml`
2. Update `docs/CHANGELOG.md`
3. Tag release: `git tag v4.0.0 && git push --tags`
4. GitHub Actions auto-build wheel

## ❓ Pertanyaan?

- Buka **GitHub Issue** dengan label `question`
- Atau mention `@NanoMindExplorer` di issue/PR

---

Terima kasih sudah berkontribusi! 🎵
