#!/usr/bin/env bash
# fix-test-instrumental.sh - Fix tests yang gagal karena instrumental filter
# Repo  : https://github.com/NanoMindExplorer/music-mix-playlist-downloader
#
# Bug: GitHub Actions CI merah (Python 3.10-3.14) karena test_spotify.py
#      masih expect output lama (tanpa filter instrumental).
#
# Fix: Update assertions di test_spotify.py untuk match output baru.
#
# Cara pakai:
#   nano fix-test-instrumental.sh
#   (paste, save: Ctrl+O Enter Ctrl+X)
#   bash fix-test-instrumental.sh

set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
success() { echo -e "${GREEN}[OK]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()    { echo -e "\n${CYAN}${BOLD}=== $* ===${NC}"; }

REPO_DIR="${1:-$HOME/music-mix-playlist-downloader}"

step "1/3 - Cek repo"
[ ! -d "$REPO_DIR/.git" ] && { error "Repo tidak ditemukan: $REPO_DIR"; exit 1; }
success "Repo: $REPO_DIR"
cd "$REPO_DIR"

step "2/3 - Update + apply fix"
git fetch origin && git checkout main && git pull origin main 2>&1 | tail -3

BRANCH="fix-test-instrumental"
git branch -D "$BRANCH" 2>/dev/null; git checkout -b "$BRANCH"
git config user.email "patch@local" 2>/dev/null; git config user.name "Test Fix" 2>/dev/null

# Fix test_spotify.py
python3 << 'PATCH'
FILE = "tests/test_spotify.py"
content = open(FILE, encoding="utf-8").read()

old = '''    def test_basic_query(self):
        """Test basic ytsearch query."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Adele Hello", limit=1)
        assert result == "ytsearch1:Adele Hello"

    def test_query_with_limit_3(self):
        """Test query dengan limit 3."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Test Song", limit=3)
        assert result == "ytsearch3:Test Song"'''

new = '''    def test_basic_query(self):
        """Test basic ytsearch query dengan instrumental filter."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Adele Hello", limit=1)
        assert result.startswith("ytsearch1:Adele Hello")
        assert "-instrumental" in result
        assert "-karaoke" in result

    def test_query_with_limit_3(self):
        """Test query dengan limit 3."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Test Song", limit=3)
        assert result.startswith("ytsearch3:Test Song")
        assert "-instrumental" in result'''

if old in content:
    content = content.replace(old, new, 1)
    open(FILE, "w", encoding="utf-8").write(content)
    print("OK: test_spotify.py patched")
else:
    print("SKIP: sudah di-fix atau pattern tidak match")
PATCH

# Verify
python3 -m pytest tests/test_spotify.py --tb=short 2>&1 | tail -5

step "3/3 - Commit & push"
git add tests/test_spotify.py
git commit -m "fix(test): update test_spotify.py untuk instrumental filter

Tests gagal karena expect output lama (tanpa filter instrumental).
Fix: update assertions untuk match output baru yang mengandung
-instrumental -karaoke exclusion filter." > /dev/null

success "✅ Commit done di branch: $BRANCH"

echo ""
echo -e "${GREEN}${BOLD}+================================================================+${NC}"
echo -e "${GREEN}${BOLD}|    TEST FIX BERHASIL!                                         |${NC}"
echo -e "${GREEN}${BOLD}+================================================================+${NC}"
echo ""
echo -e "${CYAN}Push + merge:${NC}"
echo -e "  ${GREEN}git push -u origin $BRANCH${NC}"
echo -e "  ${GREEN}git checkout main && git merge $BRANCH && git push origin main${NC}"
echo ""
echo -e "\033[1;33mSetelah merge, GitHub Actions akan HIJAU lagi!\033[0m"
