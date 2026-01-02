---
date: 2026-01-02
status: Accepted
---

# 0002: Multi-User YAML Configuration

## Context

The original implementation only supported a single Slack user via environment variables (`.env`). For realistic testing scenarios, we needed messages to appear from different users to simulate real team conversations rather than having all messages posted by the same account.

## Decision

We will support multiple Slack users through an optional `users.yaml` configuration file that is auto-loaded when present. The configuration supports:

- **Multiple users**: Each with their own `SLACK_XOXC_TOKEN` and `SLACK_XOXD_TOKEN`
- **Posting strategies**: `round_robin` (default) or `random` for distributing messages across users
- **Per-message user assignment**: Messages in `messages.json` can specify a `user` field to target a specific user
- **Fallback behavior**: The `.env` user is always available as "default" and serves as a fallback

Configuration structure in `users.yaml`:

```yaml
strategy: round_robin  # or "random"
users:
  - name: alice
    SLACK_XOXC_TOKEN: xoxc-...
    SLACK_XOXD_TOKEN: xoxd-...
  - name: bob
    SLACK_XOXC_TOKEN: xoxc-...
    SLACK_XOXD_TOKEN: xoxd-...
```

The `.env` user is merged into the users list with name "default" (or `SLACK_USER_NAME` if set), allowing backward compatibility.

## Alternatives Considered

### Alternative 1: JSON Configuration

Use `users.json` instead of YAML. Not chosen because YAML is more readable for configuration files and allows comments for documenting token sources.

### Alternative 2: Environment Variable Arrays

Use `SLACK_XOXC_TOKEN_1`, `SLACK_XOXC_TOKEN_2`, etc. Not chosen because it's harder to manage, doesn't allow naming users, and clutters the `.env` file.

### Alternative 3: Inline Configuration in messages.json

Embed user credentials directly in the messages file. Not chosen because it mixes content with credentials, making it harder to share message templates.

## Consequences

### Positive

- Messages appear from multiple users, creating realistic Slack conversations
- Backward compatible - existing `.env`-only setups continue to work
- `users.yaml` is gitignored by default, keeping credentials out of version control
- Strategies (round_robin/random) provide flexibility without per-message configuration

### Negative

- Additional configuration file to manage
- Users must extract session tokens for each Slack account they want to use
- Token expiration affects individual users, not the entire tool

## References

- PyYAML library for YAML parsing
- `users.yaml.example` for configuration template
- `.gitignore` updated to exclude `users.yaml` and `users.yml`
