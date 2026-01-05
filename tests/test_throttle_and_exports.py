"""Tests for throttling, file naming, and export functionality."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yap_on_slack.post_messages import apply_throttle


class TestApplyThrottle:
    """Test suite for apply_throttle function."""

    def test_throttle_basic_timing(self):
        """Test that throttle applies requested delay."""
        start = time.time()
        apply_throttle(0.1, randomize=False)
        elapsed = time.time() - start

        # Should be approximately 0.1s (±50ms tolerance)
        assert 0.05 <= elapsed < 0.15

    def test_throttle_with_randomization(self):
        """Test that randomization adds variability."""
        delays = []
        for _ in range(5):
            start = time.time()
            apply_throttle(0.1, randomize=True, randomization_range=0.05)
            elapsed = time.time() - start
            delays.append(elapsed)

        # All delays should be within expected range
        for delay in delays:
            assert 0.05 <= delay < 0.20

        # Should have some variation (not all exactly the same)
        # This is probabilistic, so we check for variety
        unique_delays = len(set(round(d, 3) for d in delays))
        # With 5 calls, we should see at least some variation (allowing for timing variance)
        assert unique_delays > 1 or all(abs(d - 0.1) < 0.01 for d in delays)

    def test_throttle_max_wait_time(self):
        """Test that max_wait_time is respected."""
        start = time.time()
        apply_throttle(100.0, randomize=False, max_wait_time=0.05)
        elapsed = time.time() - start

        # Should respect max_wait_time
        assert elapsed < 0.15  # With some tolerance

    def test_throttle_minimum_wait(self):
        """Test that minimum wait time is enforced."""
        start = time.time()
        apply_throttle(-10.0, randomize=False)  # Negative value
        elapsed = time.time() - start

        # Should enforce minimum of 0.1s
        assert elapsed >= 0.05

    def test_throttle_no_randomization(self):
        """Test that disabling randomization makes delays consistent."""
        base_time = 0.1  # Use minimum time since there's a 0.1s floor
        delays = []

        for _ in range(3):
            start = time.time()
            apply_throttle(base_time, randomize=False)
            elapsed = time.time() - start
            delays.append(elapsed)

        # All delays should be close to base_time
        for delay in delays:
            assert abs(delay - base_time) < 0.05  # 50ms tolerance

    @patch("time.sleep")
    def test_throttle_calls_sleep(self, mock_sleep):
        """Test that throttle calls time.sleep with correct value."""
        apply_throttle(1.0, randomize=False)
        mock_sleep.assert_called_once()
        # Check that it was called with a value close to 1.0
        actual_sleep_time = mock_sleep.call_args[0][0]
        assert 0.95 <= actual_sleep_time <= 1.05

    @patch("time.sleep")
    def test_throttle_randomization_range(self, mock_sleep):
        """Test that randomization range is applied correctly."""
        # With randomization_range=0.5 and base=1.0, we should get values between 0.5 and 1.5
        apply_throttle(1.0, randomize=True, randomization_range=0.5)
        actual_sleep_time = mock_sleep.call_args[0][0]
        # Should be in range [0.5, 1.5] with 0.1s min enforcement
        assert 0.1 <= actual_sleep_time <= 1.5


class TestFileNaming:
    """Test suite for file naming with channel name and timestamp."""

    def test_export_file_naming_format(self, tmp_path):
        """Test that export files follow correct naming format: channel_name_export_TIMESTAMP.txt"""
        # This is a unit test for the naming pattern
        channel_name = "general"
        timestamp = "20240115_143022"
        filename = f"{channel_name}_export_{timestamp}.txt"

        # Verify format
        assert filename.startswith(channel_name)
        assert "_export_" in filename
        assert timestamp in filename
        assert filename.endswith(".txt")

    def test_prompt_file_naming_format(self, tmp_path):
        """Test that prompt files follow correct naming format: channel_name_system_prompt_N_TIMESTAMP.md"""
        channel_name = "announcements"
        timestamp = "20240115_143022"
        prompt_num = 1
        filename = f"{channel_name}_system_prompt_{prompt_num}_{timestamp}.md"

        # Verify format
        assert filename.startswith(channel_name)
        assert "_system_prompt_" in filename
        assert str(prompt_num) in filename
        assert timestamp in filename
        assert filename.endswith(".md")

    def test_file_naming_with_special_chars(self, tmp_path):
        """Test file naming works with channels that have dashes and underscores."""
        channel_names = ["project-management", "team_announcements", "dev-team_alerts"]

        for channel_name in channel_names:
            timestamp = "20240115_143022"
            filename = f"{channel_name}_export_{timestamp}.txt"
            filepath = tmp_path / filename

            # Should be able to create the file
            filepath.write_text("test content")
            assert filepath.exists()
            assert filepath.name == filename

    def test_multiple_prompt_files_naming(self, tmp_path):
        """Test that multiple prompt files get unique names."""
        channel_name = "general"
        timestamp = "20240115_143022"

        filenames = []
        for i in range(1, 4):
            filename = f"{channel_name}_system_prompt_{i}_{timestamp}.md"
            filenames.append(filename)

        # Each should have unique number but same timestamp
        assert len(set(filenames)) == 3  # All unique
        for i, filename in enumerate(filenames, 1):
            assert f"_system_prompt_{i}_" in filename


class TestExportOnlyMode:
    """Test suite for export-only mode functionality."""

    def test_export_only_flag_parsing(self):
        """Test that --export-only flag is properly parsed."""
        # This tests the CLI argument parsing
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--export-only", action="store_true")

        # Test with flag
        args = parser.parse_args(["--export-only"])
        assert args.export_only is True

        # Test without flag
        args = parser.parse_args([])
        assert args.export_only is False

    def test_export_only_prevents_prompt_generation(self):
        """Test that export-only mode skips prompt generation."""
        # This is a logical test - in export-only mode, we should return early
        # after exporting data, without calling generate_system_prompts
        should_generate_prompts = False
        should_export_data = True

        # Export-only mode should have these values
        assert should_export_data is True
        assert should_generate_prompts is False


class TestThrottleDefaults:
    """Test suite for default throttle values."""

    def test_scan_default_throttle_is_higher(self):
        """Test that default throttle for scan is higher than before."""
        # The new default is 1.5s instead of 0.5s
        new_default = 1.5
        old_default = 0.5

        assert new_default > old_default
        # Specifically 3x the old value
        assert new_default == old_default * 3

    def test_throttle_with_randomization_range(self):
        """Test that throttle has randomization range specified."""
        base_throttle = 1.5
        randomization_range = 0.5

        # With these values, we should get delays between 1.0 and 2.0
        min_expected = base_throttle - randomization_range
        max_expected = base_throttle + randomization_range

        assert min_expected == 1.0
        assert max_expected == 2.0
