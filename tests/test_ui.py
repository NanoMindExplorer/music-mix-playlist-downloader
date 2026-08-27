"""
Unit tests untuk mmpd.ui — banner, theme, helpers.

Strategy:
    - Test print_banner() tidak raise
    - Test ask_* helpers dengan mock questionary
    - Test konstanta UI (MODE_CHOICES, LYRICS_MODE_CHOICES, dll)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Constants
# ============================================================================

class TestUIConstants:
    def test_mode_choices_has_5_modes(self):
        """Test MODE_CHOICES punya 5 modes."""
        from mmpd.ui import MODE_CHOICES
        assert len(MODE_CHOICES) == 5

    def test_mode_choices_values_1_to_5(self):
        """Test MODE_CHOICES values 1-5."""
        from mmpd.ui import MODE_CHOICES
        values = set(MODE_CHOICES.values())
        assert values == {1, 2, 3, 4, 5}

    def test_lyrics_mode_choices_has_4(self):
        """Test LYRICS_MODE_CHOICES punya 4 pilihan."""
        from mmpd.ui import LYRICS_MODE_CHOICES
        assert len(LYRICS_MODE_CHOICES) == 4

    def test_transliterate_choices_has_4(self):
        """Test TRANSLITERATE_CHOICES punya 4 pilihan."""
        from mmpd.ui import TRANSLITERATE_CHOICES
        assert len(TRANSLITERATE_CHOICES) == 4

    def test_format_options_has_4(self):
        """Test FORMAT_OPTIONS punya 4 format."""
        from mmpd.ui import FORMAT_OPTIONS
        assert len(FORMAT_OPTIONS) == 4
        # Check codecs
        codecs = {fmt["codec"] for fmt in FORMAT_OPTIONS.values()}
        assert "mp3" in codecs
        assert "flac" in codecs
        assert "wav" in codecs
        assert "best" in codecs

    def test_retrofit_target_choices_has_3(self):
        """Test RETROFIT_TARGET_CHOICES punya 3 pilihan."""
        from mmpd.ui import RETROFIT_TARGET_CHOICES
        assert len(RETROFIT_TARGET_CHOICES) == 3


# ============================================================================
# custom_theme
# ============================================================================

class TestCustomTheme:
    def test_theme_is_questionary_style(self):
        """Test custom_theme adalah instance questionary.Style."""
        from mmpd.ui import custom_theme
        import questionary
        assert isinstance(custom_theme, questionary.Style)

    def test_theme_has_qmark_rule(self):
        """Test theme punya qmark rule."""
        from mmpd.ui import custom_theme
        # questionary.Style pakai style_rules (list of tuples)
        rules = custom_theme.style_rules
        assert any(rule[0] == "qmark" for rule in rules)

    def test_theme_has_question_rule(self):
        """Test theme punya question rule."""
        from mmpd.ui import custom_theme
        rules = custom_theme.style_rules
        assert any(rule[0] == "question" for rule in rules)


# ============================================================================
# print_banner
# ============================================================================

class TestPrintBanner:
    def test_print_banner_does_not_raise(self):
        """Test print_banner tidak raise."""
        from mmpd.ui import print_banner
        # Should not raise
        print_banner()

    def test_print_banner_clears_console(self):
        """Test print_banner call console.clear()."""
        from mmpd.ui import print_banner, console
        with patch.object(console, "clear") as mock_clear:
            print_banner()
        mock_clear.assert_called_once()


# ============================================================================
# ask_text helper
# ============================================================================

class TestAskText:
    def test_ask_text_returns_string(self):
        """Test ask_text return string dari questionary."""
        from mmpd.ui import ask_text
        with patch("mmpd.ui.questionary.text") as mock_text:
            mock_text.return_value.ask.return_value = "user input"
            result = ask_text("Enter something:", default="default")
        assert result == "user input"

    def test_ask_text_with_default(self):
        """Test ask_text dengan default value."""
        from mmpd.ui import ask_text
        with patch("mmpd.ui.questionary.text") as mock_text:
            mock_instance = mock_text.return_value
            mock_instance.ask.return_value = "input"
            ask_text("Prompt:", default="my_default")
            # Verify questionary.text dipanggil dengan default
            mock_text.assert_called_with("Prompt:", default="my_default", style=mock_text.call_args[1]["style"])


# ============================================================================
# ask_select helper
# ============================================================================

class TestAskSelect:
    def test_ask_select_returns_choice(self):
        """Test ask_select return pilihan user."""
        from mmpd.ui import ask_select
        with patch("mmpd.ui.questionary.select") as mock_select:
            mock_instance = mock_select.return_value
            mock_instance.ask.return_value = "Option B"
            result = ask_select("Pick one:", ["Option A", "Option B"])
        assert result == "Option B"

    def test_ask_select_passes_choices(self):
        """Test ask_select pass choices ke questionary."""
        from mmpd.ui import ask_select
        choices = ["A", "B", "C"]
        with patch("mmpd.ui.questionary.select") as mock_select:
            mock_select.return_value.ask.return_value = "A"
            ask_select("Pick:", choices)
            call_kwargs = mock_select.call_args[1]
            assert call_kwargs["choices"] == choices


# ============================================================================
# ask_confirm helper
# ============================================================================

class TestAskConfirm:
    def test_ask_confirm_true(self):
        """Test ask_confirm return True."""
        from mmpd.ui import ask_confirm
        with patch("mmpd.ui.questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            result = ask_confirm("Are you sure?", default=False)
        assert result is True

    def test_ask_confirm_false(self):
        """Test ask_confirm return False."""
        from mmpd.ui import ask_confirm
        with patch("mmpd.ui.questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            result = ask_confirm("Continue?", default=True)
        assert result is False

    def test_ask_confirm_default_passed(self):
        """Test ask_confirm pass default ke questionary."""
        from mmpd.ui import ask_confirm
        with patch("mmpd.ui.questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            ask_confirm("OK?", default=True)
            call_kwargs = mock_confirm.call_args[1]
            assert call_kwargs["default"] is True


# ============================================================================
# ask_int helper
# ============================================================================

class TestAskInt:
    def test_ask_int_valid_input(self):
        """Test ask_int dengan input valid."""
        from mmpd.ui import ask_int
        with patch("mmpd.ui.questionary.text") as mock_text:
            mock_text.return_value.ask.return_value = "42"
            result = ask_int("Enter number:", min_value=1)
        assert result == 42

    def test_ask_int_invalid_then_valid(self):
        """Test ask_int dengan invalid input lalu valid."""
        from mmpd.ui import ask_int
        with patch("mmpd.ui.questionary.text") as mock_text:
            # First call return invalid, second return valid
            mock_text.return_value.ask.side_effect = ["not_a_number", "10"]
            result = ask_int("Enter number:", min_value=1)
        assert result == 10

    def test_ask_int_empty_returns_none(self):
        """Test ask_int dengan empty input return None."""
        from mmpd.ui import ask_int
        with patch("mmpd.ui.questionary.text") as mock_text:
            mock_text.return_value.ask.return_value = ""
            result = ask_int("Enter number:", min_value=1)
        assert result is None

    def test_ask_int_below_min_value_retries(self):
        """Test ask_int dengan value < min_value retry."""
        from mmpd.ui import ask_int
        with patch("mmpd.ui.questionary.text") as mock_text:
            mock_text.return_value.ask.side_effect = ["0", "5"]
            result = ask_int("Enter number:", min_value=1)
        assert result == 5


# ============================================================================
# console singleton
# ============================================================================

class TestConsole:
    def test_console_is_rich_console(self):
        """Test console adalah instance rich Console."""
        from mmpd.ui import console
        from rich.console import Console
        assert isinstance(console, Console)

    def test_console_print_does_not_raise(self):
        """Test console.print tidak raise."""
        from mmpd.ui import console
        console.print("test message")
        # Should not raise
