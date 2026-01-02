#!/usr/bin/env python3
"""Yap on Slack - CLI entry point for posting realistic Slack messages."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from yap_on_slack import __version__

console = Console()

# Template content for .env file
ENV_TEMPLATE = """\
# Slack Session Tokens (required)
# Extract from browser dev tools while logged into Slack
SLACK_XOXC_TOKEN=xoxc-your-token-here
SLACK_XOXD_TOKEN=xoxd-your-token-here

# Optional: Default posting user name (used when a message has no "user" field)
SLACK_USER_NAME=default

# Slack Workspace Configuration (required)
SLACK_ORG_URL=https://your-workspace.slack.com
SLACK_CHANNEL_ID=C1234567890
SLACK_TEAM_ID=T1234567890

# Optional: Multi-user sessions
# If ./users.yaml (or ./users.yml) exists, it is loaded automatically.
# You can also explicitly point to a file:
# SLACK_USERS_FILE=users.yaml

# Optional: AI Message Generation
# Get API key from https://openrouter.ai
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: GitHub Context Integration
# Used to fetch real commits, PRs, and issues for more realistic messages
# Falls back to 'gh auth token' if not set
GITHUB_TOKEN=ghp_your-token-here
"""

# Template content for users.yaml file
USERS_YAML_TEMPLATE = """\
# Multi-user Slack sessions used for posting messages
# - strategy: round_robin | random
# - default_user: optional user name to prefer

strategy: round_robin
default_user: default

users:
  - name: alice
    SLACK_XOXC_TOKEN: xoxc-...
    SLACK_XOXD_TOKEN: xoxd-...

  - name: bob
    SLACK_XOXC_TOKEN: xoxc-...
    SLACK_XOXD_TOKEN: xoxd-...
"""

# Template content for messages.json file
MESSAGES_JSON_TEMPLATE = """\
[
  {
    "text": "Hey team, I'm getting a *403* on the new dashboard. Has anyone else seen this? :thinking_face:",
    "user": "alice",
    "replies": [
      {"text": "Did you check if your token has the right scope?", "user": "bob"},
      "Also check the URL path - easy typo to make"
    ]
  },
  {
    "text": "Quick question - what's our _data retention policy_ for logs?",
    "replies": [
      "90 days in hot storage, then 7 years in cold per policy"
    ]
  },
  {
    "text": "*Issue* in prod :bug:: Database timeout on user auth\\n\\`TypeError: Cannot read property 'userId' of undefined\\`\\nAnyone know what we deployed?",
    "replies": [
      "Did we change the auth middleware recently?",
      "Yeah, I see it now. JWT decode is failing. Let me push a fix"
    ]
  },
  {
    "text": ":rocket: *heads up* - deploying _auth service v2.1_ to staging in 30min",
    "replies": [
      "thanks for the heads up! when's prod?",
      "probably friday if no issues"
    ]
  },
  {
    "text": ":warning: *ATTENTION*: deprecating \\`/api/v1/users\\` endpoint _next month_. migrate to \\`/api/v2/users\\` asap",
    "replies": [
      "how long do we have?",
      "until feb 15. best to do it early"
    ]
  }
]
"""


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize configuration files for yap-on-slack."""
    cwd = Path.cwd()
    created_files: list[str] = []
    skipped_files: list[str] = []

    # Create .env file
    env_file = cwd / ".env"
    if env_file.exists() and not args.force:
        skipped_files.append(".env (already exists, use --force to overwrite)")
    else:
        env_file.write_text(ENV_TEMPLATE)
        created_files.append(".env")

    # Create users.yaml file
    users_file = cwd / "users.yaml"
    if users_file.exists() and not args.force:
        skipped_files.append("users.yaml (already exists, use --force to overwrite)")
    else:
        users_file.write_text(USERS_YAML_TEMPLATE)
        created_files.append("users.yaml")

    # Create messages.json file
    messages_file = cwd / "messages.json"
    if messages_file.exists() and not args.force:
        skipped_files.append("messages.json (already exists, use --force to overwrite)")
    else:
        messages_file.write_text(MESSAGES_JSON_TEMPLATE)
        created_files.append("messages.json")

    # Print results
    console.print("\n[bold blue]━━━ Yap on Slack Init ━━━[/bold blue]\n")

    if created_files:
        console.print("[bold green]✓ Created configuration files:[/bold green]")
        for f in created_files:
            console.print(f"  [green]• {f}[/green]")

    if skipped_files:
        console.print("\n[bold yellow]⚠ Skipped files:[/bold yellow]")
        for f in skipped_files:
            console.print(f"  [yellow]• {f}[/yellow]")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print("  1. Edit [bold].env[/bold] with your Slack credentials")
    console.print("     - Get SLACK_XOXC_TOKEN and SLACK_XOXD_TOKEN from browser dev tools")
    console.print("     - Set SLACK_ORG_URL, SLACK_CHANNEL_ID, and SLACK_TEAM_ID")
    console.print("  2. (Optional) Edit [bold]users.yaml[/bold] for multi-user posting")
    console.print("  3. (Optional) Edit [bold]messages.json[/bold] with custom messages")
    console.print("  4. Run: [bold cyan]yos run[/bold cyan] (or yaponslack run)")
    console.print()

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run the message posting."""
    # Import here to avoid circular imports and speed up --help
    from yap_on_slack.post_messages import main as post_messages_main

    # Build sys.argv for the existing parser
    new_argv = ["yap-on-slack"]

    if args.messages:
        new_argv.extend(["--messages", str(args.messages)])
    if args.users:
        new_argv.extend(["--users", str(args.users)])
    if args.user:
        new_argv.extend(["--user", args.user])
    if args.dry_run:
        new_argv.append("--dry-run")
    if args.limit:
        new_argv.extend(["--limit", str(args.limit)])
    if args.delay:
        new_argv.extend(["--delay", str(args.delay)])
    if args.reply_delay:
        new_argv.extend(["--reply-delay", str(args.reply_delay)])
    if args.reaction_delay:
        new_argv.extend(["--reaction-delay", str(args.reaction_delay)])
    if args.verbose:
        new_argv.append("--verbose")
    if args.use_ai:
        new_argv.append("--use-ai")
    if args.debug_auth:
        new_argv.append("--debug-auth")

    # Replace sys.argv and call main
    old_argv = sys.argv
    try:
        sys.argv = new_argv
        post_messages_main()
        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1
    finally:
        sys.argv = old_argv


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    console.print(f"yap-on-slack {__version__}")
    return 0


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="yap-on-slack",
        description="Simulate realistic messages in Slack channels for testing purposes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Initialize configuration files
  yos init

  # Run with default messages
  yos run

  # Run with custom messages and limit
  yos run --messages custom.json --limit 5

  # Generate messages with AI
  yos run --use-ai --limit 10

  # Dry run (validate without posting)
  yos run --dry-run

Commands can also be invoked as:
  yaponslack <command>
  yap-on-slack <command>
""",
    )
    parser.add_argument("--version", "-V", action="store_true", help="Show version and exit")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize configuration files (.env, users.yaml, messages.json)",
        description="Create configuration files needed to run yap-on-slack",
    )
    init_parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    init_parser.set_defaults(func=cmd_init)

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Post messages to Slack",
        description="Post realistic support messages to Slack using session tokens",
    )
    run_parser.add_argument(
        "--messages",
        type=Path,
        help="Path to custom messages JSON file (default: messages.json)",
    )
    run_parser.add_argument(
        "--users",
        type=Path,
        help="Path to users YAML config (overrides SLACK_USERS_FILE)",
    )
    run_parser.add_argument(
        "--user",
        type=str,
        help="Force a specific user name for all top-level messages",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and messages without posting to Slack",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of messages to post (default: all)",
    )
    run_parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between messages (default: 2.0)",
    )
    run_parser.add_argument(
        "--reply-delay",
        type=float,
        default=1.0,
        help="Delay in seconds between replies (default: 1.0)",
    )
    run_parser.add_argument(
        "--reaction-delay",
        type=float,
        default=0.5,
        help="Delay in seconds before adding reactions (default: 0.5)",
    )
    run_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    run_parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Generate messages using OpenRouter Gemini 3 Flash (requires OPENROUTER_API_KEY)",
    )
    run_parser.add_argument(
        "--debug-auth",
        action="store_true",
        help="Print safe (redacted) Slack request/response diagnostics on failures",
    )
    run_parser.set_defaults(func=cmd_run)

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
    )
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()

    # Handle --version flag at top level
    if args.version:
        cmd_version(args)
        sys.exit(0)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute the command
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
