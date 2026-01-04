"""Yap on Slack - Simulate realistic messages in Slack channels."""

import subprocess
from pathlib import Path

__version__ = "0.0.1"  # x-release-please-version


def get_git_commit() -> str | None:
    """Get current git commit hash if available."""
    try:
        repo_path = Path(__file__).parent.parent
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return None
