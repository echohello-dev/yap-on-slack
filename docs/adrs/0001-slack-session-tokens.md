---
date: 2026-01-02
status: Accepted
---

# 0001: Use Slack Session Tokens Instead of Bot API

## Context

Yap-on-slack needs to post realistic messages to Slack channels for testing purposes. There are two primary approaches to authenticate with Slack:

1. **Official Bot API**: Use bot tokens (xoxb-...) with the official Slack SDK
2. **Session Tokens**: Use browser session tokens (xoxc-... and xoxd-...) to mimic user behavior

The official Bot API has limitations:
- Bot messages are clearly labeled as "APP" in Slack
- Formatting options are restricted
- Messages don't look like real user messages
- Requires app installation and OAuth flow

For testing purposes, we need messages that look identical to real user messages, including:
- Full rich text formatting (bold, italic, code, links, emoji)
- Threading and replies that appear natural
- Reactions that seem authentic
- No "APP" or "BOT" badges

## Decision

We will use Slack session tokens (xoxc and xoxd) extracted from browser cookies to post messages via Slack's internal API endpoints.

**Implementation:**
- Extract tokens from browser developer tools
- Use `httpx` to post directly to `/api/chat.postMessage`
- Include session cookie (`d` token) and form data token (`xoxc`)
- Construct rich_text blocks matching Slack's internal format

## Alternatives Considered

### Alternative 1: Official Slack Bot API with SDK

Use `slack_sdk` package with bot tokens:

```python
from slack_sdk import WebClient
client = WebClient(token=bot_token)
client.chat_postMessage(channel=channel, text=text)
```

**Why not chosen:**
- Bot messages are visually distinct (labeled as APP)
- Limited formatting compared to real user messages
- Requires OAuth setup and app installation
- Doesn't achieve "realistic testing" goal

### Alternative 2: Slack Webhooks

Use incoming webhooks to post messages:

```python
httpx.post(webhook_url, json={"text": message})
```

**Why not chosen:**
- Also labeled as APP/integration
- Very limited formatting options
- Cannot thread or reply to messages
- No reaction support

### Alternative 3: Playwright Browser Automation

Automate a real browser to type and send messages:

**Why not chosen:**
- Extremely slow (seconds per message)
- Heavy dependency (full browser)
- Complex setup and maintenance
- Overkill for the use case

## Consequences

### Positive

- **Realistic messages**: Indistinguishable from real user messages
- **Full formatting**: Complete access to Slack's rich text features
- **Threading support**: Can create threaded conversations
- **Reactions**: Can add emoji reactions to messages
- **Lightweight**: Only needs httpx, no heavy SDKs
- **Simple**: Direct HTTP API calls, no OAuth flow

### Negative

- **Unofficial API**: Using Slack's internal endpoints, not officially supported
- **Token extraction**: Users must manually extract tokens from browser
- **Token expiration**: Session tokens expire and need periodic refresh
- **Terms of service**: May violate Slack's ToS for automation
- **Fragility**: Internal API could change without notice
- **Security risk**: Tokens provide full user access if leaked

### Mitigation Strategies

- Document token extraction clearly in README
- Warn users about token sensitivity in .env.example
- Advise testing in development/test workspaces only
- Include token expiration guidance
- Note this is for testing purposes, not production use

## References

- [Slack Web API Documentation](https://api.slack.com/web)
- [Rich text formatting in Slack](https://api.slack.com/reference/block-kit/blocks#rich_text)
- Project README: Token extraction guide
- Implementation: [yap_on_slack/post_messages.py](../../yap_on_slack/post_messages.py)
