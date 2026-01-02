"""Tests for error handling and retry logic."""

from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from yap_on_slack.post_messages import (
    AppConfig,
    InvalidMessageFormatError,
    SlackAPIError,
    SlackNetworkError,
    SlackRateLimitError,
    add_reaction,
    load_config,
    load_messages,
    parse_rich_text_from_string,
    post_message,
)


class TestConfigValidation:
    """Test configuration loading and validation."""

    def test_load_config_missing_env_file(self, tmp_path):
        """Test error when .env file is missing."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.side_effect = FileNotFoundError("No .env file")
            with pytest.raises(ValueError, match="Cannot read .env file"):
                load_config(Path("/__nope__/users.yaml"))

    def test_load_config_missing_variables(self):
        """Test error when required environment variables are missing."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "xoxc-test",
                # Missing other required vars
            }
            with pytest.raises(ValueError, match="Missing required environment variables"):
                load_config(Path("/__nope__/users.yaml"))

    def test_load_config_invalid_url_format(self):
        """Test error when SLACK_ORG_URL has invalid format."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "xoxc-test",
                "SLACK_XOXD_TOKEN": "xoxd-test",
                "SLACK_ORG_URL": "http://invalid.slack.com",  # Should be https
                "SLACK_CHANNEL_ID": "C123",
                "SLACK_TEAM_ID": "T123",
            }
            with pytest.raises(ValueError, match="SLACK_ORG_URL must start with https://"):
                load_config(Path("/__nope__/users.yaml"))

    def test_load_config_success(self):
        """Test successful configuration loading."""
        with patch("yap_on_slack.post_messages.dotenv_values") as mock_dotenv:
            mock_dotenv.return_value = {
                "SLACK_XOXC_TOKEN": "xoxc-test",
                "SLACK_XOXD_TOKEN": "xoxd-test",
                "SLACK_ORG_URL": "https://test.slack.com",
                "SLACK_CHANNEL_ID": "C123",
                "SLACK_TEAM_ID": "T123",
            }
            app_config, env = load_config(Path("/__nope__/users.yaml"))
            assert isinstance(app_config, AppConfig)
            assert app_config.users[0].SLACK_XOXC_TOKEN == "xoxc-test"
            assert app_config.workspace.SLACK_ORG_URL == "https://test.slack.com"
            assert env["SLACK_ORG_URL"] == "https://test.slack.com"


class TestMessageValidation:
    """Test message format validation."""

    def test_parse_rich_text_invalid_type(self):
        """Test error when text is not a string."""
        with pytest.raises(InvalidMessageFormatError, match="Text must be a string"):
            parse_rich_text_from_string(123)  # type: ignore

    def test_parse_rich_text_empty_string(self):
        """Test parsing empty string."""
        result = parse_rich_text_from_string("")
        assert result == [{"type": "text", "text": " "}]

    def test_parse_rich_text_with_emoji(self):
        """Test parsing text with emoji."""
        result = parse_rich_text_from_string("Hello :rocket: world")
        assert any(elem.get("type") == "emoji" and elem.get("name") == "rocket" for elem in result)

    def test_load_messages_invalid_json(self, tmp_path):
        """Test error when messages.json has invalid JSON."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text("{ invalid json }")

        # With pydantic, invalid JSON returns default messages instead of raising
        messages = load_messages(messages_file)
        assert len(messages) == 22  # Default messages

    def test_load_messages_not_array(self, tmp_path):
        """Test error when messages.json is not an array."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text('{"text": "Hello"}')

        # With pydantic validation, TypeError causes fallback to default messages
        messages = load_messages(messages_file)
        assert len(messages) == 22  # Default messages
        assert all("text" in msg for msg in messages)

    def test_load_messages_missing_text_field(self, tmp_path):
        """Test error when message is missing text field."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text('[{"replies": ["test"]}]')

        # With pydantic, invalid messages return default messages
        messages = load_messages(messages_file)
        assert len(messages) == 22  # Default messages

    def test_load_messages_invalid_text_type(self, tmp_path):
        """Test error when text field is not a string."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text('[{"text": 123}]')

        # With pydantic, invalid messages return default messages
        messages = load_messages(messages_file)
        assert len(messages) == 22  # Default messages

    def test_load_messages_invalid_replies_type(self, tmp_path):
        """Test error when replies is not an array."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text('[{"text": "Hello", "replies": "invalid"}]')

        # With pydantic, invalid messages return default messages
        messages = load_messages(messages_file)
        assert len(messages) == 22  # Default messages

    def test_load_messages_success(self, tmp_path):
        """Test successful message loading."""
        messages_file = tmp_path / "messages.json"
        messages_file.write_text('[{"text": "Hello", "replies": ["World"]}]')

        messages = load_messages(messages_file)
        assert len(messages) == 1
        assert messages[0]["text"] == "Hello"
        assert messages[0]["replies"] == [{"text": "World", "user": None}]

    def test_load_messages_default_fallback(self):
        """Test loading default messages when file doesn't exist."""
        messages = load_messages(Path("/nonexistent/messages.json"))
        assert len(messages) == 22  # Default message count
        assert all("text" in msg for msg in messages)


class TestNetworkErrors:
    """Test network error handling."""

    def test_post_message_timeout(self):
        """Test handling of timeout errors with retry."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        with patch("httpx.post") as mock_post, patch("time.sleep"):
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(SlackNetworkError, match="Network error"):
                post_message("Test message", config)

            # Should retry 3 times
            assert mock_post.call_count == 3

    def test_post_message_network_error(self):
        """Test handling of network errors with retry."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        with patch("httpx.post") as mock_post, patch("time.sleep"):
            mock_post.side_effect = httpx.NetworkError("Connection failed")

            with pytest.raises(SlackNetworkError, match="Network error"):
                post_message("Test message", config)

            assert mock_post.call_count == 3

    def test_add_reaction_timeout(self):
        """Test handling of timeout errors in add_reaction with retry."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        with patch("httpx.post") as mock_post, patch("time.sleep"):
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(SlackNetworkError, match="Network error"):
                add_reaction("C123", "123.456", "rocket", config)

            assert mock_post.call_count == 3


class TestRateLimiting:
    """Test rate limiting handling."""

    def test_post_message_rate_limited(self):
        """Test handling of rate limit errors."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "ratelimited"}
        mock_response.headers = {"Retry-After": "60"}

        with patch("httpx.post", return_value=mock_response):
            # Rate limit raises exception which does NOT trigger retry (not in retry list)
            with pytest.raises(SlackRateLimitError, match="retry after 60s"):
                add_reaction("C123", "123.456", "rocket", config)

    def test_post_message_channel_not_found(self):
        """Test handling of channel not found error."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(SlackAPIError, match="channel_not_found"):
                post_message("Test message", config)

    def test_post_message_invalid_auth(self):
        """Test handling of authentication errors."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(SlackAPIError, match="invalid_auth"):
                post_message("Test message", config)

    def test_add_reaction_invalid_emoji(self):
        """Test handling of invalid emoji name."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "invalid_name"}

        with patch("httpx.post", return_value=mock_response):
            result = add_reaction("C123", "123.456", "nonexistent_emoji", config)
            assert result is False

    def test_add_reaction_already_reacted(self):
        """Test handling of already reacted scenario."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "already_reacted"}

        with patch("httpx.post", return_value=mock_response):
            result = add_reaction("C123", "123.456", "rocket", config)
            assert result is True  # Should return True for already reacted


class TestSuccessScenarios:
    """Test successful operations."""

    def test_post_message_success(self):
        """Test successful message posting."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": True, "ts": "123.456"}

        with patch("httpx.post", return_value=mock_response):
            result = post_message("Test message", config)
            assert result is not None
            assert result["ok"] is True
            assert result["ts"] == "123.456"

    def test_add_reaction_success(self):
        """Test successful reaction addition."""
        config = {
            "SLACK_XOXC_TOKEN": "xoxc-test",
            "SLACK_XOXD_TOKEN": "xoxd-test",
            "SLACK_ORG_URL": "https://test.slack.com",
            "SLACK_CHANNEL_ID": "C123",
            "SLACK_TEAM_ID": "T123",
        }

        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}

        with patch("httpx.post", return_value=mock_response):
            result = add_reaction("C123", "123.456", "rocket", config)
            assert result is True
