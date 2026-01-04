#!/usr/bin/env python3
"""Post realistic support messages to Slack using session tokens."""

import argparse
import json
import logging
import os
import random
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote, urlparse

import httpx
import yaml
from dotenv import dotenv_values
from platformdirs import user_config_dir
from pydantic import BaseModel, ValidationError, field_validator
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from tenacity import (RetryError, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

console = Console()

# Configure logging with environment variable support
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Default AI system prompt
DEFAULT_AI_SYSTEM_PROMPT = """Generate 20 realistic Slack channel messages for an engineering team support channel.

## CRITICAL: Tone and Length Variety
Messages MUST vary dramatically in tone and length:

**Tone spectrum** (use all of these across messages):
- Super casual: "yo anyone know why ci is failing lol", "thx!", "lgtm ship it"
- Casual: "hey quick q - where's the config for...", "np, happy to help"
- Normal: "I'm seeing an issue with the auth flow. Has anyone encountered this?"
- Professional: "Team, please be advised that we'll be performing scheduled maintenance..."
- Formal announcements: "*[ACTION REQUIRED]* All teams must migrate to v2 API by EOQ"

**Length spectrum** (use all of these):
- One-word/emoji only: ":+1:", "thx", "lgtm", ":eyes:", "noted"
- Quick one-liners: "anyone else seeing 503s?", "nvm figured it out"
- Medium (2-3 sentences): Standard questions and updates
- Detailed (paragraph with bullets/code): Complex issues, announcements, guides

## Message Types to Include
1. **Quick acknowledgments** (just reactions or 1-2 words)
2. **General support questions**: "how do I...", "where can I find...", "what's the best way to..."
3. **GitHub-specific discussions**: PR reviews, commit questions, code changes, merge conflicts
4. **CI/CD and workflow issues**: Failed actions, build errors, deployment problems
5. **Incident response**: Outages, errors, postmortems
6. **Announcements**: Deprecations, releases, maintenance windows
7. **Casual team chat**: Quick kudos, jokes, offtopic-ish comments

## GitHub Actions / Workflow Errors (include several of these)
Reference actual workflow failures with realistic error messages:
- ":x: *Workflow failed*: `build.yml` on `main` - `npm ERR! peer dep issue`"
- "anyone know why the *deploy-prod* action keeps timing out? been stuck for 3 runs now"
- ":rotating_light: CI broken on <PR link> - `Error: Process completed with exit code 1`"
- "the `lint` step is failing with `eslint: command not found` - did someone update the runner?"

## Slack Formatting (use extensively and varied)
- *bold* for emphasis
- _italic_ for secondary emphasis or quotes
- ~strikethrough~ for corrections/outdated info
- `inline code` for commands, file names, variables
- Code blocks with triple backticks for multi-line code/logs
- • bullet points for lists
- 1. 2. 3. numbered lists for steps
- > blockquotes for quoting others or logs
- <https://url.com|link text> for links
- :emoji_name: for slackmoji (use varied ones: :rocket:, :fire:, :eyes:, :pray:, :100:, :tada:, :thinking_face:, :face_palm:, :sob:, :muscle:, :white_check_mark:, :x:, :warning:, :rotating_light:, :bug:, :hammer_and_wrench:, :ship:, :memo:, :bulb:, :wave:, :coffee:, :thumbsup:, :thumbsdown:, :heart:)

## Reply Patterns
- Some messages should have NO replies
- Some should have just ":+1:" or "thx" type replies
- Some should have back-and-forth debugging conversations
- Some should have multiple people chiming in with suggestions
- Include natural typos and casual language in replies

## Examples of Good Variety

CASUAL: "yo :wave: anyone know if the staging db is up? getting connection refused"
REPLY: "yeah was down for backups, should be back now"
REPLY: "confirmed, just tested :+1:"

PROFESSIONAL: "*[Scheduled Maintenance Notice]*\\nThe production database cluster will undergo maintenance:\\n• *When*: Saturday 2am-4am PST\\n• *Impact*: Read-only mode for 30 minutes\\n• *Action*: No action required, but avoid large writes during this window\\n\\ncc @oncall"

QUICK: ":eyes:"
REPLY: "lol"

DETAILED ISSUE:
":bug: *Bug Report*: User sessions expiring prematurely\\n\\n*Steps to reproduce*:\\n1. Login to dashboard\\n2. Wait 5 minutes (no activity)\\n3. Session expires (should be 30min)\\n\\n*Expected*: 30min timeout\\n*Actual*: ~5min timeout\\n\\n`JWT_EXPIRY` looks correct in config. Anyone seen this before?"

WORKFLOW ERROR:
":x: `deploy-production` failed on <https://github.com/org/repo/actions/runs/12345|run #456>\\n```\\nError: Container action is not supported on macOS\\n```\\nwhoops, wrong runner matrix :face_palm:"

ONE-LINER: "nvm found it in the docs"

ANNOUNCEMENT: "hey all :mega: quick reminder that `/api/v1/*` endpoints are *deprecated* and will be removed next sprint. please migrate to v2 - docs here: <https://docs.example.com/v2|API v2 Guide>"
"""


class SlackAPIError(Exception):
    """Base exception for Slack API errors."""

    pass


class SlackRateLimitError(SlackAPIError):
    """Raised when Slack API rate limit is hit."""

    pass


class SlackNetworkError(SlackAPIError):
    """Raised when network connection fails."""

    pass


class InvalidMessageFormatError(Exception):
    """Raised when message format is invalid."""

    pass


def _print_auth_debug(
    *,
    endpoint: str,
    config: dict[str, str],
    cookies: dict[str, str] | None = None,
    response: httpx.Response | None = None,
    slack_result: dict[str, Any] | None = None,
    note: str | None = None,
) -> None:
    """Print safe diagnostics for Slack auth debugging.

    Intentionally does not print any token/cookie values.
    """

    org_url = config.get("SLACK_ORG_URL", "")
    parsed = urlparse(org_url)
    host = parsed.netloc or org_url

    raw_d = config.get("SLACK_XOXD_TOKEN", "")
    decoded_d = unquote(raw_d)

    diagnostics: dict[str, Any] = {
        "endpoint": endpoint,
        "org_host": host,
        "org_scheme": parsed.scheme or "(unknown)",
        "team_id": config.get("SLACK_TEAM_ID", ""),
        "channel_id": config.get("SLACK_CHANNEL_ID", ""),
        "cookie_d_len": len(decoded_d),
        "cookie_d_starts_with_xoxd": decoded_d.startswith("xoxd-"),
        "cookie_d_was_urlencoded": decoded_d != raw_d,
        "cookie_d_contains_percent": "%" in raw_d,
    }

    if cookies is not None:
        diagnostics["cookie_keys"] = sorted(cookies.keys())

    if note:
        diagnostics["note"] = note

    if response is not None:
        diagnostics["http_status"] = response.status_code
        # Helpful headers (safe to print)
        for header_key in ("x-slack-req-id", "x-slack-backend", "retry-after"):
            if header_key in response.headers:
                diagnostics[header_key] = response.headers.get(header_key)

    if slack_result is not None:
        diagnostics["slack_ok"] = slack_result.get("ok")
        diagnostics["slack_error"] = slack_result.get("error")
        if "needed" in slack_result:
            diagnostics["slack_needed"] = slack_result.get("needed")
        if "provided" in slack_result:
            diagnostics["slack_provided"] = slack_result.get("provided")

    console.print(
        Panel.fit(
            json.dumps(diagnostics, indent=2, sort_keys=True),
            title="[bold]Auth Debug[/bold]",
            border_style="magenta",
        )
    )


# Unified Config Models


class WorkspaceConfigModel(BaseModel):
    """Workspace settings from config file."""

    org_url: str
    channel_id: str
    team_id: str

    @field_validator("org_url")
    @classmethod
    def org_url_is_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("org_url must start with https://")
        return v


class CredentialsConfigModel(BaseModel):
    """Default credentials from config file."""

    xoxc_token: str | None = None
    xoxd_token: str | None = None
    cookies: str | None = None


class UserConfigModel(BaseModel):
    """User configuration with credentials."""

    name: str
    xoxc_token: str
    xoxd_token: str
    cookies: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("User name cannot be empty")
        return v


class MessageReplyConfigModel(BaseModel):
    """Reply configuration from config file."""

    text: str
    user: str | None = None


class MessageConfigModel(BaseModel):
    """Message configuration from config file."""

    text: str
    user: str | None = None
    replies: list[MessageReplyConfigModel | str] = []
    reactions: list[str] = []


class AIConfigModel(BaseModel):
    """AI generation settings from config file."""

    enabled: bool = False
    model: str = "openrouter/auto"  # Auto-selects best available model
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4000
    system_prompt: str | None = None


class UnifiedConfig(BaseModel):
    """Unified configuration from config.yaml."""

    workspace: WorkspaceConfigModel
    credentials: CredentialsConfigModel | None = None
    user_strategy: Literal["round_robin", "random"] = "round_robin"
    users: list[UserConfigModel] = []
    messages: list[MessageConfigModel] = []
    ai: AIConfigModel | None = None


# Legacy Models (for backward compatibility with messages.json)


class MessageReply(BaseModel):
    """Schema for message reply."""

    text: str
    user: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate text is not empty."""
        if not v or not v.strip():
            raise ValueError("Reply text cannot be empty")
        return v


class Message(BaseModel):
    """Schema for Slack message."""

    text: str
    user: str | None = None
    replies: list[MessageReply] = []

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate text is not empty."""
        if not v or not v.strip():
            raise ValueError("Message text cannot be empty")
        return v

    @field_validator("replies", mode="before")
    @classmethod
    def validate_replies(cls, v: Any) -> list[MessageReply]:
        """Validate replies are not empty and normalize their shape.

        Accepts either:
        - replies: ["text", ...]
        - replies: [{"text": "...", "user": "alice"}, ...]
        """
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("Replies must be a list")

        replies: list[MessageReply] = []
        for reply in v:
            if isinstance(reply, str):
                replies.append(MessageReply(text=reply))
            elif isinstance(reply, dict):
                replies.append(MessageReply(**reply))
            else:
                raise ValueError("Reply must be a string or object")
        return replies


class SlackUser(BaseModel):
    """A Slack user session (xoxc/xoxd) used to post messages."""

    name: str
    SLACK_XOXC_TOKEN: str
    SLACK_XOXD_TOKEN: str
    SLACK_COOKIES: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("User name cannot be empty")
        return v


class SlackWorkspace(BaseModel):
    """Shared workspace config (org/channel/team)."""

    SLACK_ORG_URL: str
    SLACK_CHANNEL_ID: str
    SLACK_TEAM_ID: str

    @field_validator("SLACK_ORG_URL")
    @classmethod
    def org_url_is_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("SLACK_ORG_URL must start with https://")
        return v


class UsersConfig(BaseModel):
    """Multi-user config file schema."""

    users: list[SlackUser]
    default_user: str | None = None
    strategy: Literal["round_robin", "random"] = "round_robin"


class AppConfig(BaseModel):
    """Application config including workspace and multiple users."""

    model_config = {"defer_build": True}

    workspace: SlackWorkspace
    users: list[SlackUser]
    default_user: str | None = None
    strategy: Literal["round_robin", "random"] = "round_robin"

    def _user_index_by_name(self, name: str) -> int | None:
        for idx, user in enumerate(self.users):
            if user.name == name:
                return idx
        return None

    def select_user(self, *, name: str | None, message_index: int) -> SlackUser:
        """Select a user for a message.

        If name is provided, use that specific user.
        Otherwise, use the configured strategy (round_robin or random).
        """
        if not self.users:
            raise ValueError("No users configured")

        if name:
            idx = self._user_index_by_name(name)
            if idx is None:
                raise ValueError(
                    f"Unknown user '{name}'. Available: {', '.join(u.name for u in self.users)}"
                )
            return self.users[idx]

        # No specific user requested - use strategy
        if self.strategy == "random":
            return random.choice(self.users)

        # round_robin (default)
        return self.users[message_index % len(self.users)]


def _merge_request_config(app_config: AppConfig, user: SlackUser) -> dict[str, str]:
    """Build the request config dict expected by Slack API helpers."""

    merged = {
        "SLACK_ORG_URL": app_config.workspace.SLACK_ORG_URL,
        "SLACK_CHANNEL_ID": app_config.workspace.SLACK_CHANNEL_ID,
        "SLACK_TEAM_ID": app_config.workspace.SLACK_TEAM_ID,
        "SLACK_XOXC_TOKEN": user.SLACK_XOXC_TOKEN,
        "SLACK_XOXD_TOKEN": user.SLACK_XOXD_TOKEN,
    }
    if user.SLACK_COOKIES:
        merged["SLACK_COOKIES"] = user.SLACK_COOKIES
    return merged


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def _build_slack_cookies(config: dict[str, str]) -> dict[str, str]:
    # Start with any additional cookies provided (e.g., x, d-s, b, etc.)
    cookies: dict[str, str] = {}
    extra = config.get("SLACK_COOKIES")
    if extra:
        cookies.update(_parse_cookie_header(extra))

    # Always set/override the auth cookie `d` from SLACK_XOXD_TOKEN.
    # Use the token directly - do not URL-decode as Slack expects the original value
    cookies["d"] = config["SLACK_XOXD_TOKEN"]
    return cookies


def discover_config_file(explicit_path: Path | None = None) -> Path | None:
    """Discover config file location.

    Search order:
    1. Explicit --config path
    2. ./config.yaml (CWD)
    3. ~/.config/yap-on-slack/config.yaml (XDG home)

    Args:
        explicit_path: Optional explicit config path from CLI

    Returns:
        Path to config file if found, None otherwise
    """
    if explicit_path:
        if explicit_path.exists():
            logger.debug(f"Using explicit config: {explicit_path}")
            return explicit_path
        else:
            raise ValueError(f"Config file not found: {explicit_path}")

    # Check CWD
    cwd_config = Path.cwd() / "config.yaml"
    if cwd_config.exists():
        logger.debug(f"Found config in CWD: {cwd_config}")
        return cwd_config

    # Check XDG config dir
    home_config_dir = Path(user_config_dir("yap-on-slack", ensure_exists=False))
    home_config = home_config_dir / "config.yaml"
    if home_config.exists():
        logger.debug(f"Found config in home: {home_config}")
        return home_config

    logger.debug("No config.yaml found")
    return None


def load_unified_config(config_path: Path | None = None) -> tuple[AppConfig, dict[str, str]]:
    """Load unified configuration from config.yaml and .env files.

    Args:
        config_path: Optional explicit config path

    Returns:
        (app_config, env) tuple with merged configuration
    """
    console.print("[bold blue]━━━ Loading Configuration ━━━[/bold blue]")

    # Discover config file
    discovered_config = discover_config_file(config_path)

    # Load environment variables from .env in config directory (if present)
    env: dict[str, str] = {}
    if discovered_config:
        config_dir = discovered_config.parent
        env_file = config_dir / ".env"
        if env_file.exists():
            logger.debug(f"Loading .env from {env_file}")
            raw_env = dotenv_values(env_file)
            for key, value in raw_env.items():
                if value is not None:
                    env[key] = value
            console.print(f"[green]✓ Loaded .env from {env_file}[/green]")
    else:
        # Fallback: try .env in CWD
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            logger.debug(f"Loading .env from {cwd_env}")
            raw_env = dotenv_values(cwd_env)
            for key, value in raw_env.items():
                if value is not None:
                    env[key] = value
            console.print(f"[green]✓ Loaded .env from {cwd_env}[/green]")

    # Merge with OS environment variables (env vars take precedence)
    for key in [
        "SLACK_XOXC_TOKEN",
        "SLACK_XOXD_TOKEN",
        "SLACK_COOKIES",
        "SLACK_ORG_URL",
        "SLACK_CHANNEL_ID",
        "SLACK_TEAM_ID",
        "SLACK_USER_NAME",
        "OPENROUTER_API_KEY",
        "GITHUB_TOKEN",
    ]:
        os_value = os.getenv(key)
        if os_value:
            env[key] = os_value

    # Load config.yaml if found
    unified_config: UnifiedConfig | None = None
    if discovered_config:
        try:
            with discovered_config.open() as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                raise ValueError("Config file must be a YAML mapping/object")

            unified_config = UnifiedConfig(**config_data)
            console.print(f"[green]✓ Loaded config from {discovered_config}[/green]")
        except (yaml.YAMLError, ValidationError, TypeError, ValueError) as e:
            logger.error(f"Failed to load config.yaml: {e}")
            raise ValueError(f"Invalid config.yaml: {e}") from e

    # Build workspace config (env vars override config file)
    workspace_data = {}
    if unified_config:
        workspace_data["SLACK_ORG_URL"] = unified_config.workspace.org_url
        workspace_data["SLACK_CHANNEL_ID"] = unified_config.workspace.channel_id
        workspace_data["SLACK_TEAM_ID"] = unified_config.workspace.team_id

    # Env vars take precedence
    workspace_data["SLACK_ORG_URL"] = env.get(
        "SLACK_ORG_URL", workspace_data.get("SLACK_ORG_URL", "")
    )
    workspace_data["SLACK_CHANNEL_ID"] = env.get(
        "SLACK_CHANNEL_ID", workspace_data.get("SLACK_CHANNEL_ID", "")
    )
    workspace_data["SLACK_TEAM_ID"] = env.get(
        "SLACK_TEAM_ID", workspace_data.get("SLACK_TEAM_ID", "")
    )

    # Validate workspace config
    missing_workspace = [
        key
        for key in ["SLACK_ORG_URL", "SLACK_CHANNEL_ID", "SLACK_TEAM_ID"]
        if not workspace_data.get(key)
    ]
    if missing_workspace:
        console.print("[bold red]✗ Missing required workspace configuration:[/bold red]")
        for var in missing_workspace:
            console.print(f"  [red]- {var}[/red]")
        raise ValueError(f"Missing required workspace config: {', '.join(missing_workspace)}")

    workspace = SlackWorkspace(
        SLACK_ORG_URL=str(workspace_data["SLACK_ORG_URL"]),
        SLACK_CHANNEL_ID=str(workspace_data["SLACK_CHANNEL_ID"]),
        SLACK_TEAM_ID=str(workspace_data["SLACK_TEAM_ID"]),
    )

    # Build users list
    users: list[SlackUser] = []
    default_user: str | None = None
    strategy: Literal["round_robin", "random"] = "round_robin"

    # Get default credentials (env vars take precedence over config file)
    default_xoxc = env.get("SLACK_XOXC_TOKEN")
    default_xoxd = env.get("SLACK_XOXD_TOKEN")
    default_cookies = env.get("SLACK_COOKIES")
    default_user_name = env.get("SLACK_USER_NAME", "default")

    # If not in env, check config file credentials
    if unified_config and unified_config.credentials:
        if not default_xoxc:
            default_xoxc = unified_config.credentials.xoxc_token
        if not default_xoxd:
            default_xoxd = unified_config.credentials.xoxd_token
        if not default_cookies and unified_config.credentials.cookies:
            default_cookies = unified_config.credentials.cookies

    # Validate we have default credentials
    if not default_xoxc or not default_xoxd:
        console.print("[bold red]✗ Missing required credentials:[/bold red]")
        if not default_xoxc:
            console.print("  [red]- SLACK_XOXC_TOKEN or credentials.xoxc_token[/red]")
        if not default_xoxd:
            console.print("  [red]- SLACK_XOXD_TOKEN or credentials.xoxd_token[/red]")
        raise ValueError("Missing required credentials (xoxc_token and xoxd_token)")

    # Add default user
    users.append(
        SlackUser(
            name=default_user_name,
            SLACK_XOXC_TOKEN=default_xoxc,
            SLACK_XOXD_TOKEN=default_xoxd,
            SLACK_COOKIES=default_cookies,
        )
    )
    default_user = default_user_name

    # Add additional users from config file
    if unified_config and unified_config.users:
        for user_config in unified_config.users:
            if user_config.name == default_user_name:
                raise ValueError(
                    f"User '{default_user_name}' is defined in both credentials and users array; rename one"
                )
            users.append(
                SlackUser(
                    name=user_config.name,
                    SLACK_XOXC_TOKEN=user_config.xoxc_token,
                    SLACK_XOXD_TOKEN=user_config.xoxd_token,
                    SLACK_COOKIES=user_config.cookies,
                )
            )
        strategy = unified_config.user_strategy

    app_config = AppConfig(
        workspace=workspace,
        users=users,
        default_user=default_user,
        strategy=strategy,
    )

    logger.info(f"Configuration loaded: {len(users)} user{'s' if len(users) != 1 else ''}")
    console.print(
        f"[bold green]✓ Configuration ready ({len(users)} user{'s' if len(users) != 1 else ''})[/bold green]\n"
    )

    return app_config, env


def _assign_users_to_ai_messages(app_config: AppConfig, messages: list[dict[str, Any]]) -> None:
    """Mutate AI-generated messages to include explicit user fields.

    This ensures AI-generated runs actually post as multiple users when configured.
    Also randomizes reply count (0-8) when using AI-generated messages.
    """

    has_multiple_users = len(app_config.users) > 1

    # Track global reply index for round-robin across all messages
    global_reply_idx = 0

    for msg_idx, msg in enumerate(messages):
        # Assign user if multiple users configured
        if has_multiple_users and msg.get("user") is None:
            if app_config.strategy == "random":
                msg["user"] = random.choice(app_config.users).name
            else:
                msg["user"] = app_config.users[msg_idx % len(app_config.users)].name

        replies = msg.get("replies", [])
        if not isinstance(replies, list):
            continue

        # Randomize reply count: pick 0-8 replies from available replies
        # If fewer replies available, use all of them; if more, randomly sample
        max_replies = random.randint(0, 8)
        if len(replies) > max_replies:
            replies = random.sample(replies, max_replies)
        # If replies < max_replies, we just use all available replies

        normalized_replies: list[dict[str, Any]] = []
        for reply in replies:
            if isinstance(reply, str):
                reply_obj: dict[str, Any] = {"text": reply}
            elif isinstance(reply, dict):
                reply_obj = dict(reply)
            else:
                continue

            # Assign user to reply if multiple users configured
            if has_multiple_users and reply_obj.get("user") is None:
                if app_config.strategy == "random":
                    reply_obj["user"] = random.choice(app_config.users).name
                else:
                    # Use global reply index to ensure round-robin cycles through all users
                    reply_obj["user"] = app_config.users[
                        global_reply_idx % len(app_config.users)
                    ].name
                    global_reply_idx += 1

            normalized_replies.append(reply_obj)

        msg["replies"] = normalized_replies


def load_config(users_path: Path | None = None) -> tuple[AppConfig, dict[str, str]]:
    """Load configuration from .env plus optional multi-user config.

    Returns:
        (app_config, raw_env)
    """
    logger.debug("Loading environment configuration from .env file")
    with console.status("[bold blue]Loading environment configuration...", spinner="dots"):
        try:
            raw_config = dotenv_values(".env")
        except Exception as e:
            logger.error(f"Failed to read .env file: {e}")
            raise ValueError(f"Cannot read .env file: {e}") from e
        time.sleep(0.2)

    # Convert to non-optional dict
    env: dict[str, str] = {}
    for key, value in raw_config.items():
        if value is not None:
            env[key] = value

    # Workspace vars are always required
    required_workspace_vars = ["SLACK_ORG_URL", "SLACK_CHANNEL_ID", "SLACK_TEAM_ID"]
    missing_workspace = [var for var in required_workspace_vars if not env.get(var)]

    if missing_workspace:
        console.print("[bold red]✗ Missing required environment variables:[/bold red]")
        for var in missing_workspace:
            console.print(f"  [red]- {var}[/red]")
            logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_workspace)}")

    # Validate URL format via model
    workspace = SlackWorkspace(
        SLACK_ORG_URL=env["SLACK_ORG_URL"],
        SLACK_CHANNEL_ID=env["SLACK_CHANNEL_ID"],
        SLACK_TEAM_ID=env["SLACK_TEAM_ID"],
    )

    users_config_yaml = env.get("SLACK_USERS_YAML")
    # Back-compat (deprecated): JSON string payload
    users_config_json = env.get("SLACK_USERS_JSON")
    users_file_env = env.get("SLACK_USERS_FILE")

    # Always require a default user from .env, and always use it as the fallback
    required_token_vars = ["SLACK_XOXC_TOKEN", "SLACK_XOXD_TOKEN"]
    missing_tokens = [var for var in required_token_vars if not env.get(var)]
    if missing_tokens:
        console.print("[bold red]✗ Missing required environment variables:[/bold red]")
        for var in missing_tokens:
            console.print(f"  [red]- {var}[/red]")
            logger.error(f"Missing required environment variable: {var}")
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing_workspace + missing_tokens)
        )

    env_user_name = env.get("SLACK_USER_NAME", "default")
    users: list[SlackUser] = [
        SlackUser(
            name=env_user_name,
            SLACK_XOXC_TOKEN=env["SLACK_XOXC_TOKEN"],
            SLACK_XOXD_TOKEN=env["SLACK_XOXD_TOKEN"],
            SLACK_COOKIES=env.get("SLACK_COOKIES"),
        )
    ]
    default_user: str | None = env_user_name
    strategy: Literal["round_robin", "random"] = "round_robin"

    users_file = users_path or (Path(users_file_env) if users_file_env else None)
    if users_file is None:
        # Convenience: if a local users.yaml/users.yml exists, load it automatically.
        for candidate in (Path("users.yaml"), Path("users.yml")):
            if candidate.exists():
                users_file = candidate
                break
    if users_file is not None and not users_file.exists():
        # If the config file doesn't exist, fall back to the .env user.
        logger.info("Users config file not found (%s); using .env user only", users_file)
        users_file = None

    def _load_users_payload_from_file(path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        raw = path.read_text()

        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw)
        elif suffix == ".json":
            payload = json.loads(raw)
        else:
            # Default to YAML, but fall back to JSON
            try:
                payload = yaml.safe_load(raw)
            except Exception:
                payload = json.loads(raw)

        if not isinstance(payload, dict):
            raise ValueError("Users config must be a mapping/object at the top level")
        return payload

    if users_config_yaml or users_config_json or users_file:
        try:
            if users_config_yaml:
                loaded = yaml.safe_load(users_config_yaml)
                if not isinstance(loaded, dict):
                    raise ValueError("SLACK_USERS_YAML must be a YAML mapping/object")
                users_payload = loaded
            elif users_config_json:
                users_payload = json.loads(users_config_json)
            else:
                if users_file is None:
                    raise ValueError("SLACK_USERS_FILE was not provided")
                users_payload = _load_users_payload_from_file(users_file)

            parsed = UsersConfig(**users_payload)
            # Merge YAML/JSON users into the always-present .env user.
            for u in parsed.users:
                if u.name == env_user_name:
                    raise ValueError(
                        f"User '{env_user_name}' is defined in both .env and users config; rename one"
                    )
            users.extend(parsed.users)

            # Keep parsed defaults as metadata, but missing per-message user always uses .env user.
            if parsed.default_user is not None:
                default_user = parsed.default_user
            strategy = parsed.strategy
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid users config JSON: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid users config YAML: {e}") from e
        except (OSError, ValidationError, TypeError) as e:
            raise ValueError(f"Invalid users config: {e}") from e
    # else: use .env user only

    app_config = AppConfig(
        workspace=workspace,
        users=users,
        default_user=default_user,
        strategy=strategy,
    )

    logger.info(
        "Configuration loaded successfully (%d user%s)",
        len(app_config.users),
        "s" if len(app_config.users) != 1 else "",
    )
    console.print(
        f"[bold green]✓ Configuration loaded ({len(app_config.users)} user{'s' if len(app_config.users) != 1 else ''})[/bold green]"
    )
    return app_config, env


def parse_rich_text_from_string(text: str) -> list[dict[str, Any]]:
    """Parse markdown-like formatting and convert to Slack rich_text elements.

    Args:
        text: Input text with markdown-like formatting

    Returns:
        List of Slack rich_text elements

    Raises:
        InvalidMessageFormatError: If text format is invalid
    """
    if not isinstance(text, str):
        logger.error(f"Invalid text type: {type(text)}, expected str")
        raise InvalidMessageFormatError(f"Text must be a string, got {type(text)}")

    if not text.strip():
        logger.warning("Empty text provided for parsing")
        return [{"type": "text", "text": " "}]

    logger.debug(f"Parsing message text: {text[:50]}...")

    elements = []
    lines = text.split("\n")

    for line_idx, line in enumerate(lines):
        is_bullet = line.strip().startswith("•") or (
            line.strip().startswith("-") and len(line.strip()) > 1 and line.strip()[1] == " "
        )

        if is_bullet:
            if line_idx > 0 and not lines[line_idx - 1].strip().startswith(("•", "-")):
                elements.append({"type": "text", "text": "\n"})
            line_content = re.sub(r"^[\s•-]+", "", line).lstrip()
        else:
            line_content = line

        pattern = re.compile(
            r"(\*\*)([^*]+?)\1|"  # **bold**
            r"(\*)([^\s*][^*]*?[^\s*]|[^\s*])\3(?!\*)|"  # *bold*
            r"(_)([^_]+?)\5|"  # _italic_
            r"(~)([^~]+?)\7|"  # ~strikethrough~
            r"(`)([^`]+?)\9|"  # `code`
            r"(<(https?://[^|>]+)(?:\|([^>]+))?[^<]*>)|"  # <url|label> or <url>
            r"(https?://[^\s<>]+)|"  # Raw URLs
            r"(:([a-z_0-9]+):)|"  # :emoji_name:
            r"(@(here|channel|everyone))\b|"  # @here, @channel, @everyone (broadcast)
            r"(@([a-zA-Z0-9_.-]+))"  # @username mentions
        )

        pos = 0
        for match in pattern.finditer(line_content):
            if match.start() > pos:
                plain_text = line_content[pos : match.start()]
                if plain_text:
                    elements.append({"type": "text", "text": plain_text})

            if match.group(2):  # **bold**
                elements.append({"type": "text", "text": match.group(2), "style": {"bold": True}})  # type: ignore[dict-item]
            elif match.group(4):  # *bold*
                elements.append({"type": "text", "text": match.group(4), "style": {"bold": True}})  # type: ignore[dict-item]
            elif match.group(6):  # _italic_
                elements.append({"type": "text", "text": match.group(6), "style": {"italic": True}})  # type: ignore[dict-item]
            elif match.group(8):  # ~strikethrough~
                elements.append({"type": "text", "text": match.group(8), "style": {"strike": True}})  # type: ignore[dict-item]
            elif match.group(10):  # `code`
                elements.append({"type": "text", "text": match.group(10), "style": {"code": True}})  # type: ignore[dict-item]
            elif match.group(12):  # <url|label> or <url>
                url = match.group(12)
                label = match.group(13) if match.group(13) else url
                elements.append({"type": "link", "url": url, "text": label})
            elif match.group(14):  # Raw URL
                url = match.group(14)
                # Extract GitHub issue/PR number if available
                if "github.com" in url:
                    if "/pull/" in url or "/issues/" in url:
                        # Extract just the repo and number for cleaner display
                        parts = url.rstrip("/").split("/")
                        if len(parts) >= 2:
                            label = f"{parts[-2]}/{parts[-1]}"
                        else:
                            label = url
                    else:
                        label = url.split("/")[-1][:20]
                else:
                    label = url[:30] + ("..." if len(url) > 30 else "")
                elements.append({"type": "link", "url": url, "text": label})
            elif match.group(16):  # :emoji:
                emoji_name = match.group(16)
                logger.debug(f"Found emoji: {emoji_name}")
                elements.append({"type": "emoji", "name": emoji_name})
            elif match.group(18):  # @here, @channel, @everyone (broadcast)
                broadcast_type = match.group(18)
                logger.debug(f"Found broadcast mention: @{broadcast_type}")
                elements.append({"type": "broadcast", "range": broadcast_type})
            elif match.group(19):  # @username mentions
                username = match.group(20)
                logger.debug(f"Found user mention: @{username}")
                # Render as highlighted text since we don't have user IDs
                elements.append({"type": "text", "text": f"@{username}", "style": {"bold": True}})  # type: ignore[dict-item]

            pos = match.end()

        if pos < len(line_content):
            remaining = line_content[pos:]
            if remaining:
                elements.append({"type": "text", "text": remaining})

        if line_idx < len(lines) - 1:
            elements.append({"type": "text", "text": "\n"})

    return elements if elements else [{"type": "text", "text": text}]


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, SlackNetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def add_reaction(channel: str, timestamp: str, emoji: str, config: dict[str, str]) -> bool:
    """Add a reaction to a message with retry logic.

    Args:
        channel: Slack channel ID
        timestamp: Message timestamp
        emoji: Emoji name without colons (e.g., 'rocket')
        config: Configuration dictionary

    Returns:
        True if reaction was added successfully, False otherwise

    Raises:
        SlackNetworkError: If network connection fails after retries
        SlackRateLimitError: If rate limit is exceeded
    """
    logger.debug(f"Adding reaction :{emoji}: to message {timestamp}")

    data = {
        "token": config["SLACK_XOXC_TOKEN"],
        "channel": channel,
        "timestamp": timestamp,
        "name": emoji,
    }

    cookies = _build_slack_cookies(config)
    headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    try:
        response = httpx.post(
            f"{config['SLACK_ORG_URL']}/api/reactions.add",
            data=data,
            cookies=cookies,
            headers=headers,
            timeout=5,
        )
        result: dict[str, Any] = response.json()

        if result.get("ok"):
            logger.debug(f"Successfully added reaction :{emoji}:")
            return True

        error = result.get("error", "unknown")

        # Optional auth debugging (no secrets)
        if config.get("__DEBUG_AUTH") == "1":
            _print_auth_debug(
                endpoint="reactions.add",
                config=config,
                response=response,
                slack_result=result,
            )

        # Handle rate limiting
        if error == "ratelimited":
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"Rate limited on reactions.add, retry after {retry_after}s")
            raise SlackRateLimitError(f"Rate limited, retry after {retry_after}s")

        # Handle invalid emoji
        if error == "invalid_name":
            logger.warning(f"Invalid emoji name: {emoji}")
            return False

        # Handle already reacted
        if error == "already_reacted":
            logger.debug(f"Already reacted with :{emoji}:")
            return True

        logger.warning(f"Failed to add reaction: {error}")
        return False

    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error(f"Network error adding reaction: {e}")
        if config.get("__DEBUG_AUTH") == "1":
            _print_auth_debug(endpoint="reactions.add", config=config, note=f"network_error: {e}")
        raise SlackNetworkError(f"Network error: {e}") from e
    except (SlackRateLimitError, SlackAPIError):
        # Re-raise our custom exceptions
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Slack API response: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding reaction: {e}")
        return False


def get_user_repos(gh_token: str, max_repos: int = 5) -> list[str]:
    """Fetch the authenticated user's repos, prioritizing recent activity.

    Args:
        gh_token: GitHub API token
        max_repos: Maximum number of repos to return

    Returns:
        List of repository full names (owner/repo)
    """
    try:
        logger.debug(f"Fetching user's repositories (top {max_repos})...")
        response = httpx.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {gh_token}"},
            params={"sort": "updated", "per_page": 20},
            timeout=10,
        )
        if response.status_code == 200:
            repos = response.json()
            repo_names = [r.get("full_name") for r in repos if r.get("full_name")]
            selected = repo_names[:max_repos]
            console.print(
                f"[bold green]✓ Found {len(repo_names)} user repos, using top {len(selected)}[/bold green]"
            )
            for i, repo in enumerate(selected, 1):
                console.print(f"  [cyan][{i}][/cyan] {repo}")
            return selected
        else:
            logger.warning(f"GitHub API returned status {response.status_code}")
    except httpx.TimeoutException:
        logger.error("Timeout fetching user repos from GitHub")
    except Exception as e:
        logger.error(f"Error fetching user repos: {type(e).__name__}: {e}")

    return []


def get_github_context(config: dict[str, str]) -> dict[str, Any] | None:
    """Fetch recent commits, PRs, and issues from user's repositories.

    Args:
        config: Configuration dictionary with optional GITHUB_TOKEN

    Returns:
        Dictionary with commits, prs, and issues, or None if unavailable
    """
    console.print("\n[bold blue]━━━ GitHub Context ━━━[/bold blue]")

    # Try to get GitHub token from config or gh CLI
    gh_token = config.get("GITHUB_TOKEN")
    if not gh_token:
        try:
            logger.debug("GITHUB_TOKEN not set, attempting to get from 'gh auth token'...")
            result = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                gh_token = result.stdout.strip()
                console.print("[bold green]✓ Using GitHub token from 'gh auth token'[/bold green]")
            else:
                logger.warning(f"'gh auth token' failed with return code {result.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("Timeout running 'gh auth token'")
        except FileNotFoundError:
            logger.error("'gh' command not found. Install GitHub CLI or set GITHUB_TOKEN env var")
    else:
        logger.debug("Using GITHUB_TOKEN from environment")

    if not gh_token:
        logger.warning("No GitHub token available, skipping GitHub context")
        return None

    context: dict[str, Any] = {"commits": [], "prs": [], "issues": []}
    headers = {"Authorization": f"Bearer {gh_token}"}

    try:
        # Get user's repos
        repos = get_user_repos(gh_token)
        if not repos:
            logger.warning("No user repos found, skipping GitHub context")
            return None

        logger.info(f"Fetching context from {len(repos)} repositories...")

        # Fetch data from multiple repos
        for repo_idx, repo in enumerate(repos, 1):
            try:
                logger.debug(f"  [{repo_idx}/{len(repos)}] Processing {repo}...")

                # Get recent commits
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/commits",
                    headers=headers,
                    params={"per_page": 5},
                    timeout=10,
                )
                if response.status_code == 200:
                    commits = response.json()
                    fetched = len(commits[:3])
                    context["commits"].extend(
                        [
                            {
                                "message": c.get("commit", {}).get("message", ""),
                                "author": c.get("commit", {})
                                .get("author", {})
                                .get("name", "Unknown"),
                                "repo": repo,
                                "date": c.get("commit", {}).get("author", {}).get("date", ""),
                            }
                            for c in commits[:3]
                        ]
                    )
                    logger.debug(f"    ✓ Fetched {fetched} commits")
                else:
                    logger.debug(f"    ⚠ Commits API returned {response.status_code}")

                # Get recent PRs
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/pulls",
                    headers=headers,
                    params={"state": "all", "per_page": 5},
                    timeout=10,
                )
                if response.status_code == 200:
                    prs = response.json()
                    fetched = len(prs[:3])
                    context["prs"].extend(
                        [
                            {
                                "title": pr.get("title", ""),
                                "number": pr.get("number", 0),
                                "state": pr.get("state", ""),
                                "repo": repo,
                                "url": pr.get("html_url", ""),
                                "author": pr.get("user", {}).get("login", "Unknown"),
                            }
                            for pr in prs[:3]
                        ]
                    )
                    logger.debug(f"    ✓ Fetched {fetched} PRs")
                else:
                    logger.debug(f"    ⚠ PRs API returned {response.status_code}")

                # Get recent issues
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/issues",
                    headers=headers,
                    params={"state": "all", "per_page": 5},
                    timeout=10,
                )
                if response.status_code == 200:
                    issues = response.json()
                    issues_filtered = [i for i in issues[:3] if not i.get("pull_request")]
                    fetched = len(issues_filtered)
                    context["issues"].extend(
                        [
                            {
                                "title": i.get("title", ""),
                                "number": i.get("number", 0),
                                "repo": repo,
                                "url": i.get("html_url", ""),
                                "labels": [label.get("name", "") for label in i.get("labels", [])],
                            }
                            for i in issues_filtered
                        ]
                    )
                    logger.debug(f"    ✓ Fetched {fetched} issues")
                else:
                    logger.debug(f"    ⚠ Issues API returned {response.status_code}")

            except httpx.TimeoutException:
                logger.error(f"  Timeout fetching data from {repo}")
                continue
            except Exception as e:
                logger.error(f"  Error fetching data from {repo}: {type(e).__name__}: {e}")
                continue

        # Trim to reasonable sizes
        context["commits"] = context["commits"][:5]
        context["prs"] = context["prs"][:5]
        context["issues"] = context["issues"][:5]

        logger.info(
            f"✓ GitHub context loaded: {len(context['commits'])} commits, "
            f"{len(context['prs'])} PRs, {len(context['issues'])} issues"
        )
        return context if context["commits"] or context["prs"] or context["issues"] else None

    except Exception as e:
        logger.error(f"Error fetching GitHub context: {type(e).__name__}: {e}")
        return None


def generate_messages_with_ai(
    config: dict[str, str],
    ai_config: AIConfigModel | None = None,
    github_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Generate realistic Slack conversations using OpenRouter AI.

    Args:
        config: Configuration dictionary (for backward compat, used for OPENROUTER_API_KEY fallback)
        ai_config: AI configuration model with model, api_key, temperature, etc.
        github_context: Optional GitHub context for more realistic messages

    Returns:
        List of generated messages, or None if generation fails
    """
    # Get API key (env var > ai_config > config dict fallback)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key and ai_config:
        openrouter_key = ai_config.api_key
    if not openrouter_key:
        openrouter_key = config.get("OPENROUTER_API_KEY")

    if not openrouter_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping AI generation")
        return None

    # Get AI settings from config or use defaults
    model = ai_config.model if ai_config else "google/gemini-2.0-flash-exp"
    temperature = ai_config.temperature if ai_config else 0.7
    max_tokens = ai_config.max_tokens if ai_config else 4000
    system_prompt = (
        ai_config.system_prompt
        if ai_config and ai_config.system_prompt
        else DEFAULT_AI_SYSTEM_PROMPT
    )

    logger.info(f"Generating conversations with {model}...")

    # Build prompt with GitHub context if available
    base_prompt = system_prompt

    if github_context:
        context_str = "\n\n## REAL PROJECT CONTEXT (USE THIS!)\nYou have access to real GitHub data from the user's repos. HEAVILY reference this in your messages:\n"
        if github_context.get("commits"):
            context_str += "\n### Recent Commits (reference these!):\n"
            for c in github_context["commits"][:5]:
                context_str += f"- `{c['message'][:60]}` in *{c['repo']}* by _{c['author']}_\n"
        if github_context.get("prs"):
            context_str += "\n### Open/Recent PRs (discuss, review, question these!):\n"
            for pr in github_context["prs"][:5]:
                url = pr.get("url", "")
                context_str += (
                    f"- <{url}|#{pr['number']}: {pr['title']}> ({pr['state']}) by @{pr['author']}\n"
                )
        if github_context.get("issues"):
            context_str += "\n### Issues (ask about, update, close these!):\n"
            for issue in github_context["issues"][:5]:
                url = issue.get("url", "")
                labels = ", ".join(issue["labels"]) if issue["labels"] else "no labels"
                context_str += f"- <{url}|#{issue['number']}: {issue['title']}> [{labels}]\n"

        context_str += "\n### How to use this context:\n"
        context_str += "- Reference ACTUAL PR numbers and URLs from above\n"
        context_str += "- Discuss real commit messages (ask questions, give feedback)\n"
        context_str += "- Mention real issues that need attention\n"
        context_str += (
            "- Include workflow run links like https://github.com/owner/repo/actions/runs/123\n"
        )
        context_str += "- Ask about specific code changes from PRs\n"
        context_str += "- Discuss merge conflicts, review comments, CI failures on these PRs\n"
        context_str += "- Create realistic support threads around this actual project context\n"

        prompt = base_prompt + "\n\n" + context_str
        logger.debug("AI prompt includes GitHub context")
    else:
        prompt = base_prompt
        logger.debug("AI prompt using default template (no GitHub context)")

    # JSON Schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": "Array of Slack messages with varied tone and length",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The main message text with Slack formatting",
                        },
                        "replies": {
                            "type": "array",
                            "description": "Array of reply messages (can be empty, single emoji, or detailed)",
                            "items": {"type": "string"},
                        },
                        "reactions": {
                            "type": "array",
                            "description": "Emoji reactions to add to the main message (without colons, e.g., 'rocket', 'eyes')",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["text", "replies", "reactions"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["messages"],
        "additionalProperties": False,
    }

    try:
        with console.status(f"[bold magenta]Generating messages with {model}...", spinner="dots"):
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/echohello-dev/yap-on-slack",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.9,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "slack_messages", "strict": True, "schema": schema},
                    },
                },
                timeout=30,
            )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            try:
                data = json.loads(content)
                messages: list[dict[str, Any]] = data.get("messages", [])
                logger.info(f"✓ Generated {len(messages)} messages from {model}")
                return messages
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {type(e).__name__}: {e}")
                logger.debug(f"   Content: {content[:200]}")
                return None
        else:
            error_body = response.text
            logger.error(f"AI generation failed: HTTP {response.status_code}")
            logger.debug(f"   Response: {error_body[:200]}")
            return None
    except httpx.TimeoutException:
        logger.error("AI generation timed out (30s)")
        return None
    except Exception as e:
        logger.error(f"AI generation error: {type(e).__name__}: {e}")
        return None


def load_messages(messages_path: Path | None = None) -> list[dict[str, Any]]:
    """Load messages from messages.json or use defaults."""
    messages_file = messages_path if messages_path else Path("messages.json")

    if messages_file.exists():
        try:
            with messages_file.open() as f:
                data = json.load(f)
                # Validate messages with pydantic
                try:
                    validated = [Message(**msg) for msg in data]
                    console.print(
                        f"[bold green]✓ Loaded {len(validated)} messages from {messages_file}[/bold green]"
                    )
                    return [msg.model_dump() for msg in validated]
                except (ValidationError, TypeError) as e:
                    logger.error(f"Message validation failed: {e}")
                    console.print(
                        "[bold red]✗ Invalid message format. Using default messages.[/bold red]"
                    )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {messages_file}: {e}")

    # Default fallback messages
    return [
        {
            "text": "Hey team, I'm getting a *403* on the new dashboard analytics endpoint :thinking_face: Has anyone else run into this?",
            "replies": [
                "Did you check if your token has the `analytics.read` scope?",
                "Also, make sure the URL is `/api/v3/analytics`, not `/api/analytics`. Easy typo to make",
            ],
        },
        {
            "text": "Quick question - what's our _data retention policy_ for session logs? Need this for the compliance audit",
            "replies": ["90 days in hot storage, then goes to cold storage for 7 years per policy"],
        },
        {
            "text": "*Issue* in prod :bug:: Database query timeout on user auth\n`TypeError: Cannot read property 'userId' of undefined` at `user-service.js:45`\nAnyone know what we deployed?",
            "replies": [
                "Did we change the auth middleware recently?",
                "Yeah, I see it now. JWT decode is failing silently. Let me push a fix",
            ],
        },
        {
            "text": "Could someone send me the rate limiter config docs? Setting up limits for the _payment service_ and need guidance",
            "replies": [],
        },
        {
            "text": "Onboarding new team member tomorrow - where can I find the local dev setup guide? Need the Docker compose instructions :wave:",
            "replies": ["Root `README` has everything including the Docker compose setup :whale:"],
        },
        {
            "text": "Has anyone successfully integrated <https://stripe.com/docs/webhooks|Stripe webhooks>? Signature validation keeps failing and I can't figure out why",
            "replies": [
                "Make sure you're using the webhook secret from the dashboard, not your API secret",
                "Also gotta read the raw request body before parsing as JSON. That's a common gotcha",
            ],
        },
        {
            "text": "Could use some help - how does the *authentication flow* work on mobile? Is there a sequence diagram or docs somewhere?",
            "replies": [],
        },
        {
            "text": "Quick question on _database migrations_: should I create a new file or modify the existing one? Adding a column to the `users` table",
            "replies": [
                "Always create a *new migration file*. Never modify deployed migrations - that's how things break :no_entry:"
            ],
        },
        {
            "text": "Getting timeout errors on `/api/v2/reports` when generating large reports. Timeout is set to 30s currently - what's the recommended value?",
            "replies": [
                "60s is typical for report generation. Or consider making it _async with a callback_ if reports are heavy"
            ],
        },
        {
            "text": "What's the best approach for handling *retries* in the payment module? How do you differentiate between `transient` and `permanent` failures?",
            "replies": [],
        },
        {
            "text": "Question - _staging_ vs _pre-prod_: which one should I use for feature flag testing? :rocket:",
            "replies": [
                "Staging is for integration testing. Pre-prod mirrors production config. Use *pre-prod* for feature flags"
            ],
        },
        {
            "text": "Looking for documentation on *user permissions*. Need to implement role-based access control for the admin dashboard",
            "replies": [],
        },
        {
            "text": "*Push notifications* aren't showing on iOS. Has anyone worked with the notification service recently? :iphone:",
            "replies": [
                "When's the last time you updated the *APNs certificate*? Pretty sure it expired :warning:",
                "Oh, that's probably it! Where can I find the new one? :bulb:",
            ],
        },
        {
            "text": "*Security question* - do we automatically redact _credit card numbers_ in logs, or should they be manually scrubbed?",
            "replies": [],
        },
        {
            "text": "Seeing _inconsistent results_ from the search API. Same query returns different results on subsequent calls. Is Redis caching enabled?",
            "replies": [
                "Yes, Redis caching with 5-minute TTL. Could be cache warming issues :mag:"
            ],
        },
        {
            "text": ":rocket: *heads up* - deploying _auth service v2.1_ to staging in 30min. if you're testing auth stuff plz use `staging-v2`",
            "replies": [
                "thanks for the heads up! when's it going to prod?",
                "probably friday if no issues in staging. ill ping the channel",
            ],
        },
        {
            "text": "just merged <https://github.com/echohello-dev/yap-on-slack/pull/487|PR #487> - refactored the payment webhook handler to be more robust. plz review when u get a sec :eyes:",
            "replies": ["lgtm! just left a comment on line 42 :+1:", "approved! ship it :ship:"],
        },
        {
            "text": ":warning: *ATTENTION*: we're deprecating the old `/api/v1/users` endpoint _next month_. migrate to `/api/v2/users` asap. see <https://docs.example.com|docs> for migration guide",
            "replies": [
                "how long do we have to migrate?",
                "until feb 15. we're sending emails to all customers but best to get it done early",
            ],
        },
        {
            "text": "*performance update*: search endpoint now doing _fuzzy matching_. this may affect some queries but accuracy is way better. feedback welcome :mag:",
            "replies": [
                "nice! how's the perf impact?",
                "minimal actually. redis caching handles most of it :zap:",
            ],
        },
        {
            "text": "*planned maintenance*: database will be down for upgrades tomorrow 2am-3am pst. notify ur customers pls :warning:",
            "replies": [
                "done. already sent notifications :email:",
                "thx. also FYI we're upgrading to `postgres 15` :elephant:",
            ],
        },
        {
            "text": "*FYI* rolling out new UI theme next week. if things look weird that's expected lol. should stabilize by wed :art:",
            "replies": [
                "dark mode finally?? :moon:",
                "yeah! and better mobile responsive too :iphone:",
            ],
        },
        {
            "text": "quick *status update*: api latency spiked this morning around 9am but we've sorted it now. no data loss :relieved:",
            "replies": [
                "what caused it?",
                "one of the load balancers got overloaded. scaled it up :muscle:",
            ],
        },
    ]


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, SlackNetworkError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
def post_message(
    text: str, config: dict[str, str], thread_ts: str | None = None
) -> dict[str, Any] | None:
    """Post a single message to Slack with retry logic.

    Args:
        text: Message text with markdown-like formatting
        config: Configuration dictionary with Slack credentials
        thread_ts: Optional thread timestamp for replies

    Returns:
        Response dict if successful, None otherwise

    Raises:
        SlackNetworkError: If network connection fails after retries
        SlackRateLimitError: If rate limit is exceeded
        InvalidMessageFormatError: If message format is invalid
    """
    logger.debug(f"Posting message{' to thread ' + thread_ts if thread_ts else ''}: {text[:50]}...")

    try:
        elements = parse_rich_text_from_string(text)
    except InvalidMessageFormatError as e:
        logger.error(f"Invalid message format: {e}")
        raise

    blocks = [
        {"type": "rich_text", "elements": [{"type": "rich_text_section", "elements": elements}]}
    ]

    data = {
        "token": config["SLACK_XOXC_TOKEN"],
        "channel": config["SLACK_CHANNEL_ID"],
        "type": "message",
        "xArgs": "{}",
        "unfurl": "[]",
        "client_context_team_id": config["SLACK_TEAM_ID"],
        "blocks": json.dumps(blocks),
        "include_channel_perm_error": "true",
        "client_msg_id": str(uuid.uuid4()),
        "_x_reason": "webapp_message_send",
        "_x_mode": "online",
        "_x_sonic": "true",
        "_x_app_name": "client",
    }

    if thread_ts:
        data["reply_broadcast"] = "false"
        data["thread_ts"] = thread_ts

    cookies = _build_slack_cookies(config)
    headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    try:
        # Use form-urlencoded like the working script (not multipart)
        response = httpx.post(
            f"{config['SLACK_ORG_URL']}/api/chat.postMessage",
            data=data,
            cookies=cookies,
            headers=headers,
            timeout=10,
        )
        result: dict[str, Any] = response.json()

        if result.get("ok"):
            logger.debug(f"Successfully posted message: {result.get('ts')}")
            return result

        error = result.get("error", "unknown")

        # Optional auth debugging (no secrets)
        if config.get("__DEBUG_AUTH") == "1":
            _print_auth_debug(
                endpoint="chat.postMessage",
                config=config,
                cookies=cookies,
                response=response,
                slack_result=result,
                note=f"thread_ts={'yes' if thread_ts else 'no'}",
            )

        # Handle rate limiting
        if error == "ratelimited":
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"Rate limited on chat.postMessage, retry after {retry_after}s")
            raise SlackRateLimitError(f"Rate limited, retry after {retry_after}s")

        # Handle channel errors
        if error in ("channel_not_found", "not_in_channel"):
            logger.error(f"Channel error: {error}")
            raise SlackAPIError(f"Channel error: {error}")

        # Handle auth errors
        if error in ("invalid_auth", "token_revoked", "token_expired"):
            logger.error(f"Authentication error: {error}")
            raise SlackAPIError(f"Authentication error: {error}")

        logger.error(f"Slack API error: {error}")
        return None

    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.error(f"Network error posting message: {e}")
        if config.get("__DEBUG_AUTH") == "1":
            _print_auth_debug(
                endpoint="chat.postMessage", config=config, note=f"network_error: {e}"
            )
        raise SlackNetworkError(f"Network error: {e}") from e
    except (SlackRateLimitError, SlackAPIError):
        # Re-raise our custom exceptions
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Slack API response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error posting message: {e}")
        return None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Post realistic support messages to Slack using session tokens.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default messages.json
  %(prog)s

  # Use custom messages file
  %(prog)s --messages custom-messages.json

  # Dry run (validate without posting)
  %(prog)s --dry-run

  # Limit number of messages
  %(prog)s --limit 3

  # Custom delay between messages
  %(prog)s --delay 5
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml file (default: ./config.yaml or ~/.config/yap-on-slack/config.yaml)",
    )
    parser.add_argument(
        "--messages",
        type=Path,
        help="Path to custom messages JSON file (default: messages.json)",
    )
    parser.add_argument(
        "--users",
        type=Path,
        help="Path to users YAML config (overrides SLACK_USERS_FILE)",
    )
    parser.add_argument(
        "--user",
        type=str,
        help="Force a specific user name for all top-level messages",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and messages without posting to Slack",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of messages to post (default: all)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between messages (default: 2.0)",
    )
    parser.add_argument(
        "--reply-delay",
        type=float,
        default=1.0,
        help="Delay in seconds between replies (default: 1.0)",
    )
    parser.add_argument(
        "--reaction-delay",
        type=float,
        default=0.5,
        help="Delay in seconds before adding reactions (default: 0.5)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Generate messages using OpenRouter (auto-selects best model, requires OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--debug-auth",
        action="store_true",
        help="Print safe (redacted) Slack request/response diagnostics on failures",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Update log level if verbose
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)

    # Try unified config first, fall back to legacy config
    try:
        app_config, env = load_unified_config(args.config)
        # Get unified config if it was loaded
        discovered_config = discover_config_file(args.config)
        unified_config_obj: UnifiedConfig | None = None
        if discovered_config:
            with discovered_config.open() as f:
                config_data = yaml.safe_load(f)
            if isinstance(config_data, dict):
                unified_config_obj = UnifiedConfig(**config_data)
    except (ValueError, FileNotFoundError) as e:
        # Fallback to legacy config loading if unified config fails
        logger.debug(f"Unified config failed, trying legacy: {e}")
        try:
            app_config, env = load_config(args.users)
            unified_config_obj = None
        except Exception as legacy_error:
            logger.error(f"Configuration loading failed: {legacy_error}")
            raise

    # Try AI generation if requested
    messages: list[dict[str, Any]] | None = None
    if args.use_ai:
        github_context = get_github_context(env)
        ai_config = unified_config_obj.ai if unified_config_obj else None
        messages = generate_messages_with_ai(env, ai_config, github_context)
        if not messages:
            logger.warning("AI generation failed, falling back to default messages")
        else:
            _assign_users_to_ai_messages(app_config, messages)

    # Check for messages in unified config
    if not messages and unified_config_obj and unified_config_obj.messages:
        logger.info(f"Using {len(unified_config_obj.messages)} messages from config file")
        # Convert MessageConfigModel to dict format expected by downstream code
        messages = []
        for msg_config in unified_config_obj.messages:
            msg_dict: dict[str, Any] = {
                "text": msg_config.text,
                "user": msg_config.user,
                "reactions": msg_config.reactions,
                "replies": [],
            }
            # Convert replies
            for reply in msg_config.replies:
                if isinstance(reply, str):
                    msg_dict["replies"].append(reply)
                else:
                    msg_dict["replies"].append(
                        {
                            "text": reply.text,
                            "user": reply.user,
                        }
                    )
            messages.append(msg_dict)
        console.print(f"[green]✓ Loaded {len(messages)} messages from config file[/green]")

    # Fall back to file or default messages
    if not messages:
        messages = load_messages(args.messages)

    # Apply limit if specified
    if args.limit and args.limit > 0:
        messages = messages[: args.limit]
        console.print(f"[yellow]ℹ Limited to first {args.limit} messages[/yellow]")

    total_posts = sum(1 + len(msg.get("replies", [])) for msg in messages)

    console.print("\n[bold blue]━━━ Posting Messages ━━━[/bold blue]")
    console.print(
        Panel.fit(
            f"[bold cyan]{len(messages)}[/bold cyan] messages\n"
            f"[bold cyan]{total_posts}[/bold cyan] total posts (including replies)\n"
            f"[yellow]{'DRY RUN - No messages will be posted' if args.dry_run else 'LIVE - Messages will be posted'}[/yellow]",
            title="[bold]Slack Post Summary[/bold]",
            border_style="yellow" if args.dry_run else "blue",
        )
    )

    # Preview messages in logs
    console.print("\n[bold blue]━━━ Message Preview ━━━[/bold blue]\n")
    for i, msg_data in enumerate(messages, 1):
        text = str(msg_data["text"])
        msg_user = msg_data.get("user")
        user_display = (
            f"[bold magenta]@{msg_user}[/bold magenta]" if msg_user else "[dim]@default[/dim]"
        )

        # Main message
        console.print(f"[bold cyan]#{i}[/bold cyan] {user_display}")
        # Indent and format message text (truncate if very long)
        preview_text = text[:200] + "..." if len(text) > 200 else text
        console.print(f"    [white]{preview_text}[/white]")

        # Show reactions if present
        reactions = msg_data.get("reactions", [])
        if reactions:
            reaction_str = " ".join([f":{r.strip(':')}:" for r in reactions])
            console.print(f"    [yellow]reactions:[/yellow] {reaction_str}")

        # Show replies as thread
        replies = msg_data.get("replies", [])
        if replies:
            console.print(
                f"    [dim]└─ [bold]{len(replies)} repl{'y' if len(replies) == 1 else 'ies'}[/bold][/dim]"
            )
            for reply_idx, reply in enumerate(replies):
                if isinstance(reply, str):
                    reply_text = reply
                    reply_user = None
                else:
                    reply_text = str(reply.get("text", ""))
                    reply_user = reply.get("user")

                reply_user_display = (
                    f"[magenta]@{reply_user}[/magenta]" if reply_user else "[dim]@default[/dim]"
                )
                prefix = "└─" if reply_idx == len(replies) - 1 else "├─"
                # Truncate long replies
                reply_preview = reply_text[:150] + "..." if len(reply_text) > 150 else reply_text
                console.print(
                    f"       [dim]{prefix}[/dim] {reply_user_display}: [white]{reply_preview}[/white]"
                )

        console.print()  # Empty line between messages

    if args.dry_run:
        console.print("[bold green]✓ Dry run complete - all validations passed[/bold green]")
        console.print(f"[cyan]Would post {total_posts} messages to Slack[/cyan]")
        return

    success = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Posting messages...", total=len(messages))

        for i, msg_data in enumerate(messages, 1):
            text = str(msg_data["text"])
            msg_user = msg_data.get("user")
            user_display = f"@{msg_user}" if msg_user else "@default"
            preview_text = text[:80] + "..." if len(text) > 80 else text

            progress.update(task, description=f"[green]Message {i}/{len(messages)}")
            progress.console.print(
                f"[bold cyan]#{i}[/bold cyan] [magenta]{user_display}[/magenta]: {preview_text}"
            )

            forced_user = args.user
            message_user = msg_data.get("user")
            # If --user is specified, use that; else if message has user field, use that;
            # else pass None to let select_user use round-robin/random strategy
            user_name = (
                forced_user if forced_user else (str(message_user) if message_user else None)
            )

            posting_user = app_config.select_user(name=user_name, message_index=i - 1)
            request_config = _merge_request_config(app_config, posting_user)

            if args.debug_auth:
                # A sentinel key so helpers can print diagnostics without changing function signatures.
                request_config["__DEBUG_AUTH"] = "1"

            try:
                result = post_message(text, request_config)

                if result:
                    success += 1
                    thread_ts = result["ts"]
                    progress.console.print("    [green]✓[/green] Posted")

                    # Add AI-generated reactions first (if present)
                    ai_reactions = msg_data.get("reactions", [])
                    if ai_reactions:
                        reaction_display = " ".join([f":{r.strip(':')}:" for r in ai_reactions])
                        progress.console.print(
                            f"    [yellow]  + reactions:[/yellow] {reaction_display}"
                        )
                    for reaction_emoji in ai_reactions:
                        try:
                            time.sleep(args.reaction_delay)
                            # Strip colons if present
                            emoji_name = reaction_emoji.strip(":")
                            if emoji_name:
                                add_reaction(
                                    request_config["SLACK_CHANNEL_ID"],
                                    thread_ts,
                                    emoji_name,
                                    request_config,
                                )
                        except (SlackNetworkError, RetryError) as e:
                            logger.warning(f"Failed to add reaction after retries: {e}")
                        except SlackRateLimitError as e:
                            logger.warning(f"Rate limited adding reaction: {e}")

                    # Also add reaction if emoji found in message text (fallback for non-AI)
                    if not ai_reactions:
                        emoji_match = re.search(r":([a-z_0-9]+):", text)
                        if emoji_match:
                            progress.console.print(
                                f"    [yellow]  + reaction:[/yellow] :{emoji_match.group(1)}:"
                            )
                            try:
                                time.sleep(args.reaction_delay)
                                add_reaction(
                                    request_config["SLACK_CHANNEL_ID"],
                                    thread_ts,
                                    emoji_match.group(1),
                                    request_config,
                                )
                            except (SlackNetworkError, RetryError) as e:
                                logger.warning(f"Failed to add reaction after retries: {e}")
                            except SlackRateLimitError as e:
                                logger.warning(f"Rate limited adding reaction: {e}")

                    # Post replies
                    replies = msg_data.get("replies", [])
                    for reply_idx, reply in enumerate(replies):
                        time.sleep(args.reply_delay)
                        try:
                            if isinstance(reply, str):
                                reply_text = reply
                                reply_user_name: str | None = None
                            else:
                                reply_text = str(reply.get("text", ""))
                                reply_user_name = (
                                    str(reply.get("user"))
                                    if reply.get("user") is not None
                                    else None
                                )

                            if not reply_text.strip():
                                raise InvalidMessageFormatError("Reply text cannot be empty")

                            reply_user = app_config.select_user(
                                name=reply_user_name,
                                message_index=(i - 1) + 1 + reply_idx,
                            )
                            reply_user_display = (
                                f"@{reply_user_name}" if reply_user_name else f"@{reply_user.name}"
                            )
                            reply_preview = (
                                reply_text[:60] + "..." if len(reply_text) > 60 else reply_text
                            )
                            prefix = "└─" if reply_idx == len(replies) - 1 else "├─"
                            progress.console.print(
                                f"    [dim]{prefix}[/dim] [magenta]{reply_user_display}[/magenta]: {reply_preview}"
                            )

                            reply_request_config = _merge_request_config(app_config, reply_user)
                            if args.debug_auth:
                                reply_request_config["__DEBUG_AUTH"] = "1"
                            reply_result = post_message(
                                reply_text, reply_request_config, thread_ts=thread_ts
                            )
                            if reply_result:
                                success += 1
                            else:
                                failed += 1
                                logger.warning(f"Reply failed for message {i}")
                        except (SlackNetworkError, RetryError) as e:
                            logger.error(f"Failed to post reply after retries: {e}")
                            failed += 1
                        except SlackAPIError as e:
                            logger.error(f"Slack API error posting reply: {e}")
                            failed += 1
                else:
                    logger.error(f"Message {i} failed")
                    failed += 1

            except (SlackNetworkError, RetryError) as e:
                logger.error(f"Failed to post message {i} after retries: {e}")
                failed += 1
            except SlackAPIError as e:
                logger.error(f"Slack API error for message {i}: {e}")
                failed += 1
            except InvalidMessageFormatError as e:
                logger.error(f"Invalid message format for message {i}: {e}")
                failed += 1

            progress.advance(task)

            if i < len(messages):
                time.sleep(args.delay)

    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold green]✓ {success} successful[/bold green]\n"
            f"[bold red]✗ {failed} failed[/bold red]\n"
            f"[bold cyan]{success}/{total_posts} total posts[/bold cyan]",
            title="[bold]Completion Summary[/bold]",
            border_style="green" if failed == 0 else "yellow",
        )
    )


if __name__ == "__main__":
    main()
