# AI Agent Instructions for yap-on-slack

## Purpose

Simulate realistic Slack messages in channels for testing purposes. Python CLI tool that posts messages with formatting, replies, and reactions.

## Architecture

Python CLI tool with:
- **yap_on_slack/cli.py** — CLI entry point (`yos`, `yaponslack`, `yap-on-slack`)
- **yap_on_slack/post_messages.py** — Core message posting logic
- **messages.json** (optional) — Custom message definitions
- **.env** — Slack credentials and configuration

## Installation

```bash
# Via pipx (recommended)
pipx install yap-on-slack

# Via pip
pip install yap-on-slack

# From GitHub URL
pipx install git+https://github.com/echohello-dev/yap-on-slack.git

# From source
mise run install
```

## Commands

**CLI commands** (after installation):

```bash
yos init            # Create config files (.env, users.yaml, messages.json)
yos run             # Post messages to Slack
yos run --dry-run   # Validate without posting
yos run --use-ai    # Generate AI messages
yos --version       # Show version
```

**Development commands** (use `mise run`):

```bash
mise run install    # Install dependencies with uv
mise run lint       # Run ruff linter
mise run format     # Format code with ruff
mise run test       # Run pytest
mise run run        # Execute message posting
mise run build      # Build Docker image
```

## Configuration

**Required environment variables** (in `.env`):
- `SLACK_XOXC_TOKEN` — Slack session token (xoxc-...)
- `SLACK_XOXD_TOKEN` — Slack session token (xoxd-...)
- `SLACK_ORG_URL` — Workspace URL (https://workspace.slack.com)
- `SLACK_CHANNEL_ID` — Target channel ID
- `SLACK_TEAM_ID` — Workspace team ID

## Message Format

Messages support markdown-like formatting:
- `*bold*` or `**bold**` — Bold text
- `_italic_` — Italic text
- `~strikethrough~` — Strikethrough
- `` `code` `` — Inline code
- `<url|label>` — Links with labels
- `:emoji_name:` — Emoji (e.g., :rocket:, :warning:)
- `•` or `- ` — Bullet points

**Custom messages**: Create `messages.json` with array of message objects:
```json
[
  {
    "text": "Main message with *formatting*",
    "replies": ["First reply", "Second reply"]
  }
]
```

## Tech Stack

- **Python 3.13** — Latest Python version
- **httpx** — Async HTTP client for Slack API
- **rich** — Terminal UI with progress bars
- **python-dotenv** — Environment configuration
- **ruff** — Fast linting and formatting

## Docker

Build and run in container:
```bash
docker build -t yap-on-slack .
docker run --rm --env-file .env yap-on-slack
```

Published to GHCR: `ghcr.io/echohello-dev/yap-on-slack:latest`

## Development

1. Run `yos init` to create config files (or copy `.env.example` to `.env`)
2. Edit `.env` and add credentials
3. Run `mise run install` to install dependencies (from source)
4. Run `yos run` or `mise run run` to post messages
5. Use `mise run lint` before committing

**Note**: This uses Slack session tokens (xoxc/xoxd), not bot tokens. Extract from browser dev tools.
