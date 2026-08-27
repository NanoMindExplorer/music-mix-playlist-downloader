# 🧪 Test Suite — mmpd (Music Mix Playlist Downloader)

Unit tests untuk semua modul modular di package `mmpd/`.

## 📁 Struktur Test

```
tests/
├── conftest.py                  # Shared fixtures (mock_track_info, mock_youtube_entry, dll)
├── test_utils_fs.py             # Atomic write, find_audio_files, cleanup_temp_files
├── test_utils_matching.py       # clean_search_query, fuzzy_match, normalize_title
├── test_utils_ffmpeg.py         # inject_cover_to_audio, convert_audio (mock subprocess)
├── test_config.py               # AppConfig (Termux/Linux/Windows env detection)
├── test_types.py                # TrackInfo, LyricsResult, LyricsProvider protocol
├── test_lyrics_providers.py     # LrclibProvider + SyncedLyricsProvider + LyricsChain
├── test_lyrics.py               # process_transliteration, process_translation, sync_huawei_lrc
├── test_spotify_client.py       # SpotifyClient, SpotifyTrack, _parse_spotify_url
├── test_isrc_matcher.py         # search_youtube_with_isrc, 3-tier matching strategy
└── test_concurrent.py           # run_concurrent, ThreadPoolExecutor wrapper
```

## 🚀 Cara Run Tests

### Install dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Run semua tests

```bash
# Run semua test, verbose output
pytest tests/ -v

# Run dengan coverage report
pytest tests/ --cov=mmpd --cov-report=term

# Generate HTML coverage report (buka htmlcov/index.html)
pytest tests/ --cov=mmpd --cov-report=html
```

### Run subset tests

```bash
# Hanya test utils/
pytest tests/test_utils_*.py -v

# Hanya test Spotify
pytest tests/test_spotify_client.py tests/test_isrc_matcher.py -v

# Skip slow tests
pytest tests/ -m "not slow"

# Skip integration tests (yang butuh network)
pytest tests/ -m "not integration"
```

### Run single test

```bash
# Single test function
pytest tests/test_utils_fs.py::TestAtomicWriteText::test_basic_write -v

# Single test class
pytest tests/test_lyrics_providers.py::TestLrclibProvider -v
```

## 📊 Coverage Target

| Modul | Coverage Target | Status |
|---|---|---|
| `mmpd/utils/fs.py` | 95%+ | Atomic write, file ops |
| `mmpd/utils/matching.py` | 95%+ | Pure functions, easy to test |
| `mmpd/utils/ffmpeg.py` | 80%+ | Mock subprocess |
| `mmpd/config.py` | 85%+ | Env detection |
| `mmpd/types.py` | 95%+ | Dataclasses |
| `mmpd/lyrics_providers.py` | 75%+ | Mock requests + syncedlyrics |
| `mmpd/lyrics.py` | 70%+ | Mock pykakasi/pypinyin |
| `mmpd/spotify_client.py` | 80%+ | Mock spotipy |
| `mmpd/isrc_matcher.py` | 75%+ | Mock yt_dlp |
| `mmpd/concurrent.py` | 90%+ | ThreadPoolExecutor |
| **TOTAL** | **80%+** | |

## 🎯 Test Strategy

### Mock External Dependencies

Test suite tidak hit network atau external services. Mock strategy:

| External | Mock Strategy |
|---|---|
| yt_dlp.YoutubeDL | `patch("yt_dlp.YoutubeDL")` return mock entries |
| spotipy.Spotify | `patch.dict("sys.modules", {"spotipy": mock})` |
| requests (LRCLIB API) | `patch.dict("sys.modules", {"requests": mock})` |
| pykakasi, pypinyin | `patch.dict("sys.modules", {...})` |
| subprocess.run | `patch("subprocess.run")` return MagicMock |
| shutil.which | `patch("shutil.which")` return path atau None |

### Fixtures di `conftest.py`

| Fixture | Description |
|---|---|
| `tmp_output_dir` | Temporary directory (auto-cleanup oleh pytest) |
| `tmp_lrc_file` | File .lrc kosong |
| `sample_lrc_content` | Sample LRC content dengan timestamp |
| `mock_track_info` | TrackInfo(title="Hello", artist="Adele", isrc="GBBKS1500214") |
| `mock_track_no_isrc` | TrackInfo tanpa ISRC (untuk test fuzzy matching) |
| `mock_lyrics_result_synced` | LyricsResult dengan synced lyrics |
| `mock_spotify_track` | SpotifyTrack dengan ISRC + duration |
| `mock_youtube_entry_isrc` | Mock YouTube entry dengan ISRC di external_ids |
| `mock_youtube_entries_list` | List 3 mock YouTube entries (1 dengan ISRC match) |
| `mock_termux_env` | Mock PREFIX env var (seolah di Termux) |
| `mock_linux_env` | Mock tanpa PREFIX (seolah di Linux) |
| `reset_mmpd_singletons` | Auto-reset config/logger/spotify_client antar test |

### Test Markers

```bash
# Skip slow tests
pytest tests/ -m "not slow"

# Skip integration tests (yang butuh network)
pytest tests/ -m "not integration"
```

## 🔧 CI/CD (GitHub Actions)

Workflow file: `.github/workflows/ci.yml`

Auto-run pada setiap push ke `main` atau `fase*` branch:

1. **Test matrix**: Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
2. **Build wheel**: `python -m build --wheel` + verify installable
3. **Smoke test Termux**: Run di container `python:3.14-slim` dengan FFmpeg
4. **Coverage upload** ke Codecov (Python 3.12 only)
5. **Type check** via mypy (non-blocking)
6. **Linting** via ruff (non-blocking)

Workflow status badge (tambahkan ke README.md utama):
```markdown
![CI](https://github.com/NanoMindExplorer/music-mix-playlist-downloader/actions/workflows/ci.yml/badge.svg)
```

## 🐛 Debugging Failed Tests

### Run dengan output maksimal

```bash
pytest tests/test_failed.py -v -s --tb=long
```

### Run dengan pdb debugger

```bash
pytest tests/test_failed.py --pdb
```

### Run dengan logging

```bash
pytest tests/ --log-cli-level=DEBUG
```

### Lihat slowest 10 tests

```bash
pytest tests/ --durations=10
```

## 📝 Adding New Tests

Ketika menambah modul baru di `mmpd/`, ikuti pattern ini:

1. Buat `tests/test_{module_name}.py`
2. Group tests dalam class `Test{ClassName}` untuk readability
3. Pakai fixtures dari `conftest.py` (jangan duplikasi setup)
4. Mock external dependencies (no real network/file system)
5. Test happy path + edge cases + exception handling
6. Update tabel Coverage Target di atas

### Test naming convention

```python
def test_{what}_{condition}_{expected_result}():
    ...
```

Contoh:
- `test_atomic_write_preserves_timestamps`
- `test_isrc_match_returns_true_for_exact_match`
- `test_search_returns_none_on_404`

## 🎉 Coverage Checklist

Sebelum submit PR, pastikan:

- [ ] Semua tests pass: `pytest tests/ -v`
- [ ] Coverage ≥ 80%: `pytest tests/ --cov=mmpd`
- [ ] Tidak ada warning yang blocking
- [ ] Test baru untuk fitur baru
- [ ] Mock external dependencies (no real network calls)
- [ ] Test edge cases (empty input, None, exceptions)
