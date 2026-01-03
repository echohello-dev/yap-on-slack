# Plan: Restructure Configuration to Unified config.yaml

Consolidate `users.yaml`, `messages.json`, `.env`, and AI settings into a single `config.yaml` file. Default to `~/.config/yap-on-slack/config.yaml` (XDG-compliant), with CWD `config.yaml` taking precedence when present.

## Config Template Structure

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/echohello-dev/yap-on-slack/main/schema/config.schema.json
# ~/.config/yap-on-slack/config.yaml

# Workspace settings (required)
workspace:
  org_url: https://your-workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

# Default credentials (used when no per-user tokens defined)
credentials:
  xoxc_token: xoxc-your-token-here
  xoxd_token: xoxd-your-token-here
  cookies: ""  # optional extra cookies

# User selection strategy
user_strategy: round_robin  # round_robin | random

# Additional users (optional, merged with default credentials user)
users:
  - name: alice
    xoxc_token: xoxc-alice-token
    xoxd_token: xoxd-alice-token
  - name: bob
    xoxc_token: xoxc-bob-token
    xoxd_token: xoxd-bob-token

# Messages to post (optional, can also use --use-ai to generate)
messages:
  - text: "Good morning team! :wave:"
    replies:
      - "Hey! Ready for standup?"
      - text: "Morning everyone"
        user: alice
    reactions:
      - wave
      - coffee

# AI message generation settings
ai:
  enabled: false
  model: google/gemini-2.5-flash-preview
  api_key: ""  # or use OPENROUTER_API_KEY env var
  temperature: 0.7
  max_tokens: 4000
  system_prompt: |
    Generate realistic Slack messages for testing...
    (full prompt extracted from code)
```

## Steps

1. **Add `platformdirs` dependency** in pyproject.toml for cross-platform config directory resolution.

2. **Create JSON Schema** at `schema/config.schema.json`:
   - Define all config sections with types, descriptions, and examples
   - Host on GitHub raw URL for editor autocomplete (VS Code, IntelliJ, etc.)
   - Register with [SchemaStore](https://www.schemastore.org/) for wider editor support (future)

3. **Create config template file** `config.yaml.example` with placeholder values and inline documentation comments, including schema reference comment.

4. **Create new configuration models** in post_messages.py:
   - `WorkspaceConfig` — org_url, channel_id, team_id
   - `CredentialsConfig` — xoxc_token, xoxd_token, cookies (all optional)
   - `UserConfig` — name, xoxc_token, xoxd_token, cookies
   - `MessageConfig` — text, replies, reactions, user
   - `AIConfig` — enabled, model, api_key, temperature, max_tokens, system_prompt
   - `Config` — top-level model combining all sections

5. **Implement config discovery** in post_messages.py:
   - Search order: `--config` flag → `./config.yaml` → `~/.config/yap-on-slack/config.yaml`
   - Optionally load `.env` from same directory as config file (if present)
   - Env vars override config file values (SLACK_XOXC_TOKEN, SLACK_XOXD_TOKEN, etc.)

6. **Refactor `init` command** in cli.py:
   - Default: write to `~/.config/yap-on-slack/config.yaml`
   - Add `--local` flag to write to `./config.yaml` instead
   - Create parent directories if needed

7. **Extract hardcoded AI config** from post_messages.py:
   - Move model name, temperature, max_tokens into config defaults
   - Extract system prompt (~3KB) into config with sensible default

8. **Update `run` command** in cli.py:
   - Load unified config using new discovery logic
   - Validate credentials exist (from config or env)
   - Add `--config` flag to specify config file path

9. **Remove deprecated files** from init command:
   - Stop generating `users.yaml`, `messages.json`, `.env`
   - Update AGENTS.md and README.md references

10. **Cleanup**: Delete `users.yaml.example`, `messages.json.example` after migration complete.

## Credential Precedence (highest to lowest)

1. CLI flags (if any added in future)
2. Environment variables (SLACK_XOXC_TOKEN, SLACK_XOXD_TOKEN)
3. Config file `credentials:` section (default user)
4. Config file `users:` array (per-user credentials)
