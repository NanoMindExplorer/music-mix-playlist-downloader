"""
Unit tests untuk mmpd.utils.matching.

Coverage:
    - clean_search_query (strip bracket, parenthetical, promo keywords)
    - normalize_title (lowercase + collapse whitespace)
    - fuzzy_match (rapidfuzz wrapper, threshold)
    - extract_extension, strip_extension
"""

from __future__ import annotations

import pytest

from mmpd.utils.matching import (
    clean_search_query,
    extract_extension,
    fuzzy_match,
    normalize_title,
    strip_extension,
)


# ============================================================================
# clean_search_query
# ============================================================================

class TestCleanSearchQuery:
    def test_strip_square_brackets(self):
        """Test hapus [bracket]."""
        result = clean_search_query("[Rainych] JUSTadICE")
        assert result == "JUSTadICE"

    def test_strip_parentheses(self):
        """Test hapus (parenthetical)."""
        result = clean_search_query("Adele - Hello (Official Music Video)")
        # "(Official Music Video)" dihapus, "Official Music Video" juga sebagai promo keyword
        assert "Hello" in result
        assert "Adele" in result
        # "Official Music Video" harus hilang
        assert "official" not in result.lower()
        assert "music video" not in result.lower()

    def test_strip_japanese_brackets(self):
        """Test hapus 【japanese bracket】."""
        result = clean_search_query("【東方】Vocal Cover")
        assert "東方" not in result
        # "Vocal" tetap, "Cover" dihapus sebagai promo keyword
        assert "Vocal" in result
        assert "Cover" not in result

    def test_strip_multiple_brackets(self):
        """Test hapus multiple bracket types sekaligus."""
        result = clean_search_query("[Anime] Song Title (Official Lyric Video) 【HD】")
        # Hanya "Song Title" yang tersisa
        assert "Song Title" in result
        assert "Anime" not in result
        assert "Official" not in result.lower()

    def test_strip_promo_keywords(self):
        """Test hapus kata kunci promo (Official, MV, Cover, etc.)."""
        result = clean_search_query("Song Official")
        assert "Official" not in result

    def test_collapse_multiple_spaces(self):
        """Test collapse multiple spaces menjadi satu."""
        result = clean_search_query("Song    With    Extra    Spaces")
        assert result == "Song With Extra Spaces"

    def test_empty_string(self):
        """Test empty string return empty."""
        assert clean_search_query("") == ""

    def test_preserve_non_promo_words(self):
        """Test kata non-promo tetap utuh."""
        result = clean_search_query("Adele Hello")
        assert result == "Adele Hello"

    def test_case_insensitive_promo_strip(self):
        """Test promo keyword case-insensitive."""
        result_lower = clean_search_query("Song official")
        result_upper = clean_search_query("Song OFFICIAL")
        result_mixed = clean_search_query("Song OfFiCiAl")
        assert "official" not in result_lower.lower()
        assert "official" not in result_upper.lower()
        assert "official" not in result_mixed.lower()


# ============================================================================
# normalize_title
# ============================================================================

class TestNormalizeTitle:
    def test_lowercase_conversion(self):
        """Test lowercase."""
        assert normalize_title("Hello World") == "hello world"

    def test_collapse_whitespace(self):
        """Test collapse multiple spaces."""
        assert normalize_title("Hello    World") == "hello world"

    def test_trim(self):
        """Test trim leading/trailing whitespace."""
        assert normalize_title("  Hello  ") == "hello"

    def test_empty_string(self):
        """Test empty."""
        assert normalize_title("") == ""

    def test_mixed_case_with_extra_spaces(self):
        """Test kombinasi case + whitespace."""
        assert normalize_title("  ADELE   Hello  ") == "adele hello"


# ============================================================================
# fuzzy_match
# ============================================================================

class TestFuzzyMatch:
    def test_exact_match(self):
        """Test exact match return score 100."""
        result = fuzzy_match("Adele Hello", ["Adele Hello"])
        assert result == "Adele Hello"

    def test_case_insensitive_match(self):
        """Test case insensitive match."""
        result = fuzzy_match("Adele Hello", ["adele hello"])
        assert result == "adele hello"

    def test_close_match(self):
        """Test fuzzy match untuk string mirip."""
        result = fuzzy_match("Adele Hello", ["Adele - Hello"])
        # rapidfuzz score untuk "adele hello" vs "adele - hello" cukup tinggi
        assert result == "Adele - Hello"

    def test_no_match_below_threshold(self):
        """Test tidak ada match di bawah threshold."""
        result = fuzzy_match("Adele Hello", ["Completely Different Song"], threshold=80)
        assert result is None

    def test_best_match_selection(self):
        """Test pilih best match dari multiple candidates."""
        candidates = ["Random Song", "Adele Hello", "Other Adele"]
        result = fuzzy_match("Adele Hello", candidates)
        assert result == "Adele Hello"

    def test_empty_candidates(self):
        """Test empty candidates list return None."""
        result = fuzzy_match("Adele Hello", [])
        assert result is None

    def test_threshold_customization(self):
        """Test threshold custom."""
        # Score untuk "abc" vs "abd" ~ 66
        result_low = fuzzy_match("abc", ["abd"], threshold=50)
        result_high = fuzzy_match("abc", ["abd"], threshold=80)
        assert result_low == "abd"
        assert result_high is None


# ============================================================================
# extract_extension, strip_extension
# ============================================================================

class TestExtractExtension:
    def test_simple_extension(self):
        """Test simple extension extraction."""
        assert extract_extension("song.mp3") == "mp3"

    def test_uppercase_extension(self):
        """Test uppercase extension di-lowercase."""
        assert extract_extension("song.MP3") == "mp3"

    def test_multiple_dots(self):
        """Test file dengan multiple dots — ambil yang terakhir."""
        assert extract_extension("song.backup.mp3") == "mp3"

    def test_no_extension(self):
        """Test file tanpa extension return empty string."""
        assert extract_extension("song") == ""

    def test_hidden_file(self):
        """Test hidden file (.filename)."""
        # ".bashrc" → extension "bashrc" (weird tapi konsisten dengan implementasi)
        assert extract_extension(".bashrc") == "bashrc"


class TestStripExtension:
    def test_simple_strip(self):
        """Test strip extension."""
        assert strip_extension("song.mp3") == "song"

    def test_multiple_dots(self):
        """Test multiple dots — strip yang terakhir."""
        assert strip_extension("song.backup.mp3") == "song.backup"

    def test_no_extension(self):
        """Test no extension return as-is."""
        assert strip_extension("song") == "song"

    def test_uppercase_extension(self):
        """Test extension case insensitive."""
        assert strip_extension("song.MP3") == "song"
