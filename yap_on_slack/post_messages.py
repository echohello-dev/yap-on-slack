#!/usr/bin/env python3
"""Post realistic support messages to Slack using session tokens."""

import argparse
import json
import logging
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
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


class MessageReply(BaseModel):
    """Schema for message reply."""

    text: str

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
    replies: list[str] = []

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate text is not empty."""
        if not v or not v.strip():
            raise ValueError("Message text cannot be empty")
        return v

    @field_validator("replies")
    @classmethod
    def validate_replies(cls, v: list[str]) -> list[str]:
        """Validate replies are not empty."""
        for reply in v:
            if not reply or not reply.strip():
                raise ValueError("Reply text cannot be empty")
        return v


def load_config() -> dict[str, str]:
    """Load configuration from .env file with comprehensive validation."""
    logger.debug("Loading environment configuration from .env file")
    with console.status("[bold blue]Loading environment configuration...", spinner="dots"):
        try:
            raw_config = dotenv_values(".env")
        except Exception as e:
            logger.error(f"Failed to read .env file: {e}")
            raise ValueError(f"Cannot read .env file: {e}") from e
        time.sleep(0.2)

    # Convert to non-optional dict
    config: dict[str, str] = {}
    for key, value in raw_config.items():
        if value is not None:
            config[key] = value

    required_vars = [
        "SLACK_XOXC_TOKEN",
        "SLACK_XOXD_TOKEN",
        "SLACK_ORG_URL",
        "SLACK_CHANNEL_ID",
        "SLACK_TEAM_ID",
    ]
    missing = [var for var in required_vars if not config.get(var)]

    if missing:
        console.print("[bold red]✗ Missing required environment variables:[/bold red]")
        for var in missing:
            console.print(f"  [red]- {var}[/red]")
            logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Validate URL format
    org_url = config["SLACK_ORG_URL"]
    if not org_url.startswith("https://"):
        logger.error(f"Invalid SLACK_ORG_URL format: {org_url}")
        raise ValueError("SLACK_ORG_URL must start with https://")

    logger.info("All required environment variables loaded successfully")
    console.print("[bold green]✓ All required environment variables loaded[/bold green]")
    return config


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
            r"(:([a-z_0-9]+):)"  # :emoji_name:
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

    cookies = {"d": config["SLACK_XOXD_TOKEN"]}
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
                                "labels": [
                                    label.get("name", "") for label in i.get("labels", [])
                                ],
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
    config: dict[str, str], github_context: dict[str, Any] | None = None
) -> list[dict[str, Any]] | None:
    """Generate realistic Slack conversations using OpenRouter Gemini 3 Flash.

    Args:
        config: Configuration dictionary with OPENROUTER_API_KEY
        github_context: Optional GitHub context for more realistic messages

    Returns:
        List of generated messages, or None if generation fails
    """
    openrouter_key = config.get("OPENROUTER_API_KEY")
    if not openrouter_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping AI generation")
        return None

    logger.info("Generating conversations with Gemini 3 Flash...")

    # Build prompt with GitHub context if available
    base_prompt = """Generate 20 realistic Slack channel messages for an engineering team support channel.
Messages should include:
- Technical questions and troubleshooting
- Status updates and announcements
- Deployment notices
- Deprecation warnings
- Casual but professional tone (semi-formal)
- Some typos and natural language variation
- Minimal emoji use with :emoji_name: syntax (e.g., :rocket:, :warning:, :wave:)
- Links with format <url|label> for URLs
- Formatting: use *bold*, _italic_, ~strikethrough~, `code` for inline code
- Bullet points with • or - prefix
- Mix of quick questions, detailed issues, and team coordination
- Each message has 0-3 replies

IMPORTANT: Use markdown-like formatting in text:
- *bold text* for emphasis
- _italic text_ for secondary emphasis
- `code` for technical terms
- <https://example.com|link text> for URLs
- :emoji_name: for emojis
- • bullet points for lists

Example: "*Issue*: _Database timeout_ on <https://github.com|PR#123>. `SELECT` query taking 30s :warning:"
"""

    if github_context:
        context_str = "Use this real project context when generating messages. Reference actual repos, PRs, and issues:\n"
        if github_context.get("commits"):
            context_str += "\nRecent commits (repos touched):\n"
            for c in github_context["commits"][:3]:
                context_str += f"- {c['message'][:60]} ({c['repo']})\n"
        if github_context.get("prs"):
            context_str += "\nRecent PRs to reference:\n"
            for pr in github_context["prs"][:3]:
                url = pr.get("url", "")
                context_str += f"- #{pr['number']}: {pr['title']} ({pr['state']}) - <{url}>\n"
        if github_context.get("issues"):
            context_str += "\nRecent issues to reference:\n"
            for issue in github_context["issues"][:3]:
                url = issue.get("url", "")
                labels = ", ".join(issue["labels"]) if issue["labels"] else "no labels"
                context_str += f"- #{issue['number']}: {issue['title']} ({labels}) - <{url}>\n"

        context_str += "\n\nWhen generating messages:\n"
        context_str += "- Reference actual PR/issue numbers and URLs from the context above\n"
        context_str += "- Use raw GitHub URLs like https://github.com/owner/repo/issues/123\n"
        context_str += "- Include actual commit messages and PR titles from your repos\n"
        context_str += (
            "- Make questions/discussions specific to the repos and issues you actually work on\n"
        )

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
                "description": "Array of Slack messages",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The main message text"},
                        "replies": {
                            "type": "array",
                            "description": "Array of reply messages",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["text", "replies"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["messages"],
        "additionalProperties": False,
    }

    try:
        with console.status(
            "[bold magenta]Generating messages with Gemini 3 Flash...", spinner="dots"
        ):
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/echohello-dev/yap-on-slack",
                },
                json={
                    "model": "google/gemini-3-flash-preview",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4000,
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
                messages = data.get("messages", [])
                logger.info(f"✓ Generated {len(messages)} messages from Gemini 3 Flash")
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

    cookies = {"d": config["SLACK_XOXD_TOKEN"]}
    headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    try:
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
        "--messages",
        type=Path,
        help="Path to custom messages JSON file (default: messages.json)",
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
        help="Generate messages using OpenRouter Gemini 3 Flash (requires OPENROUTER_API_KEY)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Update log level if verbose
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)

    config = load_config()

    # Try AI generation if requested
    messages = None
    if args.use_ai:
        github_context = get_github_context(config)
        messages = generate_messages_with_ai(config, github_context)
        if not messages:
            logger.warning("AI generation failed, falling back to default messages")

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

    if args.dry_run:
        console.print("\n[bold green]✓ Dry run complete - all validations passed[/bold green]")
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
            progress.update(task, description=f"[green]Message {i}/{len(messages)}")
            text = msg_data["text"]

            try:
                result = post_message(text, config)

                if result:
                    success += 1
                    thread_ts = result["ts"]

                    # Add reaction if emoji found in message
                    emoji_match = re.search(r":([a-z_0-9]+):", text)
                    if emoji_match:
                        try:
                            time.sleep(args.reaction_delay)
                            add_reaction(
                                config["SLACK_CHANNEL_ID"], thread_ts, emoji_match.group(1), config
                            )
                        except (SlackNetworkError, RetryError) as e:
                            logger.warning(f"Failed to add reaction after retries: {e}")
                        except SlackRateLimitError as e:
                            logger.warning(f"Rate limited adding reaction: {e}")

                    # Post replies
                    for reply_text in msg_data.get("replies", []):
                        time.sleep(args.reply_delay)
                        try:
                            reply_result = post_message(reply_text, config, thread_ts=thread_ts)
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
