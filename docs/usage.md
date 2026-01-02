# Usage Guide & Troubleshooting

## Table of Contents

- [Authentication Setup](#authentication-setup)
- [Getting Slack Credentials](#getting-slack-credentials)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Common Issues](#common-issues)

## Authentication Setup

Open up your Slack in your browser and login.

> **Note**: You only need one of the following: an `xoxp-*` User OAuth token, an `xoxb-*` Bot token, or both `xoxc-*` and `xoxd-*` session tokens. User/Bot tokens are more secure and do not require a browser session. If multiple are provided, priority is `xoxp` > `xoxb` > `xoxc/xoxd`.

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

**Method 1: Via Workspace Settings**

1. Click your workspace name at the top-left
2. Select "Settings & administration" → "Workspace settings"
3. Look at the URL: `https://workspace.slack.com/admin/settings#team_id=T01234ABC56`
4. The Team ID is in the URL (e.g., `T01234ABC56`)

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

### Environment Variables

Create a `.env` file in the project root:

```bash
# Copy from example
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required Variables:**

```env
SLACK_XOXC_TOKEN=xoxc-1234567890-1234567890-1234567890-abcdef
SLACK_XOXD_TOKEN=xoxd-abcdef123456
SLACK_ORG_URL=https://your-workspace.slack.com
SLACK_CHANNEL_ID=C01234ABC56
SLACK_TEAM_ID=T01234ABC56
```

**Optional Variables:**

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Custom Messages

Create a `messages.json` file (or use any name with `--messages` flag):

```json
[
  {
    "text": "Main message with *bold* and _italic_",
    "replies": [
      "First reply",
      "Second reply"
    ]
  },
  {
    "text": "Message without replies"
  }
]
```

**Supported Formatting:**

- `*bold*` or `**bold**` → Bold text
- `_italic_` → Italic text
- `~strikethrough~` → Strikethrough
- `` `code` `` → Inline code
- `<url|label>` → Link with label
- `:emoji_name:` → Emoji (e.g., `:rocket:`)
- `•` or `- ` → Bullet points

## Usage Examples

### Basic Usage

```bash
# Use default messages.json
mise run run

# Or with uv directly
uv run python -m yap_on_slack.post_messages
```

### Custom Messages File

```bash
# Use custom messages file
mise run run -- --messages my-messages.json

# Or absolute path
mise run run -- --messages /path/to/messages.json
```

### Dry Run (Validate Without Posting)

```bash
# Test configuration and message validation
mise run run -- --dry-run

# With custom messages
mise run run -- --dry-run --messages test-messages.json
```

### Limit Number of Messages

```bash
# Post only first 3 messages
mise run run -- --limit 3

# Useful for testing
mise run run -- --limit 1 --dry-run
```

### Custom Delays

```bash
# Slower posting (5s between messages)
mise run run -- --delay 5

# Faster replies (0.5s between)
mise run run -- --reply-delay 0.5

# Instant reactions
mise run run -- --reaction-delay 0.1

# Combine all
mise run run -- --delay 3 --reply-delay 1.5 --reaction-delay 0.8
```

### Verbose Logging

```bash
# Enable debug logging
mise run run -- --verbose

# See detailed HTTP requests and responses
mise run run -- --verbose --dry-run
```

### Combined Examples

```bash
# Test run with custom messages, limited count
mise run run -- --messages test.json --limit 2 --dry-run

# Production run with slower delays
mise run run -- --delay 5 --reply-delay 2 --reaction-delay 1

# Quick test of first message only
mise run run -- --limit 1 --verbose
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

**Error:** `invalid_auth` or HTTP 401

**Causes:**
- Tokens expired (session tokens expire after hours/days)
- Wrong tokens copied
- Tokens from different workspace

**Solutions:**
```bash
# Extract fresh tokens from browser
# See "Extracting Session Tokens" section above

# Verify tokens in .env are correct
cat .env | grep SLACK_XOXC_TOKEN
cat .env | grep SLACK_XOXD_TOKEN

# Test with dry-run first
mise run run -- --dry-run
```

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
mise run run -- --messages messages.json --dry-run

# Start with example
cp messages.json.example messages.json
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
mise run run -- --verbose

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
mise run run -- --delay 5 --reply-delay 2

# Post fewer messages
mise run run -- --limit 5

# Wait before retrying
sleep 60 && mise run run
```

### Debugging Steps

1. **Verify Environment**
   ```bash
   # Check .env exists and has required vars
   cat .env
   
   # Ensure no extra spaces or quotes
   grep -v '^#' .env | grep '='
   ```

2. **Test with Dry Run**
   ```bash
   mise run run -- --dry-run --verbose
   ```

3. **Check Dependencies**
   ```bash
   # Reinstall dependencies
   mise run install
   
   # Verify Python version
   python --version  # Should be 3.13+
   ```

4. **Validate Messages File**
   ```bash
   # Pretty-print JSON
   cat messages.json | jq .
   
   # Validate with Python
   python -m json.tool messages.json
   ```

5. **Test Minimal Setup**
   ```bash
   # Use only 1 message
   echo '[{"text": "Test message"}]' > test.json
   mise run run -- --messages test.json --limit 1 --dry-run
   ```

### Getting Help

If issues persist:

1. **Check Logs**: Run with `--verbose` flag for detailed output
2. **Verify Tokens**: Extract fresh tokens from browser
3. **Read Security Docs**: See [SECURITY.md](../SECURITY.md)
4. **Check Slack Status**: Visit https://status.slack.com
5. **Review ADRs**: See [docs/adrs/](adrs/) for design decisions

### Environment-Specific Issues

#### macOS

```bash
# May need to trust Python certificate
/Applications/Python\ 3.13/Install\ Certificates.command
```

#### Linux

```bash
# Ensure ca-certificates installed
sudo apt-get install ca-certificates

# Or on RHEL/Fedora
sudo dnf install ca-certificates
```

#### Docker

```bash
# Ensure .env is properly mounted
docker run --rm --env-file .env yap-on-slack

# Or pass variables directly
docker run --rm \
  -e SLACK_XOXC_TOKEN="xoxc-..." \
  -e SLACK_XOXD_TOKEN="xoxd-..." \
  -e SLACK_ORG_URL="https://workspace.slack.com" \
  -e SLACK_CHANNEL_ID="C123" \
  -e SLACK_TEAM_ID="T123" \
  yap-on-slack
```

## Performance Tips

### Optimizing Speed

```bash
# Minimum delays (use with caution - may hit rate limits)
mise run run -- --delay 1 --reply-delay 0.5 --reaction-delay 0.2

# Disable reactions (remove emojis from message text)
# Or skip reaction logic by not including emojis
```

### Batch Processing

```bash
# Process messages in batches
mise run run -- --limit 10  # First 10
# Wait a bit
mise run run -- --limit 10  # Modify messages.json for next batch
```

---

**Need more help?** Check the [README](../README.md) or review [ADR-0001](adrs/0001-slack-session-tokens.md) for context on token usage.
