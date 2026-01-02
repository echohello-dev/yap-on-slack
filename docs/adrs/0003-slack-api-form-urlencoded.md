---
date: 2026-01-02
status: Accepted
---

# 0003: Use Form-Urlencoded Instead of Multipart for Slack API

## Context

When posting messages to Slack's `chat.postMessage` endpoint using session tokens (xoxc/xoxd), requests were failing with `invalid_auth` errors despite having valid credentials. The same tokens worked in a simple standalone script but failed in our main application.

Through debugging, we discovered the issue was the HTTP content encoding:
- Our code used `files=` parameter in httpx, which sends `multipart/form-data`
- A working reference script used `data=` parameter, which sends `application/x-www-form-urlencoded`

## Decision

We will use `application/x-www-form-urlencoded` encoding (via httpx's `data=` parameter) for all Slack API requests instead of `multipart/form-data` (via `files=`).

The minimal working request pattern:

```python
response = httpx.post(
    f"{org_url}/api/chat.postMessage",
    data={
        "token": xoxc_token,
        "channel": channel_id,
        "text": message,
        # ... other fields
    },
    cookies={"d": xoxd_token},
    headers={"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    timeout=10,
)
```

We also removed unnecessary headers (`origin`, `referer`) and query parameters (`slack_route`) that were not required and may have contributed to validation failures.

## Alternatives Considered

### Alternative 1: Keep Multipart with Different Headers

Add more headers to make multipart work (Origin, Referer, various Slack-specific headers). Not chosen because the simpler form-urlencoded approach works without additional headers.

### Alternative 2: Use Official Slack SDK

Use `slack_sdk` Python package with bot tokens. Not chosen because the project specifically requires session tokens to post as real users (per ADR 0001).

### Alternative 3: Add Additional Cookies

Add extra session cookies (x, d-s, b) from browser DevTools. Tested but these were not the root cause - the encoding was.

## Consequences

### Positive

- Slack API requests work reliably with session tokens
- Simpler request construction with fewer headers
- Matches the actual browser behavior more closely
- Tests are simpler (assert on `data=` dict vs `files=` tuple structure)

### Negative

- Cannot easily upload files/attachments (would need multipart for that)
- Less explicit about content type being sent

## References

- httpx documentation on [request content](https://www.python-httpx.org/quickstart/#sending-form-encoded-data)
- Slack Web API uses form-urlencoded for most endpoints
- `post_message()` and `add_reaction()` functions in `yap_on_slack/post_messages.py`
