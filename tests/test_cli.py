"""Tests for CLI commands."""

import argparse
import subprocess
from unittest.mock import patch

import pytest

from yap_on_slack import __version__, get_git_commit
from yap_on_slack.cli import cmd_version


class TestVersionCommand:
    """Test suite for version command."""

    def test_version_shows_version_number(self):
        """Test that version command displays the version number."""
        args = argparse.Namespace()

        with patch("yap_on_slack.cli.console") as mock_console:
            result = cmd_version(args)

            assert result == 0
            # Check that console.print was called
            assert mock_console.print.call_count == 2

            # First call should contain version
            first_call = str(mock_console.print.call_args_list[0])
            assert __version__ in first_call
            assert "yap-on-slack" in first_call

            # Second call should contain GitHub URL
            second_call = str(mock_console.print.call_args_list[1])
            assert "github.com/echohello-dev/yap-on-slack" in second_call

    def test_version_includes_commit_hash(self):
        """Test that version command includes commit hash when available."""
        args = argparse.Namespace()

        with (
            patch("yap_on_slack.cli.console") as mock_console,
            patch("yap_on_slack.cli.get_git_commit", return_value="abc1234"),
        ):
            result = cmd_version(args)

            assert result == 0
            first_call = str(mock_console.print.call_args_list[0])
            assert "abc1234" in first_call

    def test_version_works_without_git_commit(self):
        """Test that version command works even without git commit."""
        args = argparse.Namespace()

        with (
            patch("yap_on_slack.cli.console") as mock_console,
            patch("yap_on_slack.cli.get_git_commit", return_value=None),
        ):
            result = cmd_version(args)

            assert result == 0
            # Should still show version and GitHub URL
            assert mock_console.print.call_count == 2

    def test_version_commit_url_format(self):
        """Test that version command generates correct commit URL."""
        args = argparse.Namespace()

        with (
            patch("yap_on_slack.cli.console") as mock_console,
            patch("yap_on_slack.cli.get_git_commit", return_value="abc1234"),
        ):
            result = cmd_version(args)

            assert result == 0
            second_call = str(mock_console.print.call_args_list[1])
            assert "/tree/abc1234" in second_call


class TestGetGitCommit:
    """Test suite for get_git_commit function."""

    def test_get_git_commit_returns_hash_when_available(self):
        """Test that get_git_commit returns short hash in git repo."""
        commit = get_git_commit()

        # If we're in a git repo, should return a valid short hash
        if commit:
            assert isinstance(commit, str)
            assert len(commit) == 7  # git rev-parse --short returns 7 chars by default
            assert all(c in "0123456789abcdef" for c in commit.lower())

    def test_get_git_commit_handles_no_git_repo(self):
        """Test that get_git_commit handles non-git directories gracefully."""
        with patch("subprocess.run") as mock_run:
            # Simulate git command failure
            mock_run.side_effect = FileNotFoundError("git not found")

            commit = get_git_commit()

            assert commit is None

    def test_get_git_commit_handles_git_errors(self):
        """Test that get_git_commit handles git command errors gracefully."""
        with patch("subprocess.run") as mock_run:
            # Simulate git error
            mock_result = mock_run.return_value
            mock_result.returncode = 128  # Git error code
            mock_result.stdout = ""

            commit = get_git_commit()

            assert commit is None

    def test_get_git_commit_timeout_handling(self):
        """Test that get_git_commit handles timeout gracefully."""
        with patch("subprocess.run") as mock_run:
            # Simulate timeout
            mock_run.side_effect = subprocess.TimeoutExpired("git", 2)

            commit = get_git_commit()

            assert commit is None


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_version_flag_at_top_level(self):
        """Test that --version flag works at top level."""
        # This is an integration test that actually runs the CLI
        # We'll skip it in CI if subprocess fails
        try:
            result = subprocess.run(
                ["python", "-m", "yap_on_slack.cli", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0
            assert "yap-on-slack" in result.stdout
            assert __version__ in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("CLI subprocess test not available")

    def test_version_command(self):
        """Test that version subcommand works."""
        try:
            result = subprocess.run(
                ["python", "-m", "yap_on_slack.cli", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0
            assert "yap-on-slack" in result.stdout
            assert __version__ in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("CLI subprocess test not available")
