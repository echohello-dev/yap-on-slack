#!/usr/bin/env python3
"""Post realistic support messages to Slack using session tokens."""

import argparse
import json
import logging
import os
import re
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
            "text": "Hey team, I'm getting a *403* on the new dashboard. Has anyone else seen this? :thinking_face:",
            "replies": [
                "Did you check if your token has the right scope?",
                "Also check the URL path - easy typo to make",
            ],
        },
        {
            "text": "Quick question - what's our _data retention policy_ for logs?",
            "replies": ["90 days in hot storage, then 7 years in cold per policy"],
        },
        {
            "text": "*Issue* in prod :bug:: Database timeout on user auth\n`TypeError: Cannot read property 'userId' of undefined`\nAnyone know what we deployed?",
            "replies": [
                "Did we change the auth middleware recently?",
                "Yeah, I see it now. JWT decode is failing. Let me push a fix",
            ],
        },
        {
            "text": ":rocket: *heads up* - deploying _auth service v2.1_ to staging in 30min",
            "replies": ["thanks for the heads up! when's prod?", "probably friday if no issues"],
        },
        {
            "text": ":warning: *ATTENTION*: deprecating `/api/v1/users` endpoint _next month_. migrate to `/api/v2/users` asap",
            "replies": ["how long do we have?", "until feb 15. best to do it early"],
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
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Update log level if verbose
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)

    config = load_config()
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
