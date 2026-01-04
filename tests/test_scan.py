"""Tests for channel scanning functionality."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from yap_on_slack.post_messages import (
    SlackAPIError,
    SlackNetworkError,
    SlackRateLimitError,
    fetch_channel_messages,
    generate_system_prompts,
    get_channel_info,
    list_channels,
)


class TestListChannels:
    """Test suite for list_channels function."""

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
    def test_list_channels_success(self, mock_post, config):
        """Test successful channel listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "channels": [
                {
                    "id": "C1234567890",
                    "name": "general",
                    "num_members": 42,
                    "is_private": False,
                    "topic": {"value": "General discussion"},
                },
                {
                    "id": "C0987654321",
                    "name": "random",
                    "num_members": 35,
                    "is_private": False,
                    "topic": {"value": "Random stuff"},
                },
            ],
            "response_metadata": {},
        }
        mock_post.return_value = mock_response

        result = list_channels(config)

        assert len(result) == 2
        assert result[0]["id"] == "C1234567890"
        assert result[0]["name"] == "general"
        assert result[0]["num_members"] == 42
        assert result[0]["is_private"] is False
        mock_post.assert_called_once()

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_list_channels_with_pagination(self, mock_post, config):
        """Test channel listing with pagination."""
        # First response with cursor
        first_response = MagicMock()
        first_response.json.return_value = {
            "ok": True,
            "channels": [{"id": "C1", "name": "ch1", "num_members": 10, "is_private": False}],
            "response_metadata": {"next_cursor": "cursor123"},
        }

        # Second response without cursor
        second_response = MagicMock()
        second_response.json.return_value = {
            "ok": True,
            "channels": [{"id": "C2", "name": "ch2", "num_members": 20, "is_private": True}],
            "response_metadata": {},
        }

        mock_post.side_effect = [first_response, second_response]

        result = list_channels(config)

        assert len(result) == 2
        assert result[0]["name"] == "ch1"
        assert result[1]["name"] == "ch2"
        assert mock_post.call_count == 2

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_list_channels_rate_limited(self, mock_post, config):
        """Test rate limit handling."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "ratelimited"}
        mock_response.headers = {"Retry-After": "60"}
        mock_post.return_value = mock_response

        with pytest.raises(SlackRateLimitError) as exc_info:
            list_channels(config)

        assert "Rate limited" in str(exc_info.value)

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_list_channels_auth_error(self, mock_post, config):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}
        mock_post.return_value = mock_response

        with pytest.raises(SlackAPIError) as exc_info:
            list_channels(config)

        assert "Authentication error" in str(exc_info.value)

    @patch("time.sleep")
    @patch("yap_on_slack.post_messages.httpx.post")
    def test_list_channels_network_error(self, mock_post, mock_sleep, config):
        """Test network error handling with retries."""
        mock_post.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(SlackNetworkError):
            list_channels(config)

        # Verify it retried 3 times
        assert mock_post.call_count == 3


class TestGetChannelInfo:
    """Test suite for get_channel_info function."""

    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return {
            "SLACK_XOXC_TOKEN": "xoxc-test-token",
            "SLACK_XOXD_TOKEN": "xoxd-test-token",
            "SLACK_ORG_URL": "https://test-workspace.slack.com",
        }

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_get_channel_info_success(self, mock_post, config):
        """Test successful channel info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "general",
                "num_members": 42,
                "is_private": False,
                "topic": {"value": "General discussion"},
            },
        }
        mock_post.return_value = mock_response

        result = get_channel_info(config, "C1234567890")

        assert result is not None
        assert result["id"] == "C1234567890"
        assert result["name"] == "general"

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_get_channel_info_not_found(self, mock_post, config):
        """Test channel not found returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}
        mock_post.return_value = mock_response

        result = get_channel_info(config, "C9999999999")

        assert result is None


class TestFetchChannelMessages:
    """Test suite for fetch_channel_messages function."""

    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return {
            "SLACK_XOXC_TOKEN": "xoxc-test-token",
            "SLACK_XOXD_TOKEN": "xoxd-test-token",
            "SLACK_ORG_URL": "https://test-workspace.slack.com",
        }

    @patch("time.sleep")  # Mock sleep to speed up tests
    @patch("yap_on_slack.post_messages.httpx.post")
    def test_fetch_messages_success(self, mock_post, mock_sleep, config):
        """Test successful message fetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {
                    "text": "Hello world",
                    "user": "U1234",
                    "ts": "1234567890.123456",
                    "reply_count": 0,
                    "reactions": [{"name": "thumbsup", "count": 3}],
                },
                {
                    "text": "How are you?",
                    "user": "U5678",
                    "ts": "1234567890.123457",
                    "reply_count": 0,
                },
            ],
            "response_metadata": {},
        }
        mock_post.return_value = mock_response

        result = fetch_channel_messages(config, "C1234567890", limit=10, throttle=0)

        assert result["total_messages"] == 2
        assert result["total_reactions"] == 3
        assert len(result["messages"]) == 2
        assert result["messages"][0]["text"] == "Hello world"

    @patch("time.sleep")
    @patch("yap_on_slack.post_messages.httpx.post")
    def test_fetch_messages_with_replies(self, mock_post, mock_sleep, config):
        """Test fetching messages with thread replies."""
        # First call: history
        history_response = MagicMock()
        history_response.json.return_value = {
            "ok": True,
            "messages": [
                {
                    "text": "Original message",
                    "user": "U1234",
                    "ts": "1234567890.123456",
                    "reply_count": 2,
                },
            ],
            "response_metadata": {},
        }

        # Second call: replies
        replies_response = MagicMock()
        replies_response.json.return_value = {
            "ok": True,
            "messages": [
                {"text": "Original message", "user": "U1234", "ts": "1234567890.123456"},
                {"text": "Reply 1", "user": "U5678", "ts": "1234567890.123457"},
                {"text": "Reply 2", "user": "U9012", "ts": "1234567890.123458"},
            ],
        }

        mock_post.side_effect = [history_response, replies_response]

        result = fetch_channel_messages(config, "C1234567890", limit=10, throttle=0)

        assert result["total_messages"] == 1
        assert result["total_replies"] == 2
        assert len(result["messages"][0]["replies"]) == 2

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_fetch_messages_rate_limited(self, mock_post, config):
        """Test rate limit handling."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "ratelimited"}
        mock_response.headers = {"Retry-After": "60"}
        mock_post.return_value = mock_response

        with pytest.raises(SlackRateLimitError):
            fetch_channel_messages(config, "C1234567890", limit=10, throttle=0)

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_fetch_messages_channel_not_found(self, mock_post, config):
        """Test channel not found error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}
        mock_post.return_value = mock_response

        with pytest.raises(SlackAPIError) as exc_info:
            fetch_channel_messages(config, "C9999999999", limit=10, throttle=0)

        assert "not found" in str(exc_info.value)

    @patch("time.sleep")
    @patch("yap_on_slack.post_messages.httpx.post")
    def test_fetch_messages_progress_callback(self, mock_post, mock_sleep, config):
        """Test progress callback is called."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "messages": [{"text": "Test", "user": "U1", "ts": "123.456", "reply_count": 0}],
            "response_metadata": {},
        }
        mock_post.return_value = mock_response

        progress_calls = []

        def callback(current, total, status):
            progress_calls.append((current, total, status))

        fetch_channel_messages(
            config, "C1234567890", limit=10, throttle=0, progress_callback=callback
        )

        assert len(progress_calls) > 0


class TestGenerateSystemPrompts:
    """Test suite for generate_system_prompts function."""

    @pytest.fixture
    def channel_data(self):
        """Provide sample channel data."""
        return {
            "name": "test-channel",
            "total_messages": 50,
            "total_replies": 20,
            "total_reactions": 100,
            "top_reactions": [("thumbsup", 30), ("rocket", 20), ("eyes", 15)],
            "messages": [
                {"text": "Hello team! How's everyone doing today?", "replies": []},
                {"text": "Working on the new feature", "replies": [{"text": "Nice!"}]},
            ],
        }

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_generate_prompts_success(self, mock_post, channel_data):
        """Test successful prompt generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                "Prompt 1: Focus on casual tone...",
                                "Prompt 2: Focus on message structure...",
                                "Prompt 3: Focus on content themes...",
                            ]
                        )
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = generate_system_prompts(channel_data, model="test-model", api_key="test-api-key")

        assert result is not None
        assert len(result) == 3
        assert "Prompt 1" in result[0]

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_generate_prompts_with_markdown_code_block(self, mock_post, channel_data):
        """Test parsing prompts from markdown code blocks."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": '```json\n["Prompt A", "Prompt B", "Prompt C"]\n```'}}
            ]
        }
        mock_post.return_value = mock_response

        result = generate_system_prompts(channel_data, model="test-model", api_key="test-api-key")

        assert result is not None
        assert len(result) == 3

    def test_generate_prompts_no_api_key(self, channel_data):
        """Test that missing API key returns None."""
        with patch.dict("os.environ", {}, clear=True):
            result = generate_system_prompts(channel_data, api_key=None)

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_generate_prompts_api_error(self, mock_post, channel_data):
        """Test API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        result = generate_system_prompts(channel_data, model="test-model", api_key="test-api-key")

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_generate_prompts_invalid_auth(self, mock_post, channel_data):
        """Test invalid auth handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        result = generate_system_prompts(channel_data, model="test-model", api_key="invalid-key")

        assert result is None

    @patch("yap_on_slack.post_messages.httpx.post")
    def test_generate_prompts_timeout(self, mock_post, channel_data):
        """Test timeout handling."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        result = generate_system_prompts(channel_data, model="test-model", api_key="test-api-key")

        assert result is None
