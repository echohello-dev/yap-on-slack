"""Integration tests for the full message posting flow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yap_on_slack.post_messages import (
    AppConfig,
    SlackUser,
    SlackWorkspace,
    _assign_users_to_ai_messages,
    load_config,
    load_messages,
)


class TestLoadConfig:
    """Test suite for load_config function."""

    def test_load_config_success(self):
        """Test loading valid configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SLACK_XOXC_TOKEN=xoxc-test\n")
            f.write("SLACK_XOXD_TOKEN=xoxd-test\n")
            f.write("SLACK_ORG_URL=https://test.slack.com\n")
            f.write("SLACK_CHANNEL_ID=C123\n")
            f.write("SLACK_TEAM_ID=T123\n")
            env_file = f.name

        try:
            with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
                mock_dotenv.return_value = {
                    "SLACK_XOXC_TOKEN": "xoxc-test",
                    "SLACK_XOXD_TOKEN": "xoxd-test",
                    "SLACK_ORG_URL": "https://test.slack.com",
                    "SLACK_CHANNEL_ID": "C123",
                    "SLACK_TEAM_ID": "T123",
                }
                app_config, env = load_config(Path("/__nope__/users.yaml"))

                assert app_config.workspace.SLACK_ORG_URL == "https://test.slack.com"
                assert app_config.workspace.SLACK_CHANNEL_ID == "C123"
                assert app_config.workspace.SLACK_TEAM_ID == "T123"

                assert len(app_config.users) == 1
                assert app_config.users[0].SLACK_XOXC_TOKEN == "xoxc-test"
                assert app_config.users[0].SLACK_XOXD_TOKEN == "xoxd-test"

                assert env["SLACK_ORG_URL"] == "https://test.slack.com"
        finally:
            Path(env_file).unlink(missing_ok=True)

    def test_load_config_missing_required_var(self):
        """Test loading config with missing required variables."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "xoxc-test",
                "SLACK_XOXD_TOKEN": "xoxd-test",
                # Missing SLACK_ORG_URL, SLACK_CHANNEL_ID, SLACK_TEAM_ID
            }

            with pytest.raises(ValueError, match="Missing required environment variables"):
                load_config(Path("/__nope__/users.yaml"))

    def test_load_config_empty_values(self):
        """Test loading config with empty string values."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "",  # Empty string
                "SLACK_XOXD_TOKEN": "xoxd-test",
                "SLACK_ORG_URL": "https://test.slack.com",
                "SLACK_CHANNEL_ID": "C123",
                "SLACK_TEAM_ID": "T123",
            }

            with pytest.raises(ValueError, match="Missing required environment variables"):
                load_config(Path("/__nope__/users.yaml"))

    def test_load_config_extra_vars_ignored(self):
        """Test that extra variables in .env are loaded but don't break config."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "xoxc-test",
                "SLACK_XOXD_TOKEN": "xoxd-test",
                "SLACK_ORG_URL": "https://test.slack.com",
                "SLACK_CHANNEL_ID": "C123",
                "SLACK_TEAM_ID": "T123",
                "EXTRA_VAR": "extra_value",  # Extra variable
            }

            _, env = load_config(Path("/__nope__/users.yaml"))
            assert "EXTRA_VAR" in env
            assert len(env) == 6

        def test_load_config_from_yaml_users_file(self, tmp_path):
            """Test loading multi-user config from a YAML file."""
            users_file = tmp_path / "users.yaml"
            users_file.write_text(
                """
strategy: round_robin
default_user: alice
users:
    - name: alice
        SLACK_XOXC_TOKEN: xoxc-alice
        SLACK_XOXD_TOKEN: xoxd-alice
    - name: bob
        SLACK_XOXC_TOKEN: xoxc-bob
        SLACK_XOXD_TOKEN: xoxd-bob
""".lstrip()
            )

            with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
                mock_dotenv.return_value = {
                    "SLACK_XOXC_TOKEN": "xoxc-env",
                    "SLACK_XOXD_TOKEN": "xoxd-env",
                    "SLACK_USER_NAME": "env",
                    "SLACK_ORG_URL": "https://test.slack.com",
                    "SLACK_CHANNEL_ID": "C123",
                    "SLACK_TEAM_ID": "T123",
                }

                app_config, _ = load_config(users_file)
                assert app_config.default_user == "alice"
                assert app_config.strategy == "round_robin"
                assert len(app_config.users) == 3
                assert app_config.users[0].name == "env"
                assert app_config.users[1].name == "alice"
                assert app_config.users[2].name == "bob"

        def test_load_config_missing_users_file_falls_back_to_env_user(self, tmp_path):
            """If users.yaml is configured but missing, fall back to .env user."""
            missing_users = tmp_path / "users.yaml"

            with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
                mock_dotenv.return_value = {
                    "SLACK_XOXC_TOKEN": "xoxc-env",
                    "SLACK_XOXD_TOKEN": "xoxd-env",
                    "SLACK_USER_NAME": "env",
                    "SLACK_ORG_URL": "https://test.slack.com",
                    "SLACK_CHANNEL_ID": "C123",
                    "SLACK_TEAM_ID": "T123",
                    "SLACK_USERS_FILE": str(missing_users),
                }

                app_config, _ = load_config()
                assert len(app_config.users) == 1
                assert app_config.users[0].name == "env"

    class TestAiUserAssignment:
        def test_assigns_users_to_ai_messages(self):
            app = AppConfig(
                workspace=SlackWorkspace(
                    SLACK_ORG_URL="https://test.slack.com",
                    SLACK_CHANNEL_ID="C123",
                    SLACK_TEAM_ID="T123",
                ),
                users=[
                    SlackUser(name="env", SLACK_XOXC_TOKEN="x1", SLACK_XOXD_TOKEN="d1"),
                    SlackUser(name="alice", SLACK_XOXC_TOKEN="x2", SLACK_XOXD_TOKEN="d2"),
                ],
                default_user="env",
                strategy="round_robin",
            )

            messages = [
                {"text": "Hello", "replies": ["r1", "r2"]},
                {"text": "Hi", "replies": []},
            ]

            _assign_users_to_ai_messages(app, messages)

            assert messages[0]["user"] in {"env", "alice"}
            assert messages[1]["user"] in {"env", "alice"}
            assert isinstance(messages[0]["replies"], list)
            assert messages[0]["replies"][0]["text"] == "r1"
            assert messages[0]["replies"][0]["user"] in {"env", "alice"}


class TestLoadMessages:
    """Test suite for load_messages function."""

    def test_load_messages_from_file(self):
        """Test loading messages from messages.json file."""
        test_messages = [
            {"text": "Test message 1", "replies": ["Reply 1"]},
            {"text": "Test message 2", "replies": []},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            messages_file = Path(tmpdir) / "messages.json"
            with messages_file.open("w") as f:
                json.dump(test_messages, f)

            with patch("yap_on_slack.post_messages.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.open.return_value.__enter__.return_value = (
                    messages_file.open()
                )

                messages = load_messages()

                assert len(messages) == 2
                assert messages[0]["text"] == "Test message 1"
                assert messages[0]["replies"] == [{"text": "Reply 1", "user": None}]

    def test_load_messages_file_not_exists(self):
        """Test loading default messages when file doesn't exist."""
        with patch("yap_on_slack.post_messages.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            messages = load_messages()

            # Should return default messages
            assert len(messages) == 22
            assert isinstance(messages, list)
            assert all("text" in msg for msg in messages)

    def test_load_messages_invalid_json(self):
        """Test loading messages with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_file = Path(tmpdir) / "messages.json"
            with messages_file.open("w") as f:
                f.write("{ invalid json }")

            with patch("yap_on_slack.post_messages.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.open.return_value.__enter__.return_value = (
                    messages_file.open()
                )

                messages = load_messages()

                # Should fallback to default messages
                assert len(messages) == 22

    def test_load_messages_default_format(self):
        """Test that default messages have correct format."""
        with patch("yap_on_slack.post_messages.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            messages = load_messages()

            for msg in messages:
                assert "text" in msg
                assert isinstance(msg["text"], str)
                if "replies" in msg:
                    assert isinstance(msg["replies"], list)

    def test_load_messages_with_empty_file(self):
        """Test loading empty messages file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_file = Path(tmpdir) / "messages.json"
            with messages_file.open("w") as f:
                json.dump([], f)

            with patch("yap_on_slack.post_messages.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.open.return_value.__enter__.return_value = (
                    messages_file.open()
                )

                messages = load_messages()

                assert len(messages) == 0
                assert isinstance(messages, list)


class TestMainFlow:
    """Integration tests for the main message posting flow."""

    @pytest.fixture
    def app_env(self):
        """Provide test configuration."""
        app = AppConfig(
            workspace=SlackWorkspace(
                SLACK_ORG_URL="https://test-workspace.slack.com",
                SLACK_CHANNEL_ID="C1234567890",
                SLACK_TEAM_ID="T1234567890",
            ),
            users=[
                SlackUser(
                    name="default",
                    SLACK_XOXC_TOKEN="xoxc-test-token",
                    SLACK_XOXD_TOKEN="xoxd-test-token",
                )
            ],
            default_user="default",
            strategy="round_robin",
        )
        env = {
            "SLACK_XOXC_TOKEN": "xoxc-test-token",
            "SLACK_XOXD_TOKEN": "xoxd-test-token",
            "SLACK_ORG_URL": "https://test-workspace.slack.com",
            "SLACK_CHANNEL_ID": "C1234567890",
            "SLACK_TEAM_ID": "T1234567890",
        }
        return app, env

    @patch("yap_on_slack.post_messages.httpx.post")
    @patch("yap_on_slack.post_messages.time.sleep")
    @patch("yap_on_slack.post_messages.load_config")
    @patch("yap_on_slack.post_messages.load_messages")
    def test_main_posts_all_messages(
        self, mock_load_messages, mock_load_config, mock_sleep, mock_post, app_env
    ):
        """Test that main function posts all messages including replies."""
        from yap_on_slack.post_messages import main

        test_messages = [
            {"text": "Message 1", "replies": ["Reply 1"]},
            {"text": "Message 2", "replies": []},
        ]

        mock_load_config.return_value = app_env
        mock_load_messages.return_value = test_messages

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_post.return_value = mock_response

        main()

        # Should post 3 messages total: 2 main + 1 reply
        assert mock_post.call_count == 3

    @patch("yap_on_slack.post_messages.httpx.post")
    @patch("yap_on_slack.post_messages.time.sleep")
    @patch("yap_on_slack.post_messages.load_config")
    @patch("yap_on_slack.post_messages.load_messages")
    def test_main_handles_api_failures_gracefully(
        self, mock_load_messages, mock_load_config, mock_sleep, mock_post, app_env
    ):
        """Test that main function handles API failures gracefully."""
        from yap_on_slack.post_messages import main

        test_messages = [{"text": "Message 1", "replies": []}]

        mock_load_config.return_value = app_env
        mock_load_messages.return_value = test_messages

        # Simulate API failure
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "rate_limited"}
        mock_post.return_value = mock_response

        # Should not raise exception
        main()

        assert mock_post.call_count >= 1

    @patch("yap_on_slack.post_messages.httpx.post")
    @patch("yap_on_slack.post_messages.time.sleep")
    @patch("yap_on_slack.post_messages.load_config")
    @patch("yap_on_slack.post_messages.load_messages")
    def test_main_posts_replies_with_thread_ts(
        self, mock_load_messages, mock_load_config, mock_sleep, mock_post, app_env
    ):
        """Test that replies are posted with correct thread_ts."""
        from yap_on_slack.post_messages import main

        test_messages = [{"text": "Parent message", "replies": ["Reply 1", "Reply 2"]}]

        mock_load_config.return_value = app_env
        mock_load_messages.return_value = test_messages

        parent_ts = "1234567890.123456"
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "ts": parent_ts}
        mock_post.return_value = mock_response

        main()

        # Check that replies use thread_ts
        assert mock_post.call_count == 3  # 1 parent + 2 replies
        # The second and third calls should have thread_ts in data
        for call in mock_post.call_args_list[1:]:
            data = call.kwargs.get("data", {})
            assert "thread_ts" in data
            assert data["thread_ts"] == parent_ts
            assert data["reply_broadcast"] == "false"

    @patch("yap_on_slack.post_messages.httpx.post")
    @patch("yap_on_slack.post_messages.time.sleep")
    @patch("yap_on_slack.post_messages.load_config")
    @patch("yap_on_slack.post_messages.load_messages")
    def test_main_adds_reactions_for_messages_with_emoji(
        self, mock_load_messages, mock_load_config, mock_sleep, mock_post, app_env
    ):
        """Test that reactions are added for messages containing emoji."""
        from yap_on_slack.post_messages import main

        test_messages = [{"text": "Deploy complete :rocket:", "replies": []}]

        mock_load_config.return_value = app_env
        mock_load_messages.return_value = test_messages

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_post.return_value = mock_response

        main()

        # Should post message + add reaction
        assert mock_post.call_count == 2

        # Check that reaction endpoint was called
        calls = [call[0][0] for call in mock_post.call_args_list]
        assert any("reactions.add" in url for url in calls)
