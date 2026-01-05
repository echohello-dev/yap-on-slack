# Usage Guide & Troubleshooting

## Table of Contents

- [Authentication Setup](#authentication-setup)
- [Getting Slack Credentials](#getting-slack-credentials)
- [Configuration](#configuration)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Common Issues](#common-issues)

## Authentication Setup

Open up your Slack in your browser and login.

> **Note**: This tool uses Slack *session tokens* from your browser session: `xoxc-*` plus the `d` cookie value (often starts with `xoxd-*`).

### Option 1: Using Session Tokens (Browser-based)

⚠️ **Security Warning**: Session tokens are less secure and expire frequently. See [SECURITY.md](../SECURITY.md) for important security considerations.

#### Lookup `SLACK_XOXC_TOKEN`

- Open your browser's Developer Console.
- In Firefox, under `Tools -> Browser Tools -> Web Developer tools` in the menu bar
- In Chrome, click the "three dots" button to the right of the URL Bar, then select
  `More Tools -> Developer Tools`
- Switch to the console tab.
- Type "allow pasting" and press ENTER.
- Paste the following snippet and press ENTER to execute:
  ```javascript
  JSON.parse(localStorage.localConfig_v2).teams[document.location.pathname.match(/^\/client\/([A-Z0-9]+)/)[1]].token
  ```

Token value is printed right after the executed command (it starts with
`xoxc-`), save it somewhere for now.

#### Lookup `SLACK_XOXD_TOKEN`

- Switch to "Application" tab and select "Cookies" in the left navigation pane.
- Find the cookie with the name `d`.  That's right, just the letter `d`.
- Double-click the Value of this cookie.
- Press Ctrl+C or Cmd+C to copy it's value to clipboard.
- Save it for later.

### Option 2: Using User OAuth Token (Recommended)

Instead of using browser-based tokens (`xoxc`/`xoxd`), you can use a User OAuth token:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under "OAuth & Permissions", add the following scopes:
    - `channels:history` - View messages in public channels
    - `channels:read` - View basic information about public channels
    - `groups:history` - View messages in private channels
    - `groups:read` - View basic information about private channels
    - `im:history` - View messages in direct messages
    - `im:read` - View basic information about direct messages
    - `im:write` - Start direct messages with people on a user's behalf
    - `mpim:history` - View messages in group direct messages
    - `mpim:read` - View basic information about group direct messages
    - `mpim:write` - Start group direct messages with people on a user's behalf
    - `users:read` - View people in a workspace
    - `chat:write` - Send messages on a user's behalf
    - `search:read` - Search a workspace's content

3. Install the app to your workspace
4. Copy the "User OAuth Token" (starts with `xoxp-`)

#### App manifest (preconfigured scopes)

To create the app from a manifest with permissions preconfigured, use the following code snippet:

```json
{
    "display_information": {
        "name": "Slack MCP"
    },
    "oauth_config": {
        "scopes": {
            "user": [
                "channels:history",
                "channels:read",
                "groups:history",
                "groups:read",
                "im:history",
                "im:read",
                "im:write",
                "mpim:history",
                "mpim:read",
                "mpim:write",
                "users:read",
                "chat:write",
                "search:read"
            ]
        }
    },
    "settings": {
        "org_deploy_enabled": false,
        "socket_mode_enabled": false,
        "token_rotation_enabled": false
    }
}
```

### Option 3: Using Bot Token

You can also use a Bot token instead of a User token:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Under "OAuth & Permissions", add Bot Token Scopes (same as User scopes above, except `search:read`)
3. Install the app to your workspace
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
5. **Important**: Bot must be invited to channels for access

> **Note**: Bot tokens cannot use `search.messages` API, so some search functionality may be limited.

## Getting Slack Credentials

### Finding Your Channel ID

**Method 1: Via Slack App/Web**

1. Open Slack and navigate to the channel
2. Click the channel name at the top
3. Scroll down in the "About" tab
4. Look for "Channel ID" at the bottom (copy the ID)

**Method 2: Via URL**

1. Open the channel in your browser
2. Look at the URL: `https://workspace.slack.com/archives/C01234ABC56`
3. The Channel ID is the part after `/archives/` (e.g., `C01234ABC56`)

**Method 3: Via API Inspector**

1. Open Developer Tools (`F12`)
2. Go to Network tab
3. Post a message in the channel
4. Find the `chat.postMessage` request
5. Look for `channel` parameter in the request payload

### Finding Your Team ID

**Method 1: Via DevTools Console (recommended)**

1. Open Slack in your browser: `https://your-workspace.slack.com`
2. Open Developer Tools → **Console**
3. Run:
   ```js
   window.boot_data.team_id
   ```
4. Copy the value (it starts with `T`)

**Method 2: Via API Inspector**

1. Open Developer Tools (`F12`)
2. Go to Network tab
3. Look at any API request
4. Find the Team ID in request headers or payload (starts with `T`)

### Extracting Session Tokens

⚠️ **Important**: Read [SECURITY.md](../SECURITY.md) before extracting tokens!

**Step-by-Step Guide:**

1. **Open Slack in Browser** (not desktop app)
   - Use Chrome, Firefox, or Safari
   - Log in to your workspace

2. **Open Developer Tools**
   - Chrome/Firefox: Press `F12` or `Cmd+Option+I` (Mac)
   - Safari: Enable Developer Menu first in Preferences

3. **Go to Network Tab**
   - Clear existing requests (trash icon)
   - Filter by "XHR" or "Fetch"

4. **Trigger an Action**
   - Send a message in any channel
   - Or navigate to different channels

5. **Find API Request**
   - Look for requests to `https://[workspace].slack.com/api/`
   - Click on any `chat.postMessage` or similar request

6. **Extract xoxc Token**
   - Go to "Headers" or "Payload" tab
   - Find `token` field with value starting with `xoxc-`
   - Copy the full token

7. **Extract xoxd Token**
   - Go to "Cookies" tab
   - Find cookie named `d`
   - Copy the value (starts with `xoxd-`)

8. **Get Workspace URL**
   - Just your workspace URL: `https://your-workspace.slack.com`

## Configuration

> **Important**: This tool uses **config.yaml** for all configuration, NOT `.env` files. Config files use YAML format and support workspace settings, credentials, multi-user setup, AI settings, and more.

### Config File Locations

Yap on Slack uses **YAML configuration** (`config.yaml` or `.yos.yaml`). Config files are discovered in this priority order:

1. **`--config` flag** (explicit path from command line)
2. **`.yos.yaml`** (current directory - highest priority, use with `--local`)
3. **`config.yaml`** (current directory)
4. **`~/.config/yap-on-slack/config.yaml`** (XDG home directory - default)

**Initialize configuration:**

```bash
# Create ~/.config/yap-on-slack/config.yaml (default XDG location)
yos init

# Create .yos.yaml in current directory (project-specific, highest priority)
yos init --local

# Force overwrite existing config
yos init --force

# View config template
yos show-config

# View JSON schema
yos show-schema
```

### Configuration File Structure

Create `config.yaml` with the following structure:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/echohello-dev/yap-on-slack/main/schema/config.schema.json

# Workspace settings (required)
workspace:
  org_url: https://your-workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

# Default credentials (required)
credentials:
  xoxc_token: xoxc-your-token-here
  xoxd_token: xoxd-your-token-here
  cookies: ""  # optional: additional cookies if needed (e.g., "x=...; d-s=...")

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
  # See models: https://openrouter.ai/models?order=top-weekly
  api_key: ""  # or use OPENROUTER_API_KEY env var
  temperature: 0.7
  max_tokens: 4000
  # system_prompt: |  # Optional: override default prompt
  #   Your custom system prompt here
  # Default: yap_on_slack/prompts/generate_messages.txt
  
  # GitHub context integration (optional)
  github:
    enabled: true  # Enable GitHub context when available
    token: ""  # Optional: explicit GitHub token (overrides GITHUB_TOKEN env var)
    limit: 5  # Max repositories to fetch from
    include_commits: true  # Include recent commits
    include_prs: true  # Include recent PRs
    include_issues: true  # Include recent issues

# Channel scanning settings (for `yos scan` command)
scan:
  limit: 200                                # Max messages to fetch (10-5000)
  throttle: 0.5                             # Delay between API batches in seconds
  output_dir: ~/.config/yap-on-slack/scan   # Where to save prompts
  model: openrouter/auto                    # LLM for prompt generation
  export_data: true                         # Export messages to text file
  # Default system prompt: yap_on_slack/prompts/generate_channel_prompts.txt

# GitHub integration (top-level, optional)
github:
  enabled: true  # Enable GitHub context globally
  token: ""  # Optional: explicit GitHub token
  limit: 5  # Max repositories to fetch from
  include_commits: true
  include_prs: true
  include_issues: true
```

### Environment Variables

Environment variables **override** config file settings. This is useful for CI/CD, Docker, or temporary overrides without editing config files:

```bash
# Workspace settings (override workspace: section in config.yaml)
export SLACK_ORG_URL=https://your-workspace.slack.com
export SLACK_CHANNEL_ID=C01234ABC56
export SLACK_TEAM_ID=T01234ABC56

# Credentials (override credentials: section in config.yaml)
export SLACK_XOXC_TOKEN=xoxc-...
export SLACK_XOXD_TOKEN=xoxd-...

# AI generation (override ai: section in config.yaml)
export OPENROUTER_API_KEY=sk-or-v1-...

# GitHub integration (override github: section in config.yaml)
export GITHUB_TOKEN=ghp_...  # For AI to reference your repos

# SSL/TLS (standard environment variables - automatically detected)
export SSL_CERT_FILE=~/your-corporate-cert.pem       # CA bundle (highest priority)
export REQUESTS_CA_BUNDLE=~/your-corporate-cert.pem  # requests library
export CURL_CA_BUNDLE=~/your-corporate-cert.pem      # curl
export SSL_CERT_DIR=/etc/ssl/certs                   # CA certificate directory
export SSL_STRICT_X509=false                         # Control strict X509 verification (true/false)

# Optional
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

> **Note**: Environment variables take precedence over config file values. Standard SSL environment variables (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `SSL_CERT_DIR`) are automatically detected without additional configuration. When a custom CA bundle is detected, strict X509 verification is automatically disabled (Python 3.13+ compatibility for corporate proxies).

### Multi-user Configuration

To post messages as different users (different browser sessions), define them in `config.yaml`:

```yaml
user_strategy: round_robin  # or "random"

users:
  - name: alice
    xoxc_token: xoxc-alice-token
    xoxd_token: xoxd-alice-token
  - name: bob
    xoxc_token: xoxc-bob-token
    xoxd_token: xoxd-bob-token
```

**How user selection works:**

1. If `--user <name>` is passed on command line, that user is used for all messages
2. If a message has `user: <name>`, that user posts it
3. Otherwise, the configured **strategy** determines the poster:
   - `round_robin` (default): cycles through users in order (user 0, 1, 2, 0, ...)
   - `random`: picks a random user for each message

**Notes:**
- The credentials user is added as "default" to the user list
- If `SLACK_XOXD_TOKEN` contains URL-encoded characters (e.g., `%2F`), keep as-is - the script handles it
- Each user can have optional `cookies` field for extra session cookies

### Custom Messages

Define messages directly in `config.yaml` under `messages:` or use a separate JSON file:

```json
[
  {
    "text": "Main message with *bold* and _italic_",
    "user": "alice",
    "replies": [
      "First reply",
      {"text": "Second reply (as bob)", "user": "bob"}
    ],
    "reactions": ["thumbsup", "thinking_face"]
  },
  {
    "text": "Message without explicit user - uses round-robin strategy"
  }
]
```

**Message fields:**
- `text` (required): Message content
- `user` (optional): Which user posts it (must exist in config)
- `replies` (optional): Array of reply messages (same structure as messages)
- `reactions` (optional): Array of emoji names to react with

**Supported Formatting:**

- `*bold*` or `**bold**` → Bold text
- `_italic_` → Italic text
- `~strikethrough~` → Strikethrough
- `` `code` `` → Inline code
- `<url|label>` → Link with label
- `:emoji_name:` → Emoji (e.g., `:rocket:`, `:warning:`)
- `•` or `- ` → Bullet points

## Installation

### Install via pipx (recommended)

```bash
# Install globally
pipx install yap-on-slack

# Or directly from GitHub
pipx install git+https://github.com/echohello-dev/yap-on-slack.git

# Initialize config files
yos init

# Run
yos run
```

### Install via pip

```bash
pip install yap-on-slack

# Or from GitHub
pip install git+https://github.com/echohello-dev/yap-on-slack.git

yos init && yos run
```

### From source

```bash
git clone https://github.com/echohello-dev/yap-on-slack.git
cd yap-on-slack
mise run install
mise run run
```

**CLI aliases:** `yos`, `yaponslack`, `yap-on-slack` - all work identically.

## Usage Examples

### Initialize Configuration

```bash
# Create ~/.config/yap-on-slack/config.yaml (XDG default, recommended)
yos init

# Create .yos.yaml in current directory (project-specific, higher priority)
yos init --local

# View config template without creating file
yos show-config

# View JSON schema for validation
yos show-schema

# Edit the created config file (choose one based on what you created)
nano ~/.config/yap-on-slack/config.yaml  # For default location
# OR
nano .yos.yaml  # For project-specific config

# Config files use YAML format - see template for all available options:
# - workspace: (org_url, channel_id, team_id)
# - credentials: (xoxc_token, xoxd_token)
# - users: (multi-user setup)
# - messages: (custom messages)
# - ai: (AI generation settings with GitHub integration)
# - scan: (channel scanning settings)
# - ssl: (SSL/TLS settings for corporate proxies)
```

### Basic Usage

```bash
# Post messages from config.yaml/messages section
yos run

# Or with mise (from source)
mise run run
```

### Interactive Channel Selection

```bash
# Choose channel interactively before running
yos run -i

# Or choose with scan command
yos scan -i
```

### Dry Run (Validate Without Posting)

```bash
# Test configuration and message validation
yos run --dry-run

# With verbose logging to see all details
yos run --dry-run --verbose
```

### Limit Number of Messages

```bash
# Post only first 3 messages
yos run --limit 3

# Useful for testing
yos run --limit 1 --dry-run
```

### Custom Delays

```bash
# Slower posting (5s between messages)
yos run --delay 5

# Faster replies (0.5s between)
yos run --reply-delay 0.5

# Instant reactions
yos run --reaction-delay 0.1

# Combine all
yos run --delay 3 --reply-delay 1.5 --reaction-delay 0.8
```

### Verbose Logging

```bash
# Enable debug logging
yos run --verbose

# See detailed HTTP requests and responses
yos run --verbose --dry-run
```

### AI-Generated Messages

Generate realistic, varied Slack conversations using AI (requires OpenRouter API key):

```bash
# Generate and post AI messages with default model
yos run --use-ai

# Use specific LLM model
yos run --use-ai --model google/gemini-2.5-flash

# Include GitHub context (commits, PRs, issues)
yos run --use-ai --use-github

# Use specific GitHub token
yos run --use-ai --github-token ghp_xxxxxxxxxxxx

# Limit GitHub context to 10 repos
yos run --use-ai --github-limit 10

# Combine all options
yos run --use-ai --model grok-2 --use-github --github-limit 5 --limit 10 --dry-run
```

**Setup:**
1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Add to config file or environment:
   ```yaml
   ai:
     enabled: false
     model: openrouter/auto
     api_key: sk-or-v1-...
     # GitHub context integration
     github:
       enabled: true
       token: ""  # Optional: explicit token
       limit: 5
       include_commits: true
       include_prs: true
       include_issues: true
   ```
   Or:
   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-...
   export GITHUB_TOKEN=ghp_...
   ```

**What AI generates:**
- **Varied tones**: From casual ("yo anyone know why ci is failing lol") to formal announcements ("[ACTION REQUIRED]...")
- **Varied lengths**: One-word reactions (":+1:", "thx") to detailed bug reports with code blocks
- **GitHub-aware**: References real PRs, commits, and issues from your repos
- **Workflow errors**: Realistic CI/CD failures, build errors, deployment issues
- **Rich formatting**: Bullet points, numbered lists, code blocks, blockquotes, slackmoji
- **Natural conversations**: Multi-reply threads with debugging back-and-forth
- **Reactions**: AI suggests appropriate emoji reactions for messages

**GitHub Context Integration:**
When enabled with `--use-github` or `github.enabled: true` in config:
- Fetches recent commits from your repositories
- Includes PR titles, numbers, and states
- Adds issue titles, labels, and status
- References actual GitHub URLs in generated messages
- Uses explicit GitHub token if provided, otherwise tries `gh CLI` or `GITHUB_TOKEN` env var

**GitHub Control Options:**
- `--use-github` — Enable GitHub context (requires token)
- `--github-token <token>` — Use specific GitHub token (overrides env var and gh CLI)
- `--github-limit <count>` — Max repos to fetch (default: 5)

Configure GitHub behavior in `config.yaml`:
```yaml
ai:
  github:
    enabled: true                # Enable/disable GitHub context
    token: ""                    # Optional explicit token
    limit: 5                     # Max repositories
    include_commits: true        # Include commits
    include_prs: true           # Include PRs
    include_issues: true        # Include issues
```

**GitHub Context:**
If you have `gh` CLI installed and authenticated, or set `GITHUB_TOKEN`, the AI will reference your actual repositories:
- Recent commits and their messages
- Open/merged PRs with links
- Issues with labels and status
- Workflow run failures

```bash
# Check if gh is authenticated
gh auth status

# Or set token explicitly
export GITHUB_TOKEN=ghp_...
```

### Channel Scanning (Generate System Prompts)

Scan a channel to analyze message patterns and generate system prompts:

```bash
# Scan channel interactively
yos scan -i

# Scan specific channel
yos scan --channel-id C123ABC

# Use specific LLM for analysis
yos scan --channel-id C123ABC --model grok-2

# Configure scan settings in config.yaml
# scan:
#   limit: 200
#   throttle: 0.5
#   output_dir: ~/.config/yap-on-slack/scan
#   model: openrouter/auto
#   export_data: true
```

### Auth Debugging (safe/redacted)

If you are seeing `invalid_auth` errors, get safe diagnostics (no tokens printed):

```bash
yos run --limit 1 --debug-auth
```

This prints:
- Workspace host, team/channel IDs
- Whether the cookie `d` value looks like an `xoxd-` and its length
- Slack response `error` and request ID headers

### Multi-user Posting

Post as different users:

```bash
# Force all messages as specific user
yos run --user alice

# Or let config.yaml user_strategy handle it
yos run  # Uses round_robin or random

# Edit config.yaml to define users:
# users:
#   - name: alice
#     xoxc_token: xoxc-...
#     xoxd_token: xoxd-...
#   - name: bob
#     xoxc_token: xoxc-...
#     xoxd_token: xoxd-...
```

### Combined Examples

```bash
# Test run with limits and verbose output
yos run --limit 2 --dry-run --verbose

# Production run with slower delays
yos run --delay 5 --reply-delay 2 --reaction-delay 1

# AI-generated messages with specific model and preview
yos run --use-ai --model openrouter/auto --limit 5 --dry-run

# Scan and analyze channel for patterns
yos scan --channel-id C123ABC --model grok-2
```

## Troubleshooting

### Config File Not Found

**Error:** `Config file not found` or unable to find `config.yaml`

**Causes:**
- Config file not initialized
- Wrong directory (if using `.yos.yaml`)
- Typo in config path

**Solutions:**
```bash
# Initialize default config in ~/.config/yap-on-slack/
yos init

# Or create project-specific config
yos init --local

# Check config file exists
ls -la ~/.config/yap-on-slack/config.yaml
# or
ls -la .yos.yaml

# List where tool looks for config (priority order):
# 1. --config flag (if provided)
# 2. ./.yos.yaml (current directory)
# 3. ./config.yaml (current directory)
# 4. ~/.config/yap-on-slack/config.yaml (XDG default)
```

### Config Validation Errors

**Error:** `Config validation error` or `Invalid config format`

**Causes:**
- Invalid YAML syntax
- Missing required fields (workspace, credentials)
- Invalid field values

**Solutions:**
```bash
# Validate YAML syntax
cat ~/.config/yap-on-slack/config.yaml | yaml lint

# Check required fields exist
grep -E "org_url|channel_id|team_id" ~/.config/yap-on-slack/config.yaml

# Use example as template
cat yap_on_slack/templates/config.yaml.template

# Check schema is correct
# See: https://github.com/echohello-dev/yap-on-slack/blob/main/schema/config.schema.json
```

#### 1. Authentication Errors

**Error:** `invalid_auth` or HTTP 401

**Causes:**
- Tokens expired (session tokens expire after hours/days)
- Wrong tokens copied
- Tokens from different workspace
- Wrong `SLACK_TEAM_ID`
- Credentials not in config file

**Solutions:**
```bash
# Verify config file has credentials
grep -A3 "credentials:" ~/.config/yap-on-slack/config.yaml

# Extract fresh tokens from browser
# See "Extracting Session Tokens" section above

# Verify tokens in config are correct
nano ~/.config/yap-on-slack/config.yaml

# Check environment variables (take precedence)
echo $SLACK_XOXC_TOKEN
echo $SLACK_XOXD_TOKEN

# Test with dry-run first
yos run --dry-run

# If live posting fails, run with safe diagnostics
yos run --limit 1 --debug-auth

# Test with a single user explicitly
yos run --limit 1 --user default --debug-auth
```

**Technical note:** The script uses `application/x-www-form-urlencoded` encoding for Slack API requests. This is required for session token authentication - multipart/form-data encoding causes `invalid_auth` errors. See [ADR-0003](adrs/0003-slack-api-form-urlencoded.md) for details.

#### 2. Channel Not Found

**Error:** `channel_not_found`

**Causes:**
- Wrong Channel ID
- Bot/user doesn't have access to channel
- Private channel without membership

**Solutions:**
```bash
# Verify Channel ID
# Must start with 'C' (public) or 'G' (private)
echo $SLACK_CHANNEL_ID

# Check you're a member of the channel
# Navigate to channel in Slack UI first

# Try in a different public channel for testing
```

#### 3. Message Validation Errors

**Error:** `Message validation failed` or `Invalid message format`

**Causes:**
- Empty message text
- Invalid JSON syntax
- Missing required fields

**Solutions:**
```bash
# Validate JSON syntax
cat messages.json | jq .

# Check for empty strings
grep '""' messages.json

# Use dry-run to test
yos run --messages messages.json --dry-run

# Start with example (or run yos init)
yos init
```

#### 4. Network/Connection Issues

**Error:** `SlackNetworkError` or timeout

**Causes:**
- No internet connection
- Firewall blocking Slack
- Slack API downtime

**Solutions:**
```bash
# Test internet connection
curl -I https://slack.com

# Check if Slack API is reachable
curl -I https://your-workspace.slack.com/api

# Try with verbose logging
yos run --verbose

# Increase timeout (edit post_messages.py if needed)
```

#### 5. Rate Limiting

**Error:** `SlackRateLimitError` or HTTP 429

**Causes:**
- Posting too many messages too quickly
- Slack workspace rate limits hit

**Solutions:**
```bash
# Increase delays between messages
yos run --delay 5 --reply-delay 2

# Post fewer messages
yos run --limit 5

# Wait before retrying
sleep 60 && yos run
```

#### 6. SSL/TLS Certificate Errors

**Error:** `SSLError`, `SSL: CERTIFICATE_VERIFY_FAILED`, or `ssl.VERIFY_X509_STRICT`

**Causes:**
- Corporate proxy with self-signed certificates (common with Netskope, Zscaler, etc.)
- Python 3.13+ enforces strict X509 verification by default
- Missing or invalid CA certificates

**Solutions:**

**Option 1: Use standard environment variables (automatic, no config needed)**
```bash
# The tool automatically respects these standard environment variables:
export SSL_CERT_FILE=~/your-corporate-cert.pem        # CA bundle file (standard)
export REQUESTS_CA_BUNDLE=~/your-corporate-cert.pem   # Used by requests library
export CURL_CA_BUNDLE=~/your-corporate-cert.pem       # Used by curl
export SSL_CERT_DIR=/etc/ssl/certs        # CA certificate directory

# For Python 3.13+ with corporate proxies (auto-disabled by default)
# Only needed if you want to force strict mode with custom CA:
export SSL_STRICT_X509=false  # Disable strict X509 verification
# Or: export SSL_STRICT_X509=true  # Force enable (rare, only for testing)

# Now just run normally - no additional configuration needed!
yos run
```

**Option 2: Use custom CA bundle via config file**
```bash
# Create CA bundle with corporate certificates
cat /path/to/corporate-ca.crt >> ~/your-corporate-cert.pem

# Configure in config file
cat >> ~/.config/yap-on-slack/config.yaml <<EOF
ssl:
  ca_bundle: ~/your-corporate-cert.pem
  # strict_x509: null  # Auto mode (default): disables strict for custom CA
  # strict_x509: true  # Force enable strict X509 (rare, only if needed)
  # strict_x509: false # Force disable strict X509 (legacy compat)
EOF

yos run
```

**Option 3: Use CLI flags**
```bash
# Pass CA bundle (strict X509 auto-disabled for corporate certs)
yos run --ssl-ca-bundle ~/your-corporate-cert.pem

# Or force strict mode (only if you have certs with proper extensions)
yos run --ssl-ca-bundle ~/your-corporate-cert.pem --ssl-strict

# Legacy: explicitly disable strict mode
yos run --ssl-ca-bundle ~/your-corporate-cert.pem --ssl-no-strict
```

**Option 4: Disable SSL verification (insecure, testing only)**
```bash
# Via CLI flag (not recommended for production)
yos run --no-verify-ssl

# Or in config file
ssl:
  verify: false
```

# Via config file
cat >> ~/.config/yap-on-slack/config.yaml <<EOF
ssl:
  verify: false
EOF

# Via environment variable
export SSL_VERIFY=false
yos run
```

**Priority Order:**
1. CLI flags (highest) - `--ssl-strict`, `--ssl-no-strict`, `--ssl-ca-bundle`, `--no-verify-ssl`
2. Environment variables - `SSL_STRICT_X509`, `SSL_VERIFY`, `SSL_CA_BUNDLE`, `SSL_NO_STRICT`
3. Standard cert env vars - `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, `SSL_CERT_DIR`
4. Config file - `ssl.strict_x509`, `ssl.verify`, `ssl.ca_bundle`, `ssl.no_strict`
5. Auto-detection - Disables strict X509 when custom CA bundle is detected (Python 3.13+ compat)
6. System defaults (lowest)

**Example: Corporate Proxy (Netskope, Zscaler) - Automatic**
```bash
# Set once in your shell profile (.zshrc, .bashrc, etc.)
export REQUESTS_CA_BUNDLE=~/your-corporate-cert.pem
# SSL_STRICT_X509 is auto-disabled for custom CA bundles - no manual config needed!

# Now yos works automatically without any configuration!
yos run
```

**Example: Corporate Proxy - Config File**
```yaml
# ~/.config/yap-on-slack/config.yaml
workspace:
  org_url: https://your-workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

credentials:
  xoxc_token: xoxc-your-token
  xoxd_token: xoxd-your-token

ssl:
  ca_bundle: ~/your-corporate-cert.pem      # Corporate CA bundle
  no_strict: true                # Python 3.13+ compat
```

**Testing SSL configuration:**
```bash
# Test with dry-run first
yos run --dry-run

# With verbose logging to see SSL setup
yos run --limit 1 --verbose

# Verify environment variables are picked up
echo "SSL_CERT_FILE: $SSL_CERT_FILE"
echo "REQUESTS_CA_BUNDLE: $REQUESTS_CA_BUNDLE"
```

### Debugging Steps

1. **Verify Configuration File**
   ```bash
   # Check config exists and is readable
   cat ~/.config/yap-on-slack/config.yaml
   
   # Or if using project-specific config
   cat .yos.yaml
   
   # Validate YAML syntax (no trailing spaces, proper indentation)
   cat ~/.config/yap-on-slack/config.yaml | head -20
   ```

2. **Verify Required Fields**
   ```bash
   # Check workspace settings
   grep -E "org_url|channel_id|team_id" ~/.config/yap-on-slack/config.yaml
   
   # Check credentials
   grep -E "xoxc_token|xoxd_token" ~/.config/yap-on-slack/config.yaml
   
   # Ensure values are not empty
   grep "xoxc_token: " ~/.config/yap-on-slack/config.yaml | grep -v "your-token"
   ```

3. **Test with Dry Run**
   ```bash
   yos run --dry-run --verbose
   ```

4. **Check Dependencies**
   ```bash
   # Reinstall with pipx
   pipx reinstall yap-on-slack
   
   # Or from source
   mise run install
   
   # Verify Python version
   python --version  # Should be 3.13+
   ```

5. **Validate Messages**
   ```bash
   # If using separate messages file
   python -c "import yaml; print(yaml.safe_load(open('messages.json')))"
   
   # Or check messages in config
   grep -A5 "messages:" ~/.config/yap-on-slack/config.yaml
   ```

6. **Test Minimal Setup**
   ```bash
   # Create minimal test config
   yos init --local
   
   # Edit .yos.yaml with just workspace + credentials
   # Then test
   yos run --limit 1 --dry-run
   ```

### Getting Help

If issues persist:

1. **Check Logs**: Run with `--verbose` flag for detailed output
2. **Verify Config**: Ensure all required fields are in config file
3. **Verify Tokens**: Extract fresh tokens from browser
4. **Read Security Docs**: See [SECURITY.md](../SECURITY.md)
5. **Check Slack Status**: Visit https://status.slack.com
6. **Review ADRs**: See [docs/adrs/](adrs/) for design decisions and troubleshooting

**Common ADRs for troubleshooting:**
- [ADR-0001: Slack Session Tokens](adrs/0001-slack-session-tokens.md) - Why we use session tokens
- [ADR-0003: Form-Urlencoded for Slack API](adrs/0003-slack-api-form-urlencoded.md) - Why we use form-urlencoded encoding
- [ADR-0004: Unified config.yaml](adrs/0004-unified-config-yaml.md) - Configuration system design
- [ADR-0006: XDG ~/.config Standard](adrs/0006-xdg-config-over-platformdirs.md) - Config file location choice

#### Docker

```bash
# Mount config file from ~/.config
docker run --rm \
  -v ~/.config/yap-on-slack:/root/.config/yap-on-slack \
  ghcr.io/echohello-dev/yap-on-slack:latest yos run

# Or mount local .yos.yaml
docker run --rm \
  -v $(pwd)/.yos.yaml:/app/.yos.yaml \
  ghcr.io/echohello-dev/yap-on-slack:latest yos run

# Or pass variables directly
docker run --rm \
  -e SLACK_XOXC_TOKEN="xoxc-..." \
  -e SLACK_XOXD_TOKEN="xoxd-..." \
  -e SLACK_ORG_URL="https://workspace.slack.com" \
  -e SLACK_CHANNEL_ID="C123" \
  -e SLACK_TEAM_ID="T123" \
  ghcr.io/echohello-dev/yap-on-slack:latest yos run
```

## Performance Tips

### Optimizing Speed

```bash
# Minimum delays (use with caution - may hit rate limits)
yos run --delay 1 --reply-delay 0.5 --reaction-delay 0.2

# Disable reactions (remove emojis from message text)
# Or skip reaction logic by not including emojis
```

### Batch Processing

```bash
# Process messages in batches
yos run --limit 10  # First 10
# Wait a bit
yos run --limit 10  # Modify messages.json for next batch
```

---

**Need more help?** Check the [README](../README.md) or review the [ADRs](adrs/README.md) for design decisions:
- [ADR-0001: Slack Session Tokens](adrs/0001-slack-session-tokens.md) - Why we use session tokens
- [ADR-0002: Multi-User YAML Configuration](adrs/0002-multi-user-yaml-configuration.md) - How multi-user support works
- [ADR-0003: Form-Urlencoded for Slack API](adrs/0003-slack-api-form-urlencoded.md) - Why we use form-urlencoded encoding
