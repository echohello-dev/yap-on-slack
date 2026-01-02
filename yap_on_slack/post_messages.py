#!/usr/bin/env python3
"""Post realistic support messages to Slack using session tokens."""

import json
import logging
import re
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


def load_config() -> dict[str, str]:
    """Load configuration from .env file."""
    with console.status("[bold blue]Loading environment configuration...", spinner="dots"):
        config = dotenv_values(".env")
        time.sleep(0.2)

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
        raise ValueError("Missing required environment variables")

    console.print("[bold green]✓ All required environment variables loaded[/bold green]")
    return config


def parse_rich_text_from_string(text: str) -> list[dict]:
    """Parse markdown-like formatting and convert to Slack rich_text elements."""
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
                elements.append({"type": "text", "text": match.group(2), "style": {"bold": True}})
            elif match.group(4):  # *bold*
                elements.append({"type": "text", "text": match.group(4), "style": {"bold": True}})
            elif match.group(6):  # _italic_
                elements.append({"type": "text", "text": match.group(6), "style": {"italic": True}})
            elif match.group(8):  # ~strikethrough~
                elements.append({"type": "text", "text": match.group(8), "style": {"strike": True}})
            elif match.group(10):  # `code`
                elements.append({"type": "text", "text": match.group(10), "style": {"code": True}})
            elif match.group(12):  # <url|label> or <url>
                url = match.group(12)
                label = match.group(13) if match.group(13) else url
                elements.append({"type": "link", "url": url, "text": label})
            elif match.group(14):  # Raw URL
                url = match.group(14)
                label = url[:30] + ("..." if len(url) > 30 else "")
                elements.append({"type": "link", "url": url, "text": label})
            elif match.group(16):  # :emoji:
                elements.append({"type": "emoji", "name": match.group(16)})

            pos = match.end()

        if pos < len(line_content):
            remaining = line_content[pos:]
            if remaining:
                elements.append({"type": "text", "text": remaining})

        if line_idx < len(lines) - 1:
            elements.append({"type": "text", "text": "\n"})

    return elements if elements else [{"type": "text", "text": text}]


def add_reaction(channel: str, timestamp: str, emoji: str, config: dict[str, str]) -> bool:
    """Add a reaction to a message."""
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
        return response.json().get("ok", False)
    except Exception:
        return False


def load_messages() -> list[dict]:
    """Load messages from messages.json or use defaults."""
    messages_file = Path("messages.json")

    if messages_file.exists():
        try:
            with messages_file.open() as f:
                data = json.load(f)
                console.print(
                    f"[bold green]✓ Loaded {len(data)} messages from messages.json[/bold green]"
                )
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse messages.json: {e}")

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


def post_message(text: str, config: dict[str, str], thread_ts: str | None = None) -> dict | None:
    """Post a single message to Slack."""
    elements = parse_rich_text_from_string(text)
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
        result = response.json()
        return result if result.get("ok") else None
    except Exception as e:
        logger.error(f"Error posting message: {e}")
        return None


def main() -> None:
    """Main entry point."""
    config = load_config()
    messages = load_messages()

    total_posts = sum(1 + len(msg.get("replies", [])) for msg in messages)

    console.print("\n[bold blue]━━━ Posting Messages ━━━[/bold blue]")
    console.print(
        Panel.fit(
            f"[bold cyan]{len(messages)}[/bold cyan] messages\n"
            f"[bold cyan]{total_posts}[/bold cyan] total posts (including replies)",
            title="[bold]Slack Post Summary[/bold]",
            border_style="blue",
        )
    )

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

            result = post_message(text, config)

            if result:
                success += 1
                thread_ts = result["ts"]

                # Add reaction if emoji found in message
                emoji_match = re.search(r":([a-z_0-9]+):", text)
                if emoji_match:
                    time.sleep(0.5)
                    add_reaction(
                        config["SLACK_CHANNEL_ID"], thread_ts, emoji_match.group(1), config
                    )

                # Post replies
                for reply_text in msg_data.get("replies", []):
                    time.sleep(1)
                    reply_result = post_message(reply_text, config, thread_ts=thread_ts)
                    if reply_result:
                        success += 1
                    else:
                        failed += 1
            else:
                logger.error(f"Message {i} failed")
                failed += 1

            progress.advance(task)

            if i < len(messages):
                time.sleep(2)

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
