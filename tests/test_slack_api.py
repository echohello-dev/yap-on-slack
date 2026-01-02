"""Mock tests for Slack API interactions."""

import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest

from yap_on_slack.post_messages import add_reaction, post_message


class TestPostMessage:
    """Test suite for post_message function."""

    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return {
            "SLACK_XOXC_TOKEN": "xoxc-test-token",
            "SLACK_XOXD_TOKEN": "xoxd-test-token",
            "SLACK_ORG_URL": "https://test-workspace.slack.com",
            "SLACK_CHANNEL_ID": "C1234567890",
            "SLACK_TEAM_ID": "T1234567890",
        }

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_success(self, mock_post, config):
        """Test successful message posting."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C1234567890",
        }
        mock_post.return_value = mock_response

        result = post_message("Test message", config)

        assert result is not None
        assert result["ok"] is True
        assert "ts" in result
        mock_post.assert_called_once()

        # Verify call arguments
        call_args = mock_post.call_args
        assert call_args.kwargs["data"]["token"] == config["SLACK_XOXC_TOKEN"]
        assert call_args.kwargs["data"]["channel"] == config["SLACK_CHANNEL_ID"]
        assert call_args.kwargs["cookies"]["d"] == config["SLACK_XOXD_TOKEN"]

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_with_thread(self, mock_post, config):
        """Test posting a message in a thread."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123457",
            "thread_ts": "1234567890.123456",
        }
        mock_post.return_value = mock_response

        result = post_message("Reply message", config, thread_ts="1234567890.123456")

        assert result is not None
        call_args = mock_post.call_args
        assert call_args.kwargs["data"]["thread_ts"] == "1234567890.123456"
        assert call_args.kwargs["data"]["reply_broadcast"] == "false"

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_failure(self, mock_post, config):
        """Test message posting failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "channel_not_found",
        }
        mock_post.return_value = mock_response

        result = post_message("Test message", config)

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_network_error(self, mock_post, config):
        """Test network error during message posting."""
        mock_post.side_effect = httpx.ConnectError("Connection failed")

        result = post_message("Test message", config)

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_timeout(self, mock_post, config):
        """Test timeout during message posting."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        result = post_message("Test message", config)

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_with_formatting(self, mock_post, config):
        """Test posting message with rich formatting."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_post.return_value = mock_response

        result = post_message("*Bold* and _italic_ text", config)

        assert result is not None
        call_args = mock_post.call_args
        assert "blocks" in call_args.kwargs["data"]

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_post_message_generates_unique_client_msg_id(self, mock_post, config):
        """Test that each message gets a unique client_msg_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "ts": "1234567890.123456"}
        mock_post.return_value = mock_response

        post_message("Message 1", config)
        call_args1 = mock_post.call_args

        post_message("Message 2", config)
        call_args2 = mock_post.call_args

        msg_id1 = call_args1.kwargs["data"]["client_msg_id"]
        msg_id2 = call_args2.kwargs["data"]["client_msg_id"]

        # Verify both are valid UUIDs and different
        uuid.UUID(msg_id1)
        uuid.UUID(msg_id2)
        assert msg_id1 != msg_id2


class TestAddReaction:
    """Test suite for add_reaction function."""

    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return {
            "SLACK_XOXC_TOKEN": "xoxc-test-token",
            "SLACK_XOXD_TOKEN": "xoxd-test-token",
            "SLACK_ORG_URL": "https://test-workspace.slack.com",
        }

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_success(self, mock_post, config):
        """Test successfully adding a reaction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        result = add_reaction("C1234567890", "1234567890.123456", "thumbsup", config)

        assert result is True
        mock_post.assert_called_once()

        # Verify call arguments
        call_args = mock_post.call_args
        assert call_args.kwargs["data"]["channel"] == "C1234567890"
        assert call_args.kwargs["data"]["timestamp"] == "1234567890.123456"
        assert call_args.kwargs["data"]["name"] == "thumbsup"

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_failure(self, mock_post, config):
        """Test reaction adding failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "already_reacted",
        }
        mock_post.return_value = mock_response

        result = add_reaction("C1234567890", "1234567890.123456", "thumbsup", config)

        assert result is False

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_network_error(self, mock_post, config):
        """Test network error during reaction adding."""
        mock_post.side_effect = httpx.ConnectError("Connection failed")

        result = add_reaction("C1234567890", "1234567890.123456", "thumbsup", config)

        assert result is False

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_timeout(self, mock_post, config):
        """Test timeout during reaction adding."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        result = add_reaction("C1234567890", "1234567890.123456", "thumbsup", config)

        assert result is False

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_with_emoji_variants(self, mock_post, config):
        """Test adding various emoji types."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        emojis = ["thumbsup", "rocket", "thinking_face", "white_check_mark"]

        for emoji in emojis:
            result = add_reaction("C1234567890", "1234567890.123456", emoji, config)
            assert result is True

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_uses_correct_endpoint(self, mock_post, config):
        """Test that reactions use the correct API endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        add_reaction("C1234567890", "1234567890.123456", "wave", config)

        call_args = mock_post.call_args
        assert call_args[0][0] == f"{config['SLACK_ORG_URL']}/api/reactions.add"

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_add_reaction_timeout_value(self, mock_post, config):
        """Test that reaction requests have appropriate timeout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        add_reaction("C1234567890", "1234567890.123456", "wave", config)

        call_args = mock_post.call_args
        assert call_args.kwargs["timeout"] == 5
