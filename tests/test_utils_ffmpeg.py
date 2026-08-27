"""
Unit tests untuk mmpd.utils.ffmpeg.

Strategy:
    - Mock subprocess.run untuk test inject_cover_to_audio tanpa benar-benar
      panggil FFmpeg (cepat, no external dependency)
    - Mock shutil.which untuk test check_ffmpeg_available
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mmpd.utils.ffmpeg import (
    check_ffmpeg_available,
    convert_audio,
    inject_cover_to_audio,
)


class TestCheckFfmpegAvailable:
    def test_ffmpeg_found(self):
        """Test ffmpeg available di PATH."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert check_ffmpeg_available() is True

    def test_ffmpeg_not_found(self):
        """Test ffmpeg tidak ada di PATH."""
        with patch("shutil.which", return_value=None):
            assert check_ffmpeg_available() is False


# ============================================================================
# inject_cover_to_audio
# ============================================================================

class TestInjectCoverToAudio:
    def test_mp3_inject_success(self, tmp_path):
        """Test inject cover ke MP3 sukses."""
        audio = tmp_path / "song.mp3"
        audio.write_bytes(b"fake_mp3_data")
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"fake_jpeg_data")
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="mp3",
            )

        assert result is True
        mock_run.assert_called_once()
        # Verify command structure
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd
        assert "-id3v2_version" in cmd
        # Index of "-id3v2_version" + 1 should be "3"
        idx = cmd.index("-id3v2_version")
        assert cmd[idx + 1] == "3"

    def test_flac_inject_success(self, tmp_path):
        """Test inject cover ke FLAC sukses."""
        audio = tmp_path / "song.flac"
        audio.write_bytes(b"fake_flac_data")
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"fake_jpeg")
        output = tmp_path / "output.flac"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="flac",
            )

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "-disposition:v" in cmd
        assert "attached_pic" in cmd

    def test_unsupported_format(self, tmp_path):
        """Test format tidak didukung return False."""
        audio = tmp_path / "song.wav"
        audio.touch()
        cover = tmp_path / "cover.jpg"
        cover.touch()
        output = tmp_path / "output.wav"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="wav",  # Not supported for cover injection
            )
        assert result is False

    def test_ffmpeg_not_installed(self, tmp_path):
        """Test FFmpeg tidak terinstal return False."""
        audio = tmp_path / "song.mp3"
        audio.touch()
        cover = tmp_path / "cover.jpg"
        cover.touch()
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value=None):
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="mp3",
            )
        assert result is False

    def test_ffmpeg_called_process_error(self, tmp_path):
        """Test FFmpeg exit non-zero (CalledProcessError) return False."""
        audio = tmp_path / "song.mp3"
        audio.touch()
        cover = tmp_path / "cover.jpg"
        cover.touch()
        output = tmp_path / "output.mp3"

        error = subprocess.CalledProcessError(returncode=1, cmd=["ffmpeg"])
        error.stderr = "FFmpeg error: invalid input"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run", side_effect=error):
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="mp3",
            )
        assert result is False

    def test_ffmpeg_binary_not_found_exception(self, tmp_path):
        """Test FileNotFoundError (ffmpeg missing saat eksekusi) return False."""
        audio = tmp_path / "song.mp3"
        audio.touch()
        cover = tmp_path / "cover.jpg"
        cover.touch()
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            result = inject_cover_to_audio(
                audio_path=str(audio),
                cover_path=str(cover),
                output_path=str(output),
                audio_format="mp3",
            )
        assert result is False

    def test_no_shell_injection_via_filename(self, tmp_path):
        """SECURITY TEST: filename dengan karakter berbahaya tidak dieksekusi sebagai shell."""
        # Filename dengan shell metacharacters
        evil_audio = tmp_path / 'song"; rm -rf ~; echo ".mp3'
        evil_audio.write_bytes(b"data")
        evil_cover = tmp_path / 'cover.jpg'
        evil_cover.write_bytes(b"cover")
        evil_output = tmp_path / 'output"; rm -rf ~; echo ".mp3'

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            inject_cover_to_audio(
                audio_path=str(evil_audio),
                cover_path=str(evil_cover),
                output_path=str(evil_output),
                audio_format="mp3",
            )

        # Verify: subprocess.run dipanggil dengan LIST argumen, BUKAN string command
        # (list argumen aman dari shell injection)
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert isinstance(cmd, list), "subprocess.run harus pakai list argumen, bukan string"
        # Evil filename harus ada sebagai element list (bukan diinterpretasi shell)
        assert any('rm -rf' in str(arg) for arg in cmd), "Filename harus dilewatkan apa adanya"


# ============================================================================
# convert_audio
# ============================================================================

class TestConvertAudio:
    def test_convert_success(self, tmp_path):
        """Test konversi audio sukses."""
        input_file = tmp_path / "input.wav"
        input_file.touch()
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            result = convert_audio(
                input_path=str(input_file),
                output_path=str(output),
                codec="mp3",
                bitrate="320k",
            )

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "-b:a" in cmd
        idx = cmd.index("-b:a")
        assert cmd[idx + 1] == "320k"

    def test_convert_no_bitrate(self, tmp_path):
        """Test konversi tanpa bitrate specified."""
        input_file = tmp_path / "input.wav"
        input_file.touch()
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            result = convert_audio(
                input_path=str(input_file),
                output_path=str(output),
                codec="mp3",
            )

        assert result is True
        cmd = mock_run.call_args[0][0]
        # Tidak ada -b:a kalau bitrate None
        assert "-b:a" not in cmd

    def test_convert_ffmpeg_not_installed(self, tmp_path):
        """Test convert tanpa FFmpeg."""
        input_file = tmp_path / "input.wav"
        input_file.touch()
        output = tmp_path / "output.mp3"

        with patch("shutil.which", return_value=None):
            result = convert_audio(
                input_path=str(input_file),
                output_path=str(output),
                codec="mp3",
            )
        assert result is False

    def test_convert_codec_best(self, tmp_path):
        """Test codec 'best' pakai copy."""
        input_file = tmp_path / "input.m4a"
        input_file.touch()
        output = tmp_path / "output.m4a"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            convert_audio(
                input_path=str(input_file),
                output_path=str(output),
                codec="best",
            )

        cmd = mock_run.call_args[0][0]
        # codec "best" → acodec "copy"
        idx = cmd.index("-acodec")
        assert cmd[idx + 1] == "copy"
