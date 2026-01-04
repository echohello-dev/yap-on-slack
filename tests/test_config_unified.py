"""Tests for unified config.yaml loading and validation."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from yap_on_slack.post_messages import (AIConfigModel, CredentialsConfigModel,
                                        MessageConfigModel, UnifiedConfig,
                                        UserConfigModel, WorkspaceConfigModel,
                                        discover_config_file,
                                        load_unified_config)


class TestWorkspaceConfigModel:
    """Test workspace configuration model."""

    def test_valid_workspace_config(self):
        """Test valid workspace configuration."""
        config = WorkspaceConfigModel(
            org_url="https://test.slack.com",
            channel_id="C0123456789",
            team_id="T0123456789",
        )
        assert config.org_url == "https://test.slack.com"
        assert config.channel_id == "C0123456789"
        assert config.team_id == "T0123456789"

    def test_workspace_url_must_be_https(self):
        """Test that workspace URL must start with https://."""
        with pytest.raises(ValueError, match="must start with https://"):
            WorkspaceConfigModel(
                org_url="http://test.slack.com",
                channel_id="C0123456789",
                team_id="T0123456789",
            )


class TestCredentialsConfigModel:
    """Test credentials configuration model."""

    def test_valid_credentials(self):
        """Test valid credentials configuration."""
        config = CredentialsConfigModel(
            xoxc_token="xoxc-test-token",
            xoxd_token="xoxd-test-token",
            cookies="d-s=1234567890",
        )
        assert config.xoxc_token == "xoxc-test-token"
        assert config.xoxd_token == "xoxd-test-token"
        assert config.cookies == "d-s=1234567890"

    def test_optional_credentials(self):
        """Test that all credentials are optional."""
        config = CredentialsConfigModel()
        assert config.xoxc_token is None
        assert config.xoxd_token is None
        assert config.cookies is None


class TestUserConfigModel:
    """Test user configuration model."""

    def test_valid_user_config(self):
        """Test valid user configuration."""
        config = UserConfigModel(
            name="alice",
            xoxc_token="xoxc-alice-token",
            xoxd_token="xoxd-alice-token",
        )
        assert config.name == "alice"
        assert config.xoxc_token == "xoxc-alice-token"
        assert config.xoxd_token == "xoxd-alice-token"

    def test_user_name_cannot_be_empty(self):
        """Test that user name cannot be empty."""
        with pytest.raises(ValueError, match="User name cannot be empty"):
            UserConfigModel(
                name="",
                xoxc_token="xoxc-test",
                xoxd_token="xoxd-test",
            )

    def test_user_name_cannot_be_whitespace(self):
        """Test that user name cannot be only whitespace."""
        with pytest.raises(ValueError, match="User name cannot be empty"):
            UserConfigModel(
                name="   ",
                xoxc_token="xoxc-test",
                xoxd_token="xoxd-test",
            )


class TestMessageConfigModel:
    """Test message configuration model."""

    def test_valid_message_config(self):
        """Test valid message configuration."""
        config = MessageConfigModel(
            text="Test message",
            user="alice",
            replies=["Reply 1", "Reply 2"],
            reactions=["wave", "rocket"],
        )
        assert config.text == "Test message"
        assert config.user == "alice"
        assert len(config.replies) == 2
        assert len(config.reactions) == 2

    def test_message_defaults(self):
        """Test message configuration defaults."""
        config = MessageConfigModel(text="Test message")
        assert config.user is None
        assert config.replies == []
        assert config.reactions == []


class TestAIConfigModel:
    """Test AI configuration model."""

    def test_valid_ai_config(self):
        """Test valid AI configuration."""
        config = AIConfigModel(
            enabled=True,
            model="google/gemini-2.5-flash",
            api_key="sk-test-key",
            temperature=0.8,
            max_tokens=5000,
        )
        assert config.enabled is True
        assert config.model == "google/gemini-2.5-flash"
        assert config.api_key == "sk-test-key"
        assert config.temperature == 0.8
        assert config.max_tokens == 5000

    def test_ai_config_defaults(self):
        """Test AI configuration defaults."""
        config = AIConfigModel()
        assert config.enabled is False
        assert config.model == "openrouter/auto"
        assert config.api_key is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.system_prompt is None


class TestUnifiedConfig:
    """Test unified configuration model."""

    def test_valid_unified_config(self):
        """Test valid unified configuration."""
        config = UnifiedConfig(
            workspace=WorkspaceConfigModel(
                org_url="https://test.slack.com",
                channel_id="C0123456789",
                team_id="T0123456789",
            ),
            credentials=CredentialsConfigModel(
                xoxc_token="xoxc-test",
                xoxd_token="xoxd-test",
            ),
            user_strategy="round_robin",
            users=[
                UserConfigModel(
                    name="alice",
                    xoxc_token="xoxc-alice",
                    xoxd_token="xoxd-alice",
                )
            ],
            messages=[MessageConfigModel(text="Test message")],
            ai=AIConfigModel(enabled=True),
        )
        assert config.workspace.org_url == "https://test.slack.com"
        assert config.credentials.xoxc_token == "xoxc-test"
        assert config.user_strategy == "round_robin"
        assert len(config.users) == 1
        assert len(config.messages) == 1
        assert config.ai.enabled is True

    def test_unified_config_minimal(self):
        """Test minimal unified configuration."""
        config = UnifiedConfig(
            workspace=WorkspaceConfigModel(
                org_url="https://test.slack.com",
                channel_id="C0123456789",
                team_id="T0123456789",
            )
        )
        assert config.credentials is None
        assert config.user_strategy == "round_robin"
        assert config.users == []
        assert config.messages == []
        assert config.ai is None


class TestDiscoverConfigFile:
    """Test config file discovery."""

    def test_discover_explicit_path(self):
        """Test discovery with explicit path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
            f.write("workspace:\n  org_url: https://test.slack.com\n")

        try:
            discovered = discover_config_file(config_path)
            assert discovered == config_path
        finally:
            config_path.unlink()

    def test_discover_explicit_path_not_found(self):
        """Test discovery with explicit path that doesn't exist."""
        with pytest.raises(ValueError, match="Config file not found"):
            discover_config_file(Path("/nonexistent/config.yaml"))

    def test_discover_cwd_yos_config(self):
        """Test discovery of .yos.yaml in CWD (highest priority)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            yos_config_file = tmpdir_path / ".yos.yaml"
            yos_config_file.write_text("workspace:\n  org_url: https://test.slack.com\n")

            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                discovered = discover_config_file()
                assert discovered == yos_config_file

    def test_discover_cwd_config_second_priority(self):
        """Test discovery of config.yaml in CWD (second priority)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text("workspace:\n  org_url: https://test.slack.com\n")

            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                discovered = discover_config_file()
                assert discovered == config_file

    def test_discover_home_config(self):
        """Test discovery of config.yaml in ~/.config/yap-on-slack/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            home_config_dir = tmpdir_path / ".config" / "yap-on-slack"
            home_config_dir.mkdir(parents=True)
            config_file = home_config_dir / "config.yaml"
            config_file.write_text("workspace:\n  org_url: https://test.slack.com\n")

            # Mock both CWD (no config) and Path.home() (has config)
            with patch("pathlib.Path.cwd", return_value=Path("/tmp")):
                with patch("pathlib.Path.home", return_value=tmpdir_path):
                    discovered = discover_config_file()
                    assert discovered == config_file

    def test_discover_no_config(self):
        """Test discovery when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                with patch("pathlib.Path.home", return_value=tmpdir_path):
                    discovered = discover_config_file()
                    assert discovered is None


class TestLoadUnifiedConfig:
    """Test unified config loading."""

    def test_load_config_with_all_fields(self):
        """Test loading config with all fields populated."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-test-token
  xoxd_token: xoxd-test-token
  cookies: "d-s=1234567890"

user_strategy: random

users:
  - name: alice
    xoxc_token: xoxc-alice-token
    xoxd_token: xoxd-alice-token
  - name: bob
    xoxc_token: xoxc-bob-token
    xoxd_token: xoxd-bob-token

messages:
  - text: "Test message"
    replies:
      - "Reply 1"
    reactions:
      - wave

ai:
  enabled: true
  model: google/gemini-2.5-flash
  api_key: sk-or-v1-test-key
  temperature: 0.8
  max_tokens: 5000
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            # Clear environment variables to ensure clean test
            with patch.dict("os.environ", {}, clear=True):
                app_config, env = load_unified_config(config_file)

                # Verify workspace
                assert app_config.workspace.SLACK_ORG_URL == "https://test.slack.com"
                assert app_config.workspace.SLACK_CHANNEL_ID == "C0123456789"
                assert app_config.workspace.SLACK_TEAM_ID == "T0123456789"

                # Verify users (default + 2 additional = 3 total)
                assert len(app_config.users) == 3
                assert app_config.users[0].name == "default"
                assert app_config.users[1].name == "alice"
                assert app_config.users[2].name == "bob"

                # Verify strategy
                assert app_config.strategy == "random"

    def test_load_config_minimal(self):
        """Test loading minimal config with just workspace and credentials."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-test-token
  xoxd_token: xoxd-test-token
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            # Clear environment variables to ensure clean test
            with patch.dict("os.environ", {}, clear=True):
                app_config, env = load_unified_config(config_file)

                # Verify workspace
                assert app_config.workspace.SLACK_ORG_URL == "https://test.slack.com"

                # Verify single default user
                assert len(app_config.users) == 1
                assert app_config.users[0].name == "default"
                assert app_config.users[0].SLACK_XOXC_TOKEN == "xoxc-test-token"

                # Verify defaults
                assert app_config.strategy == "round_robin"

    def test_load_config_with_env_override(self):
        """Test that environment variables override config file."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-config-token
  xoxd_token: xoxd-config-token
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            # Set environment variables
            with patch.dict(
                "os.environ",
                {
                    "SLACK_XOXC_TOKEN": "xoxc-env-token",
                    "SLACK_XOXD_TOKEN": "xoxd-env-token",
                    "SLACK_ORG_URL": "https://env.slack.com",
                },
            ):
                app_config, env = load_unified_config(config_file)

                # Verify env vars override config
                assert app_config.workspace.SLACK_ORG_URL == "https://env.slack.com"
                assert app_config.users[0].SLACK_XOXC_TOKEN == "xoxc-env-token"
                assert app_config.users[0].SLACK_XOXD_TOKEN == "xoxd-env-token"

    def test_load_config_missing_workspace(self):
        """Test that missing workspace configuration raises error."""
        config_content = """
credentials:
  xoxc_token: xoxc-test-token
  xoxd_token: xoxd-test-token
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            with pytest.raises(ValueError, match="Invalid config.yaml"):
                load_unified_config(config_file)

    def test_load_config_missing_credentials(self):
        """Test that missing credentials raises error."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: C0123456789
  team_id: T0123456789
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            # Clear environment variables to ensure credentials are truly missing
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(ValueError, match="Missing required credentials"):
                    load_unified_config(config_file)

    def test_load_config_invalid_yaml(self):
        """Test that invalid YAML raises error."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: [invalid yaml syntax
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            with pytest.raises(ValueError, match="Invalid config.yaml"):
                load_unified_config(config_file)


class TestGitHubConfigModel:
    """Test GitHub configuration model."""

    def test_valid_github_config(self):
        """Test valid GitHub configuration."""
        from yap_on_slack.post_messages import GitHubConfigModel

        config = GitHubConfigModel(
            enabled=True,
            token="ghp_test_token",
            limit=10,
            include_commits=True,
            include_prs=True,
            include_issues=False,
        )
        assert config.enabled is True
        assert config.token == "ghp_test_token"
        assert config.limit == 10
        assert config.include_commits is True
        assert config.include_prs is True
        assert config.include_issues is False

    def test_github_config_defaults(self):
        """Test GitHub configuration defaults."""
        from yap_on_slack.post_messages import GitHubConfigModel

        config = GitHubConfigModel()
        assert config.enabled is True
        assert config.token is None
        assert config.limit == 5
        assert config.include_commits is True
        assert config.include_prs is True
        assert config.include_issues is True

    def test_ai_config_with_github(self):
        """Test AI configuration with nested GitHub config."""
        from yap_on_slack.post_messages import GitHubConfigModel

        github_config = GitHubConfigModel(enabled=True, limit=10)
        ai_config = AIConfigModel(
            enabled=True,
            model="openrouter/auto",
            github=github_config,
        )
        assert ai_config.github is not None
        assert ai_config.github.enabled is True
        assert ai_config.github.limit == 10

    def test_unified_config_with_github(self):
        """Test unified configuration with GitHub config."""

        config_data = {
            "workspace": {
                "org_url": "https://test.slack.com",
                "channel_id": "C123",
                "team_id": "T123",
            },
            "credentials": {
                "xoxc_token": "xoxc_test",
                "xoxd_token": "xoxd_test",
            },
            "ai": {
                "enabled": True,
                "github": {
                    "enabled": True,
                    "token": "ghp_test",
                    "limit": 10,
                },
            },
            "github": {
                "enabled": True,
                "limit": 5,
            },
        }

        config = UnifiedConfig(**config_data)
        assert config.ai.github is not None
        assert config.ai.github.enabled is True
        assert config.ai.github.token == "ghp_test"
        assert config.ai.github.limit == 10
        assert config.github is not None
        assert config.github.enabled is True
        assert config.github.limit == 5

    def test_load_config_with_github(self):
        """Test loading configuration with GitHub settings."""
        config_content = """
workspace:
  org_url: https://test.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-test-token
  xoxd_token: xoxd-test-token

ai:
  enabled: true
  model: openrouter/auto
  github:
    enabled: true
    token: ghp_test_token
    limit: 10
    include_commits: true
    include_prs: true
    include_issues: false

github:
  enabled: true
  limit: 5
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text(config_content)

            app_config, env = load_unified_config(config_file)

            # Verify GitHub config was loaded
            assert app_config is not None
