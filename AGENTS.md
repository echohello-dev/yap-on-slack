# AI Agent Instructions for yap-on-slack

## Purpose

Simulate realistic Slack messages in channels for testing purposes. Python CLI tool that posts messages with formatting, replies, and reactions.

## Architecture

Python CLI tool with:
- **yap_on_slack/cli.py** — CLI entry point (`yos`, `yaponslack`, `yap-on-slack`)
- **yap_on_slack/post_messages.py** — Core message posting logic
- **config.yaml** — Unified configuration file (workspace, credentials, users, messages, AI settings)
- **schema/config.schema.json** — JSON Schema for config validation
- **config.yaml.example** — Configuration template

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
yos init            # Create config.yaml in ~/.config/yap-on-slack/ (default)
yos init --local    # Create config.yaml in current directory
yos run             # Post messages to Slack
yos run -i          # Interactive channel selector
yos run --dry-run   # Validate without posting
yos run --use-ai    # Generate AI messages
yos scan -i         # Scan channel interactively and generate system prompts
yos scan --channel-id C123  # Scan specific channel
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

**Primary configuration file**: `config.yaml`

Config file discovery order:
1. `--config` flag (explicit path)
2. `./config.yaml` (current directory)
3. `~/.config/yap-on-slack/config.yaml` (XDG home directory)

**Config file structure**:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/echohello-dev/yap-on-slack/main/schema/config.schema.json

# Workspace settings (required)
workspace:
  org_url: https://your-workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

# Default credentials (required if no users array)
credentials:
  xoxc_token: xoxc-your-token-here
  xoxd_token: xoxd-your-token-here
  cookies: ""  # optional

# User selection strategy
user_strategy: round_robin  # round_robin | random

# Additional users (optional)
users:
  - name: alice
    xoxc_token: xoxc-alice-token
    xoxd_token: xoxd-alice-token
  - name: bob
    xoxc_token: xoxc-bob-token
    xoxd_token: xoxd-bob-token

# Messages to post (optional, can also use --use-ai)
messages:
  - text: "Good morning team! :wave:"
    user: alice  # optional
    replies:
      - "Hey! Ready for standup?"
      - text: "Morning everyone"
        user: bob
    reactions:
      - wave
      - coffee

# AI message generation
ai:
  enabled: false
  model: openrouter/auto  # Auto-selects best model (recommended)
  # See top weekly models: https://openrouter.ai/models?order=top-weekly
  api_key: ""  # or use OPENROUTER_API_KEY env var
  temperature: 0.7
  max_tokens: 4000
  # system_prompt: |  # Optional: custom prompt (overrides default)
  #   Generate realistic Slack messages...

# Channel scanning settings (for `yos scan` command)
scan:
  limit: 200                                # Max messages to fetch (10-5000)
  throttle: 0.5                             # Delay between API batches in seconds
  output_dir: ~/.config/yap-on-slack/scan   # Where to save prompts and exports
  model: openrouter/auto                    # Model for prompt generation
  export_data: true                         # Export messages to text file
```

**Environment variables** (override config file):
- `SLACK_XOXC_TOKEN` — Session token (overrides credentials.xoxc_token)
- `SLACK_XOXD_TOKEN` — Session token (overrides credentials.xoxd_token)
- `SLACK_ORG_URL` — Workspace URL (overrides workspace.org_url)
- `SLACK_CHANNEL_ID` — Channel ID (overrides workspace.channel_id)
- `SLACK_TEAM_ID` — Team ID (overrides workspace.team_id)
- `OPENROUTER_API_KEY` — AI API key (overrides ai.api_key)
- `GITHUB_TOKEN` — GitHub token for context (optional)

**Legacy support**: `.env` files in the config directory are still loaded and merged with config.yaml. Environment variables take precedence.

## Message Format

Messages support markdown-like formatting:
- `*bold*` or `**bold**` — Bold text
- `_italic_` — Italic text
- `~strikethrough~` — Strikethrough
- `` `code` `` — Inline code
- `<url|label>` — Links with labels
- `:emoji_name:` — Emoji (e.g., :rocket:, :warning:)
- `•` or `- ` — Bullet points

Messages can be defined in:
1. **config.yaml** `messages:` array
2. **Custom JSON file** via `--messages` flag
3. **AI generation** via `--use-ai` flag
4. **Default fallback messages** (built-in)

## Tech Stack

- **Python 3.13** — Latest Python version
- **httpx** — Async HTTP client for Slack API
- **pydantic** — Configuration validation
- **platformdirs** — Cross-platform config directory resolution
- **rich** — Terminal UI with progress bars
- **python-dotenv** — Environment configuration
- **pyaml** — YAML configuration parsing
- **ruff** — Fast linting and formatting

## Docker

Build and run in container:
```bash
docker build -t yap-on-slack .
docker run --rm -v ~/.config/yap-on-slack:/config -e CONFIG_PATH=/config/config.yaml yap-on-slack
```

Published to GHCR: `ghcr.io/echohello-dev/yap-on-slack:latest`

## Development

1. Run `yos init` to create config.yaml (or `yos init --local` for CWD)
2. Edit config file and add workspace settings + credentials
3. Run `mise run install` to install dependencies (from source)
4. Run `yos run` or `mise run run` to post messages
5. Use `mise run lint` before committing

**Note**: This uses Slack session tokens (xoxc/xoxd), not bot tokens. Extract from browser dev tools.
