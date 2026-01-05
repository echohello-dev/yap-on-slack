# yap-on-slack

🗣️ Simulate realistic Slack conversations for testing and demos

Post realistic support conversations to Slack with proper formatting, threading, and reactions. Perfect for testing chat interfaces, training support teams, or populating demo workspaces.

## Features

- 📝 **Rich text formatting** - Bold, italic, code, links, and emoji support
- 🧵 **Threaded conversations** - Replies automatically grouped in threads
- 👍 **Smart reactions** - Auto-add reactions based on message content
- 🤖 **AI message generation** - Use Gemini 3 Flash to create realistic conversations
- 🐙 **GitHub context** - Generate messages from real commits, PRs, and issues
- 🎨 **Beautiful terminal UI** - Progress tracking with rich output
- 🐳 **Docker ready** - Easy deployment with container support
- ⚙️ **Flexible configuration** - CLI arguments and JSON message definitions
- ✅ **Message validation** - Schema validation with Pydantic
- 🔒 **Multiple auth methods** - Session tokens, User OAuth, or Bot tokens
- 🔐 **SSL/TLS support** - Corporate proxy and self-signed certificate handling

## Quick Start

### Prerequisites

- Python 3.13+ or Docker
- [mise](https://mise.jdx.dev/) (recommended) or [uv](https://docs.astral.sh/uv/)
- Slack workspace credentials (see [Authentication](#authentication))

### Authentication

You'll need Slack credentials to post messages. We support multiple authentication methods:

- **Session Tokens** (xoxc/xoxd) - Quick setup, browser-based (expires frequently)
- **User OAuth Token** (xoxp) - Recommended for production use
- **Bot Token** (xoxb) - For bot-based workflows

📖 **See [docs/usage.md](docs/usage.md#authentication-setup)** for detailed setup instructions for each method.

⚠️ **Security**: Read [SECURITY.md](SECURITY.md) for important security considerations, especially for session tokens.

### Installation

**Option 1: Install via pipx (recommended)**

```bash
# Install globally with pipx
pipx install yap-on-slack

# Or install directly from GitHub
pipx install git+https://github.com/echohello-dev/yap-on-slack.git

# Initialize config file (creates ~/.config/yap-on-slack/config.yaml)
yos init

# Or create project-specific config in current directory
yos init --local  # Creates .yos.yaml

# Edit config with your credentials
# See docs/usage.md for how to obtain each value
nano ~/.config/yap-on-slack/config.yaml
# Or: nano .yos.yaml (if using --local)

# Run with default messages
yos run
```

**Option 2: Install via pip**

```bash
pip install yap-on-slack

# Or from GitHub
pip install git+https://github.com/echohello-dev/yap-on-slack.git

yos init && yos run
```

**Option 3: From source (development)**

```bash
# Clone the repository
git clone https://github.com/echohello-dev/yap-on-slack.git
cd yap-on-slack

# Install dependencies
mise run install

# Run with mise
mise run run
```

**CLI Aliases:** `yos`, `yaponslack`, `yap-on-slack`

## Usage

### Basic Commands

```bash
# Initialize config files (.env, users.yaml, messages.json)
yos init

# Post default messages
yos run

# Use custom messages file
yos run --messages custom.json

# Generate messages with AI (requires OPENROUTER_API_KEY)
yos run --use-ai

# Interactive channel selector
yos run --interactive

# Dry run (validate without posting)
yos run --dry-run

# Scan a channel and generate system prompts
yos scan --interactive
yos scan --channel-id C1234567890

# Limit messages and add delays
yos run --limit 5 --delay 3

# Verbose output for debugging
yos run --verbose

# Show version
yos --version
```

### CLI Commands

**`yos init`** - Initialize configuration files
- `--force, -f` - Overwrite existing files

**`yos run`** - Post messages to Slack
- `--config PATH` - Path to config.yaml file
- `--channel-id ID` - Override channel ID from config
- `--interactive, -i` - Interactive channel selector
- `--messages PATH` - Custom messages JSON file
- `--users PATH` - Custom users YAML config
- `--user NAME` - Force specific user for all messages
- `--use-ai` - Generate messages using OpenRouter Gemini 3 Flash
- `--dry-run` - Validate without posting to Slack
- `--limit N` - Post only first N messages
- `--delay SECONDS` - Delay between messages (default: 2.0)
- `--reply-delay SECONDS` - Delay between replies (default: 1.0)
- `--reaction-delay SECONDS` - Delay before reactions (default: 0.5)
- `--verbose, -v` - Enable debug logging
- `--debug-auth` - Print safe diagnostics on auth failures

**`yos version`** - Show version information

**`yos scan`** - Scan a Slack channel and generate system prompts
- `--channel-id ID` - Direct channel ID to scan
- `--interactive, -i` - Interactive channel selector
- `--limit N` - Maximum messages to fetch (default: 200)
- `--throttle SECONDS` - Delay between API batches (default: 0.5)
- `--output-dir PATH` - Output directory (default: ~/.config/yap-on-slack/scan/)
- `--model MODEL` - OpenRouter model (default: openrouter/auto)
- `--dry-run` - Fetch and analyze without generating prompts
- `--no-export-data` - Skip exporting raw messages to text file

Run `yos --help` or `yos run --help` for full options.

## AI Message Generation

Generate realistic conversations using OpenRouter's AI models with optional GitHub context:

1. **Get an OpenRouter API key**: https://openrouter.ai
2. **Add to config file** (`~/.config/yap-on-slack/config.yaml` or `.yos.yaml`):
   ```yaml
   ai:
     enabled: false  # Set to true or use --use-ai flag
     api_key: sk-or-v1-your-key-here
     model: openrouter/auto  # Auto-selects best model
     github:
       enabled: true
       token: ghp_your-token-here  # Optional, falls back to GITHUB_TOKEN env var
       limit: 5  # Max repos to fetch
   ```
   Or use environment variables:
   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-your-key-here
   export GITHUB_TOKEN=ghp_your-token-here  # Optional for GitHub context
   # SSL/TLS configuration (automatically respects Python's standard cert variables)
   export SSL_CERT_FILE=~/your-corporate-cert.pem  # Custom CA bundle
   export SSL_STRICT_X509=false  # Disable strict X509 (for corporate certs)
   # Or: REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE, SSL_CERT_DIR
   ```
3. **Run with AI**:
   ```bash
   yos run --use-ai
   yos run --use-ai --use-github  # Include GitHub context
   ```

When `--use-ai` is used:
- Fetches recent commits, PRs, and issues from your GitHub repositories
- Generates 20 realistic engineering team conversations
- Messages reference actual project context (repos, issues, PRs)
- Falls back to default messages if AI generation fails

## Custom Messages

Create `messages.json` with your conversation threads:

```json
[
  {
    "text": "*Deploy complete* :rocket: New API version is live!",
    "replies": [
      "Nice! Performance looks good",
      "All tests passing :white_check_mark:"
    ]
  },
  {
    "text": "Quick question - what's our policy on log retention?"
  }
]
```

**Supported formatting:** bold, italic, strikethrough, code, links, emoji, and bullet points.

📖 See [docs/usage.md](docs/usage.md#custom-messages) for complete formatting syntax and examples.

## Docker

```bash
# Build and run locally
docker build -t yap-on-slack .

# Mount config file from ~/.config
docker run --rm \
  -v ~/.config/yap-on-slack:/root/.config/yap-on-slack \
  yap-on-slack yos run

# Or use pre-built image from GitHub Container Registry
docker pull ghcr.io/echohello-dev/yap-on-slack:latest

# Mount config file
docker run --rm \
  -v ~/.config/yap-on-slack:/root/.config/yap-on-slack \
  ghcr.io/echohello-dev/yap-on-slack:latest yos run

# Or pass credentials via environment variables
docker run --rm \
  -e SLACK_XOXC_TOKEN="xoxc-..." \
  -e SLACK_XOXD_TOKEN="xoxd-..." \
  -e SLACK_ORG_URL="https://workspace.slack.com" \
  -e SLACK_CHANNEL_ID="C123" \
  -e SLACK_TEAM_ID="T123" \
  ghcr.io/echohello-dev/yap-on-slack:latest yos run
```

## Development

### Setup

```bash
# Install dependencies (including dev tools)
mise run install

# Install pre-commit hooks
uv run pre-commit install
```

### Available Commands

```bash
mise run lint       # Run ruff linter
mise run format     # Format code with ruff
mise run typecheck  # Run mypy type checking
mise run test       # Run pytest
mise run check      # Run all checks (lint + typecheck + test)
```

See all available tasks: `mise tasks`

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing procedures
- Pull request process

## Documentation

- **[docs/usage.md](docs/usage.md)** - Comprehensive usage guide, authentication setup, and troubleshooting
- **[SECURITY.md](SECURITY.md)** - Security best practices and token management
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines and workflow
- **[docs/adrs/](docs/adrs/)** - Architecture decision records

## CI/CD

- **Build Workflow** - Automated linting, type checking, testing, and Docker image publishing
- **Release Please** - Semantic versioning and automated changelog generation

Docker images: `ghcr.io/echohello-dev/yap-on-slack`

## License

MIT - See [LICENSE](LICENSE) for details

