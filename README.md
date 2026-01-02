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

```bash
# Clone the repository
git clone https://github.com/echohello-dev/yap-on-slack.git
cd yap-on-slack

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# See docs/usage.md for how to obtain each value
nano .env

# Install dependencies
mise run install

# Run with default messages
mise run run
```

## Usage

### Basic Commands

```bash
# Post default messages
mise run run

# Use custom messages file
mise run run -- --messages custom.json

# Generate messages with AI (requires OPENROUTER_API_KEY)
mise run run -- --use-ai

# Dry run (validate without posting)
mise run run -- --dry-run

# Limit messages and add delays
mise run run -- --limit 5 --delay 3

# Verbose output for debugging
mise run run -- --verbose
```

### CLI Options

- `--messages PATH` - Custom messages JSON file
- `--use-ai` - Generate messages using OpenRouter Gemini 3 Flash
- `--dry-run` - Validate without posting to Slack
- `--limit N` - Post only first N messages
- `--delay SECONDS` - Delay between messages (default: 2.0)
- `--reply-delay SECONDS` - Delay between replies (default: 1.0)
- `--reaction-delay SECONDS` - Delay before reactions (default: 0.5)
- `--verbose` - Enable debug logging

Run `mise run run -- --help` for full options.

## AI Message Generation

Generate realistic conversations using OpenRouter's Gemini 3 Flash model with optional GitHub context:

1. **Get an OpenRouter API key**: https://openrouter.ai
2. **Add to `.env`**:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   ```
3. **Optional: Add GitHub token for context**:
   ```bash
   GITHUB_TOKEN=ghp_your-token-here
   # Or use: gh auth token (if GitHub CLI installed)
   ```
4. **Run with AI**:
   ```bash
   mise run run -- --use-ai
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
docker run --rm --env-file .env yap-on-slack

# Or use pre-built image from GitHub Container Registry
docker pull ghcr.io/echohello-dev/yap-on-slack:latest
docker run --rm --env-file .env ghcr.io/echohello-dev/yap-on-slack:latest
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

