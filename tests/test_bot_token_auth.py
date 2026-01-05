"""Tests for bot token authentication support."""

import pytest
from pydantic import ValidationError

from yap_on_slack.post_messages import (
    CredentialsConfigModel,
    SlackUser,
    UnifiedConfig,
    UserConfigModel,
    _build_auth_headers,
    _is_bot_token_auth,
)


def test_credentials_config_with_bot_token():
    """Test CredentialsConfigModel accepts bot token."""
    config = CredentialsConfigModel(
        bot_token="xoxb-1234567890-1234567890123-EXAMPLE_TOKEN_NOT_REAL_12345"
    )
    assert config.bot_token == "xoxb-1234567890-1234567890123-EXAMPLE_TOKEN_NOT_REAL_12345"
    assert config.xoxc_token is None
    assert config.xoxd_token is None


def test_credentials_config_with_session_tokens():
    """Test CredentialsConfigModel accepts session tokens."""
    config = CredentialsConfigModel(
        xoxc_token="xoxc-test-token",
        xoxd_token="xoxd-test-token",
    )
    assert config.xoxc_token == "xoxc-test-token"
    assert config.xoxd_token == "xoxd-test-token"
    assert config.bot_token is None


def test_user_config_with_bot_token():
    """Test UserConfigModel accepts bot token."""
    user = UserConfigModel(
        name="test_bot", bot_token="xoxb-EXAMPLE-NOT-A-REAL-TOKEN-FOR-TESTING"
    )
    assert user.name == "test_bot"
    assert user.bot_token == "xoxb-EXAMPLE-NOT-A-REAL-TOKEN-FOR-TESTING"
    assert user.xoxc_token is None
    assert user.xoxd_token is None


def test_user_config_with_session_tokens():
    """Test UserConfigModel accepts session tokens."""
    user = UserConfigModel(
        name="test_user",
        xoxc_token="xoxc-test-token",
        xoxd_token="xoxd-test-token",
    )
    assert user.name == "test_user"
    assert user.xoxc_token == "xoxc-test-token"
    assert user.xoxd_token == "xoxd-test-token"
    assert user.bot_token is None


def test_user_config_requires_either_tokens_or_bot():
    """Test UserConfigModel validates that at least one auth method is provided."""
    with pytest.raises(ValidationError, match="must have either session tokens|or bot_token"):
        UserConfigModel(name="test_user")


def test_user_config_rejects_both_tokens_and_bot():
    """Test UserConfigModel rejects both session tokens and bot token."""
    with pytest.raises(ValidationError, match="cannot have both"):
        UserConfigModel(
            name="test_user",
            xoxc_token="xoxc-test-token",
            xoxd_token="xoxd-test-token",
            bot_token="xoxb-test-token",
        )


def test_slack_user_with_bot_token():
    """Test SlackUser model accepts bot token."""
    user = SlackUser(
        name="bot_user", SLACK_BOT_TOKEN="xoxb-FAKE-TOKEN-FOR-TESTING-NOT-REAL"
    )
    assert user.name == "bot_user"
    assert user.SLACK_BOT_TOKEN == "xoxb-FAKE-TOKEN-FOR-TESTING-NOT-REAL"
    assert user.SLACK_XOXC_TOKEN is None
    assert user.SLACK_XOXD_TOKEN is None


def test_slack_user_with_session_tokens():
    """Test SlackUser model accepts session tokens."""
    user = SlackUser(
        name="session_user",
        SLACK_XOXC_TOKEN="xoxc-test-token",
        SLACK_XOXD_TOKEN="xoxd-test-token",
    )
    assert user.name == "session_user"
    assert user.SLACK_XOXC_TOKEN == "xoxc-test-token"
    assert user.SLACK_XOXD_TOKEN == "xoxd-test-token"
    assert user.SLACK_BOT_TOKEN is None


def test_slack_user_requires_either_tokens_or_bot():
    """Test SlackUser validates that at least one auth method is provided."""
    with pytest.raises(ValidationError, match="must have either session tokens|or SLACK_BOT_TOKEN"):
        SlackUser(name="test_user")


def test_slack_user_rejects_both_tokens_and_bot():
    """Test SlackUser rejects both session tokens and bot token."""
    with pytest.raises(ValidationError, match="cannot have both"):
        SlackUser(
            name="test_user",
            SLACK_XOXC_TOKEN="xoxc-test-token",
            SLACK_XOXD_TOKEN="xoxd-test-token",
            SLACK_BOT_TOKEN="xoxb-test-token",
        )


def test_is_bot_token_auth_detects_bot_token():
    """Test _is_bot_token_auth helper correctly detects bot token."""
    config_with_bot = {"SLACK_BOT_TOKEN": "xoxb-test-token"}
    assert _is_bot_token_auth(config_with_bot) is True

    config_with_session = {
        "SLACK_XOXC_TOKEN": "xoxc-test-token",
        "SLACK_XOXD_TOKEN": "xoxd-test-token",
    }
    assert _is_bot_token_auth(config_with_session) is False

    config_empty = {}
    assert _is_bot_token_auth(config_empty) is False


def test_build_auth_headers_with_bot_token():
    """Test _build_auth_headers creates Authorization header for bot token."""
    config = {"SLACK_BOT_TOKEN": "xoxb-test-token"}
    headers = _build_auth_headers(config)

    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer xoxb-test-token"
    assert "user-agent" in headers


def test_build_auth_headers_with_session_tokens():
    """Test _build_auth_headers doesn't add Authorization for session tokens."""
    config = {
        "SLACK_XOXC_TOKEN": "xoxc-test-token",
        "SLACK_XOXD_TOKEN": "xoxd-test-token",
    }
    headers = _build_auth_headers(config)

    assert "Authorization" not in headers
    assert "user-agent" in headers


def test_unified_config_with_bot_token():
    """Test UnifiedConfig accepts bot token in credentials."""
    config_data = {
        "workspace": {
            "org_url": "https://test.slack.com",
            "channel_id": "C0123456789",
            "team_id": "T0123456789",
        },
        "credentials": {"bot_token": "xoxb-TEST-EXAMPLE-TOKEN-NOT-REAL"},
    }

    config = UnifiedConfig(**config_data)
    assert config.credentials.bot_token == "xoxb-TEST-EXAMPLE-TOKEN-NOT-REAL"


def test_unified_config_with_mixed_users():
    """Test UnifiedConfig accepts mixed bot and session token users."""
    config_data = {
        "workspace": {
            "org_url": "https://test.slack.com",
            "channel_id": "C0123456789",
            "team_id": "T0123456789",
        },
        "credentials": {
            "xoxc_token": "xoxc-default-token",
            "xoxd_token": "xoxd-default-token",
        },
        "users": [
            {
                "name": "bot_user",
                "bot_token": "xoxb-bot-token",
            },
            {
                "name": "session_user",
                "xoxc_token": "xoxc-user-token",
                "xoxd_token": "xoxd-user-token",
            },
        ],
    }

    config = UnifiedConfig(**config_data)
    assert len(config.users) == 2
    assert config.users[0].name == "bot_user"
    assert config.users[0].bot_token == "xoxb-bot-token"
    assert config.users[1].name == "session_user"
    assert config.users[1].xoxc_token == "xoxc-user-token"
