#!/usr/bin/env python3
"""Yap on Slack - CLI entry point for posting realistic Slack messages."""

import argparse
import sys
from pathlib import Path

from platformdirs import user_config_dir
from rich.console import Console

from yap_on_slack import __version__

console = Console()


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize configuration file for yap-on-slack."""
    # Determine target directory
    if args.local:
        config_dir = Path.cwd()
        config_file = config_dir / "config.yaml"
    else:
        config_dir = Path(user_config_dir("yap-on-slack", ensure_exists=False))
        config_file = config_dir / "config.yaml"

    # Create directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    # Check if file already exists
    if config_file.exists() and not args.force:
        console.print(f"\n[bold yellow]⚠ Config file already exists:[/bold yellow] {config_file}")
        console.print("  Use [bold]--force[/bold] to overwrite")
        return 1

    # Read template from config.yaml.example
    template_path = Path(__file__).parent.parent / "config.yaml.example"
    if template_path.exists():
        template_content = template_path.read_text()
    else:
        # Fallback inline template if example file not found
        template_content = """\
# yaml-language-server: $schema=https://raw.githubusercontent.com/echohello-dev/yap-on-slack/main/schema/config.schema.json
# Yap on Slack Configuration

# Workspace settings (required)
workspace:
  org_url: https://your-workspace.slack.com
  channel_id: C0123456789
  team_id: T0123456789

# Default credentials (required)
credentials:
  xoxc_token: xoxc-your-token-here
  xoxd_token: xoxd-your-token-here
  cookies: ""

# User selection strategy
user_strategy: round_robin  # round_robin | random

# Additional users (optional)
# users:
#   - name: alice
#     xoxc_token: xoxc-alice-token
#     xoxd_token: xoxd-alice-token
#   - name: bob
#     xoxc_token: xoxc-bob-token
#     xoxd_token: xoxd-bob-token

# AI settings (optional)
ai:
  enabled: false
  model: openrouter/auto              # Auto-selects best model (recommended)
  # See top weekly models: https://openrouter.ai/models?order=top-weekly
  api_key: ""
  temperature: 0.7
  max_tokens: 4000
  # system_prompt: |                  # Optional: override default prompt
  #   Your custom prompt here
  # Default: https://github.com/echohello-dev/yap-on-slack/blob/main/yap_on_slack/post_messages.py#L49
  temperature: 0.7
  max_tokens: 4000
"""

    # Write config file
    config_file.write_text(template_content)

    # Print results
    console.print("\n[bold blue]━━━ Yap on Slack Init ━━━[/bold blue]\n")
    console.print(f"[bold green]✓ Created config file:[/bold green] {config_file}")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print(f"  1. Edit [bold]{config_file}[/bold]")
    console.print("  2. Set workspace settings (org_url, channel_id, team_id)")
    console.print("  3. Set credentials (xoxc_token, xoxd_token)")
    console.print("     - Extract from browser dev tools while logged into Slack")
    console.print("  4. (Optional) Add more users for multi-user posting")
    console.print("  5. (Optional) Configure AI generation settings")
    console.print("  6. Run: [bold cyan]yos run[/bold cyan]")
    console.print()

    return 0
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

    if args.config:
        new_argv.extend(["--config", str(args.config)])
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
        help="Initialize config.yaml file",
        description="Create config.yaml with default settings",
    )
    init_parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing file")
    init_parser.add_argument(
        "--local",
        "-l",
        action="store_true",
        help="Create config.yaml in current directory (default: ~/.config/yap-on-slack/)",
    )
    init_parser.set_defaults(func=cmd_init)

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Post messages to Slack",
        description="Post realistic support messages to Slack using session tokens",
    )
    run_parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml file (default: ./config.yaml or ~/.config/yap-on-slack/config.yaml)",
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
        help="Generate messages using OpenRouter (auto-selects best model, requires OPENROUTER_API_KEY)",
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
