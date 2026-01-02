# yap-on-slack

🗣️🗣️🗣️ Simulate realistic messages in Slack channels for testing purposes

Post realistic support conversations to Slack with proper formatting, threading, and reactions. Perfect for testing chat interfaces, training support teams, or populating demo workspaces.

## Features

- 📝 Rich text formatting (bold, italic, code, links, emoji)
- 🧵 Threaded conversations with replies
- 👍 Automatic reactions based on message content
- 🎨 Beautiful terminal UI with progress tracking
- 🐳 Docker support for easy deployment
- ⚙️ Customizable messages via JSON

## Quick Start

### Prerequisites

- Python 3.13+ or Docker
- [mise](https://mise.jdx.dev/) (recommended) or uv
- Slack session tokens (xoxc and xoxd)

### Getting Slack Tokens

1. Open Slack in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Send a message in any channel
5. Find a request to `api/` endpoints
6. Look in Cookies for:
   - `d` cookie → `SLACK_XOXD_TOKEN`
   - `token` in form data → `SLACK_XOXC_TOKEN`

### Installation

```bash
# Clone the repo
git clone https://github.com/echohello-dev/yap-on-slack.git
cd yap-on-slack

# Copy environment template
cp .env.example .env

# Edit .env with your tokens
# SLACK_XOXC_TOKEN=xoxc-...
# SLACK_XOXD_TOKEN=xoxd-...
# SLACK_ORG_URL=https://your-workspace.slack.com
# SLACK_CHANNEL_ID=C1234567890
# SLACK_TEAM_ID=T1234567890

# Install dependencies
mise run install

# Run it!
mise run run
```

### Using Docker

```bash
# Build image
docker build -t yap-on-slack .

# Run with your .env file
docker run --rm --env-file .env yap-on-slack

# Or pull from GHCR
docker pull ghcr.io/echohello-dev/yap-on-slack:latest
docker run --rm --env-file .env ghcr.io/echohello-dev/yap-on-slack:latest
```

## Custom Messages

Create a `messages.json` file to define your own conversations:

```json
[
  {
    "text": "*Deploy complete* :rocket: New API version is live!",
    "replies": [
      "Nice! Performance looks good",
      "All tests passing :white_check_mark:"
    ]
  }
]
```

See [messages.json.example](messages.json.example) for more examples.

### Formatting Support

- `*bold*` or `**bold**` - Bold text
- `_italic_` - Italic text
- `~strikethrough~` - Strikethrough
- `` `code` `` - Inline code
- `<https://example.com|label>` - Links with labels
- `:emoji_name:` - Emoji (e.g., :rocket:, :warning:)
- `•` or `- ` - Bullet points

## Development

```bash
# Install dependencies
mise run install

# Lint code
mise run lint

# Format code
mise run format

# Run tests
mise run test
```

## Available Commands

See all available commands with mise:

```bash
mise tasks
```

Key commands:
- `mise run install` - Install dependencies
- `mise run run` - Post messages to Slack
- `mise run lint` - Run linter
- `mise run format` - Format code
- `mise run test` - Run tests
- `mise run build` - Build Docker image

## CI/CD

This repo includes:
- **Build workflow** - Lints, tests, and publishes Docker images to GHCR
- **Release Please** - Automated semantic versioning and changelogs

Images are published to: `ghcr.io/echohello-dev/yap-on-slack`

## License

MIT

## Contributing

PRs welcome! Please run `mise run lint` and `mise run format` before submitting.

