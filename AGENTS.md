# AI Agent Instructions for yap-on-slack

## Purpose

Simulate realistic Slack messages in channels for testing purposes. Python CLI tool that posts messages with formatting, replies, and reactions.

## Key Files & Architecture

- **yap_on_slack/cli.py** — CLI entry point
- **yap_on_slack/post_messages.py** — Core message posting logic
- **yap_on_slack/prompts/** — AI system prompt templates
- **config.yaml** — Unified configuration file
- **schema/config.schema.json** — JSON Schema for validation
- **Tech stack**: Python 3.13, httpx, pydantic, rich

## Quick Reference

**For detailed information, refer to:**
- **[docs/usage.md](docs/usage.md)** — Complete usage guide, authentication setup, troubleshooting
- **[README.md](README.md)** — Installation, features, quick start
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development guidelines
- **[docs/adrs/](docs/adrs/)** — Architecture decisions

## Essential Commands

```bash
# Installation
pipx install yap-on-slack                  # Install globally
mise run install                           # Install from source

# Configuration
yos init                                   # Create config in ~/.config/yap-on-slack/
yos init --local                           # Create .yos.yaml in current directory

# Running
yos run                                    # Post messages
yos run -i                                 # Interactive channel selector
yos run --dry-run                          # Validate without posting
yos run --use-ai                           # Generate AI messages
yos run --use-ai --use-github              # Generate AI messages with GitHub context
yos run --use-ai --github-token <token>    # Use specific GitHub token
yos run --use-ai --github-limit 10         # Fetch up to 10 repos
yos scan -i                                # Scan channel and generate prompts

# Development (use mise run)
mise run lint                              # Run ruff linter
mise run format                            # Format code
mise run test                              # Run pytest
```

## Configuration Essentials

**Config file locations** (priority order):
1. `--config` flag → 2. `.yos.yaml` → 3. `config.yaml` → 4. `~/.config/yap-on-slack/config.yaml`

**Minimal config structure** (see config.yaml.example for full details):
```yaml
workspace:
  org_url: https://workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-token-here
  xoxd_token: xoxd-token-here

# Optional: AI settings with GitHub integration
ai:
  openrouter_api_key: your-key-here
  model: anthropic/claude-3-sonnet
  github:
    enabled: true
    token: ghp_xxxxxxxxxxxx  # optional, falls back to env var
    limit: 5                  # max repos to fetch
    include_commits: true
    include_prs: true
    include_issues: true

# Alternatively, GitHub config can be at top level:
github:
  enabled: true
  token: ghp_xxxxxxxxxxxx
  limit: 5
  include_commits: true
  include_prs: true
  include_issues: true

# Optional: multiple users, messages
# See config.yaml.example for full structure
```

**Environment variables override config:**
- `SLACK_XOXC_TOKEN`, `SLACK_XOXD_TOKEN`
- `SLACK_ORG_URL`, `SLACK_CHANNEL_ID`, `SLACK_TEAM_ID`
- `OPENROUTER_API_KEY`, `GITHUB_TOKEN`

## When Working on This Project

1. **Read relevant docs first**: Check docs/usage.md for detailed behavior
2. **Check ADRs**: Review docs/adrs/ for architectural decisions
3. **Use mise**: Prefer `mise run <task>` for common operations
4. **Follow CONTRIBUTING.md**: Development guidelines and workflow
5. **Test changes**: Use `mise run test` and `yos run --dry-run`

### When Adding New Features

1. **Implement the feature** with proper type hints and error handling
2. **Run linter**: `mise run lint` (fix any issues)
3. **Run tests**: `mise run test` (ensure all tests pass)
4. **Update documentation**:
   - Update [README.md](README.md) if user-facing feature
   - Update [docs/usage.md](docs/usage.md) for detailed usage/troubleshooting
   - Update [config.yaml.example](config.yaml.example) for new config options
   - Update [schema/config.schema.json](schema/config.schema.json) if adding/modifying config fields
   - Consider adding ADR to [docs/adrs/](docs/adrs/) for significant decisions
5. **Test end-to-end**: `yos run --dry-run` to validate integration

**Note**: This tool uses Slack session tokens (xoxc/xoxd) extracted from browser dev tools, not bot tokens. See [docs/usage.md](docs/usage.md#authentication-setup) for extraction details.

