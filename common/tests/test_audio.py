import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.audio import generate_audio_chunk


class TestAudioFunctions:
    """Test cases for audio-related functions"""

    @patch("common.audio.last_tts_call", 0)
    @patch("time.time")
    @patch("time.sleep")
    @patch("gtts.gTTS")
    def test_generate_audio_chunk_success(self, mock_gtts, mock_sleep, mock_time):
        """Test successful audio chunk generation"""
        mock_time.return_value = 10.0  # Current time

        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            generate_audio_chunk("Test text", temp_path)

            # Verify gTTS was called correctly
            mock_gtts.assert_called_once_with(text="Test text", lang="en", slow=False)
            mock_tts_instance.save.assert_called_once_with(temp_path)

            # Check that sleep was called (rate limiting)
            mock_sleep.assert_called_once()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("common.audio.last_tts_call", 10.0)
    @patch("time.time")
    @patch("time.sleep")
    @patch("gtts.gTTS")
    @patch("pydub.AudioSegment.from_mp3")
    def test_generate_audio_chunk_with_speed_adjustment(
        self, mock_from_mp3, mock_gtts, mock_sleep, mock_time
    ):
        """Test audio chunk generation with speed adjustment"""
        from common.config import AUDIO_SPEED

        if AUDIO_SPEED == 1.0:
            pytest.skip("Audio speed is 1.0, no speed adjustment needed")

        mock_time.return_value = 10.1  # Just over wait time

        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        mock_audio_segment = MagicMock()
        mock_from_mp3.return_value = mock_audio_segment
        mock_sped_audio = MagicMock()
        mock_audio_segment.speedup.return_value = mock_sped_audio

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            generate_audio_chunk("Test text", temp_path)

            # Verify speed adjustment was applied
            mock_from_mp3.assert_called_once_with(temp_path)
            mock_audio_segment.speedup.assert_called_once_with(
                playback_speed=AUDIO_SPEED
            )
            mock_sped_audio.export.assert_called_once()

            mock_sleep.assert_not_called()  # No sleep needed

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
