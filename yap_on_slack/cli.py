#!/usr/bin/env python3
"""Yap on Slack - CLI entry point for posting realistic Slack messages."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from rich.prompt import Prompt
from rich.table import Table

from yap_on_slack import __version__

console = Console()


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize configuration file for yap-on-slack."""
    # Determine target directory and filename
    if args.local:
        config_dir = Path.cwd()
        config_file = config_dir / ".yos.yaml"
    else:
        config_dir = Path.home() / ".config" / "yap-on-slack"
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
  # Default: https://github.com/echohello-dev/yap-on-slack/blob/main/yap_on_slack/prompts/generate_messages.txt
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


def cmd_run(args: argparse.Namespace) -> int:
    """Run the message posting."""
    import os

    # Import here to avoid circular imports and speed up --help
    from yap_on_slack.post_messages import main as post_messages_main

    # Handle interactive channel selection
    if args.interactive or args.channel_id:
        from yap_on_slack.post_messages import (SlackAPIError,
                                                SlackNetworkError,
                                                SlackRateLimitError,
                                                list_channels,
                                                load_unified_config)

        # Load config to get credentials
        try:
            app_config, env = load_unified_config(args.config)
        except ValueError as e:
            console.print(f"[bold red]Configuration error:[/bold red] {e}")
            return 1

        if not app_config.users:
            console.print("[bold red]Error:[/bold red] No users configured")
            return 1

        user = app_config.users[0]
        config = {
            "SLACK_ORG_URL": app_config.workspace.SLACK_ORG_URL,
            "SLACK_CHANNEL_ID": app_config.workspace.SLACK_CHANNEL_ID,
            "SLACK_TEAM_ID": app_config.workspace.SLACK_TEAM_ID,
            "SLACK_XOXC_TOKEN": user.SLACK_XOXC_TOKEN,
            "SLACK_XOXD_TOKEN": user.SLACK_XOXD_TOKEN,
        }
        if user.SLACK_COOKIES:
            config["SLACK_COOKIES"] = user.SLACK_COOKIES

        if args.interactive:
            console.print("\n[bold cyan]Fetching available channels...[/bold cyan]")
            try:
                channels = list_channels(config)
            except (SlackAPIError, SlackNetworkError, SlackRateLimitError) as e:
                console.print(f"[bold red]Error fetching channels:[/bold red] {e}")
                return 1

            if not channels:
                console.print(
                    "[bold red]Error:[/bold red] No channels accessible with current credentials"
                )
                return 1

            # Display channel table
            table = Table(title="Available Channels", show_header=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Name", style="green")
            table.add_column("ID", style="dim")
            table.add_column("Members", justify="right", style="magenta")
            table.add_column("Type", style="yellow")

            for idx, ch in enumerate(channels, 1):
                ch_type = "\U0001f512 Private" if ch.get("is_private") else "\U0001f4e2 Public"
                table.add_row(
                    str(idx),
                    ch.get("name", ""),
                    ch.get("id", ""),
                    str(ch.get("num_members", 0)),
                    ch_type,
                )

            console.print(table)
            console.print()

            # Auto-select if only one channel
            if len(channels) == 1:
                selected = channels[0]
                confirm = Prompt.ask(
                    f"Only one channel available: #{selected['name']}. Use it?",
                    choices=["y", "n"],
                    default="y",
                )
                if confirm.lower() != "y":
                    console.print("[yellow]Aborted.[/yellow]")
                    return 0
                channel_id = selected["id"]
                channel_name = selected["name"]
            else:
                # Let user select
                max_attempts = 3
                channel_id = None
                channel_name = None
                for attempt in range(max_attempts):
                    selection = Prompt.ask(
                        "Enter channel number or name (partial match supported)",
                        default="1",
                    )

                    # Try to match by number first
                    try:
                        idx = int(selection) - 1
                        if 0 <= idx < len(channels):
                            selected = channels[idx]
                            channel_id = selected["id"]
                            channel_name = selected["name"]
                            break
                    except ValueError:
                        pass

                    # Try partial name match
                    selection_lower = selection.lower()
                    matches = [
                        ch for ch in channels if selection_lower in ch.get("name", "").lower()
                    ]

                    if len(matches) == 1:
                        selected = matches[0]
                        channel_id = selected["id"]
                        channel_name = selected["name"]
                        break
                    elif len(matches) > 1:
                        console.print(
                            f"[yellow]Multiple matches:[/yellow] {', '.join(m['name'] for m in matches[:5])}"
                        )
                        console.print("Please be more specific.")
                    else:
                        console.print(f"[red]No channel matching '{selection}'[/red]")

                    if attempt == max_attempts - 1:
                        console.print("[bold red]Max attempts reached. Aborting.[/bold red]")
                        return 1

                if not channel_id:
                    return 1

            console.print(
                f"\n[bold green]\u2713 Selected:[/bold green] #{channel_name} ({channel_id})\n"
            )
            # Set environment variable to override config
            os.environ["SLACK_CHANNEL_ID"] = channel_id

        elif args.channel_id:
            # Direct channel ID provided
            os.environ["SLACK_CHANNEL_ID"] = args.channel_id
            console.print(f"\n[bold green]\u2713 Using channel:[/bold green] {args.channel_id}\n")

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
    if args.model != "openrouter/auto":  # Only add if not default
        new_argv.extend(["--model", args.model])
    if args.use_github:
        new_argv.append("--use-github")
    if args.github_token:
        new_argv.extend(["--github-token", args.github_token])
    if args.github_limit != 5:  # Only add if not default
        new_argv.extend(["--github-limit", str(args.github_limit)])
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


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan a Slack channel and generate system prompts."""
    from yap_on_slack.post_messages import (SlackAPIError, SlackNetworkError,
                                            SlackRateLimitError,
                                            fetch_channel_messages,
                                            generate_system_prompts,
                                            get_channel_info, list_channels,
                                            load_unified_config)

    console.print("\n[bold blue]━━━ Yap on Slack: Channel Scanner ━━━[/bold blue]\n")

    # Validate mutually exclusive args
    if not args.channel_id and not args.interactive:
        console.print(
            "[bold red]Error:[/bold red] Must specify either --channel-id or --interactive"
        )
        return 1

    if args.channel_id and args.interactive:
        console.print("[bold red]Error:[/bold red] Cannot use both --channel-id and --interactive")
        return 1

    # Load configuration
    try:
        app_config, env = load_unified_config(args.config)
    except ValueError as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}")
        return 1

    # Apply scan config defaults (CLI args take precedence)
    # Only use config defaults when CLI arg wasn't explicitly provided
    if env.get("_SCAN_LIMIT") and args.limit == 200:  # 200 is the argparse default
        args.limit = int(env["_SCAN_LIMIT"])
    if env.get("_SCAN_THROTTLE") and args.throttle == 0.5:  # 0.5 is the argparse default
        args.throttle = float(env["_SCAN_THROTTLE"])
    if env.get("_SCAN_MODEL") and args.model == "openrouter/auto":  # default
        args.model = env["_SCAN_MODEL"]
    if env.get("_SCAN_OUTPUT_DIR") and args.output_dir is None:
        args.output_dir = env["_SCAN_OUTPUT_DIR"]
    if env.get("_SCAN_EXPORT_DATA") == "false" and not args.no_export_data:
        args.no_export_data = True

    # Build request config from first user
    if not app_config.users:
        console.print("[bold red]Error:[/bold red] No users configured")
        return 1

    user = app_config.users[0]
    config = {
        "SLACK_ORG_URL": app_config.workspace.SLACK_ORG_URL,
        "SLACK_CHANNEL_ID": app_config.workspace.SLACK_CHANNEL_ID,
        "SLACK_TEAM_ID": app_config.workspace.SLACK_TEAM_ID,
        "SLACK_XOXC_TOKEN": user.SLACK_XOXC_TOKEN,
        "SLACK_XOXD_TOKEN": user.SLACK_XOXD_TOKEN,
    }
    if user.SLACK_COOKIES:
        config["SLACK_COOKIES"] = user.SLACK_COOKIES

    channel_id = args.channel_id
    channel_name = "unknown"

    # Interactive channel selection
    if args.interactive:
        console.print("[bold cyan]Fetching available channels...[/bold cyan]")
        try:
            channels = list_channels(config)
        except (SlackAPIError, SlackNetworkError, SlackRateLimitError) as e:
            console.print(f"[bold red]Error fetching channels:[/bold red] {e}")
            return 1

        if not channels:
            console.print(
                "[bold red]Error:[/bold red] No channels accessible with current credentials"
            )
            return 1

        # Display channel table
        table = Table(title="Available Channels", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Name", style="green")
        table.add_column("ID", style="dim")
        table.add_column("Members", justify="right", style="magenta")
        table.add_column("Type", style="yellow")

        for idx, ch in enumerate(channels, 1):
            ch_type = "🔒 Private" if ch.get("is_private") else "📢 Public"
            table.add_row(
                str(idx),
                ch.get("name", ""),
                ch.get("id", ""),
                str(ch.get("num_members", 0)),
                ch_type,
            )

        console.print(table)
        console.print()

        # Auto-select if only one channel
        if len(channels) == 1:
            selected = channels[0]
            confirm = Prompt.ask(
                f"Only one channel available: #{selected['name']}. Use it?",
                choices=["y", "n"],
                default="y",
            )
            if confirm.lower() != "y":
                console.print("[yellow]Aborted.[/yellow]")
                return 0
            channel_id = selected["id"]
            channel_name = selected["name"]
        else:
            # Let user select
            max_attempts = 3
            for attempt in range(max_attempts):
                selection = Prompt.ask(
                    "Enter channel number or name (partial match supported)",
                    default="1",
                )

                # Try to match by number first
                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(channels):
                        selected = channels[idx]
                        channel_id = selected["id"]
                        channel_name = selected["name"]
                        break
                except ValueError:
                    pass

                # Try partial name match
                selection_lower = selection.lower()
                matches = [ch for ch in channels if selection_lower in ch.get("name", "").lower()]

                if len(matches) == 1:
                    selected = matches[0]
                    channel_id = selected["id"]
                    channel_name = selected["name"]
                    break
                elif len(matches) > 1:
                    console.print(
                        f"[yellow]Multiple matches:[/yellow] {', '.join(m['name'] for m in matches[:5])}"
                    )
                    console.print("Please be more specific.")
                else:
                    console.print(f"[red]No channel matching '{selection}'[/red]")

                if attempt == max_attempts - 1:
                    console.print("[bold red]Max attempts reached. Aborting.[/bold red]")
                    return 1

        console.print(f"\n[bold green]✓ Selected:[/bold green] #{channel_name} ({channel_id})")
    else:
        # Validate provided channel ID
        console.print(f"[bold cyan]Validating channel {channel_id}...[/bold cyan]")
        try:
            channel_info = get_channel_info(config, channel_id)
            if not channel_info:
                console.print(
                    f"[bold red]Error:[/bold red] Channel {channel_id} not found or not accessible"
                )
                return 1
            channel_name = channel_info.get("name", "unknown")
            console.print(f"[bold green]✓ Found:[/bold green] #{channel_name}")
        except (SlackAPIError, SlackNetworkError) as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return 1

    # Fetch messages
    console.print("\n[bold blue]━━━ Fetching Messages ━━━[/bold blue]")
    console.print(f"  Channel: [cyan]#{channel_name}[/cyan]")
    console.print(f"  Limit: [cyan]{args.limit}[/cyan] messages")
    console.print(f"  Throttle: [cyan]{args.throttle}s[/cyan] between requests")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Fetching messages...", total=args.limit)

            def update_progress(current: int, total: int, status: str) -> None:
                progress.update(task, completed=current, description=f"[green]{status}")

            channel_data = fetch_channel_messages(
                config,
                channel_id,
                limit=args.limit,
                throttle=args.throttle,
                progress_callback=update_progress,
            )
            channel_data["name"] = channel_name

    except SlackRateLimitError as e:
        console.print(f"\n[bold yellow]Rate limited:[/bold yellow] {e}")
        console.print("Try using [cyan]--throttle 2.0[/cyan] or wait before retrying")
        return 1
    except (SlackAPIError, SlackNetworkError) as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        return 1

    # Display summary
    console.print("\n[bold blue]━━━ Analysis Summary ━━━[/bold blue]")
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Messages fetched", str(channel_data["total_messages"]))
    summary_table.add_row("Replies included", str(channel_data["total_replies"]))
    summary_table.add_row("Reactions counted", str(channel_data["total_reactions"]))

    top_reactions = channel_data.get("top_reactions", [])[:5]
    if top_reactions:
        reaction_str = " ".join([f":{name}: ({count})" for name, count in top_reactions])
        summary_table.add_row("Top reactions", reaction_str)

    console.print(summary_table)

    # Check for insufficient data
    if channel_data["total_messages"] < 10:
        console.print(
            f"\n[bold yellow]Warning:[/bold yellow] Only {channel_data['total_messages']} messages found. "
            "Prompts may be low quality."
        )

    if channel_data["total_replies"] == 0:
        console.print("[dim]Note: No threaded conversations found.[/dim]")

    if channel_data["total_reactions"] == 0:
        console.print("[dim]Note: No reactions found.[/dim]")

    # Resolve output directory (default to ~/.config/yap-on-slack/scan/)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path.home() / ".config" / "yap-on-slack" / "scan"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export data by default (unless --no-export-data)
    export_file: Path | None = None
    if not args.no_export_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = output_dir / f"channel_export_{channel_name}_{timestamp}.txt"

        lines: list[str] = []
        lines.append(f"# Channel Export: #{channel_name}")
        lines.append(f"# Channel ID: {channel_id}")
        lines.append(f"# Exported: {datetime.now().isoformat()}")
        lines.append(f"# Total Messages: {channel_data['total_messages']}")
        lines.append(f"# Total Replies: {channel_data['total_replies']}")
        lines.append(f"# Total Reactions: {channel_data['total_reactions']}")
        lines.append("")

        # Top reactions summary
        top_reactions = channel_data.get("top_reactions", [])
        if top_reactions:
            lines.append("## Top Reactions")
            for name, count in top_reactions:
                lines.append(f"  :{name}: - {count}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")

        # Export each message with replies and reactions
        for idx, msg in enumerate(channel_data.get("messages", []), 1):
            text = msg.get("text", "").strip()
            user = msg.get("user", "unknown")
            ts = msg.get("ts", "")
            reactions = msg.get("reactions", [])
            replies = msg.get("replies", [])

            lines.append(f"[Message {idx}] @{user} ({ts})")
            lines.append(text if text else "(empty message)")

            # Show reactions on main message
            if reactions:
                reaction_str = " ".join([f":{r['name']}:({r['count']})" for r in reactions])
                lines.append(f"  Reactions: {reaction_str}")

            # Show replies
            if replies:
                lines.append(f"  └─ {len(replies)} repl{'y' if len(replies) == 1 else 'ies'}:")
                for reply_idx, reply in enumerate(replies, 1):
                    reply_text = reply.get("text", "").strip()
                    reply_user = reply.get("user", "unknown")
                    reply_ts = reply.get("ts", "")
                    prefix = "└" if reply_idx == len(replies) else "├"
                    lines.append(f"     {prefix}─ @{reply_user} ({reply_ts})")
                    # Indent reply text
                    for line in (reply_text or "(empty)").split("\n"):
                        lines.append(f"        {line}")

            lines.append("-" * 40)
            lines.append("")

        export_file.write_text("\n".join(lines))
        console.print("\n[bold green]✓ Exported channel data[/bold green]")
        console.print(
            f"  [dim]{len(channel_data.get('messages', []))} messages, {channel_data['total_replies']} replies, {channel_data['total_reactions']} reactions[/dim]"
        )
        console.print(
            f"\n  [link=file://{export_file.absolute()}][cyan]{export_file.absolute()}[/cyan][/link]"
        )

    # Dry run mode - stop here
    if args.dry_run:
        console.print("\n[bold green]✓ Dry run complete[/bold green]")
        console.print(f"Would generate prompts with model: [cyan]{args.model}[/cyan]")
        if export_file:
            console.print(f"\n[bold]Channel data saved to:[/bold] {export_file.absolute()}")
        return 0

    # Generate prompts
    console.print("\n[bold blue]━━━ Generating System Prompts ━━━[/bold blue]")
    console.print(f"  Model: [cyan]{args.model}[/cyan]")

    openrouter_key = env.get("OPENROUTER_API_KEY")
    prompts = generate_system_prompts(channel_data, model=args.model, api_key=openrouter_key)

    if not prompts:
        console.print("[bold red]Error:[/bold red] Failed to generate prompts")
        return 1

    # Save prompts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_files: list[Path] = []

    for i, prompt in enumerate(prompts, 1):
        filename = f"system_prompt_draft_{timestamp}_{i}.md"
        filepath = output_dir / filename

        content = f"""# System Prompt Draft {i}

Generated: {datetime.now().isoformat()}
Model: {args.model}
Channel: #{channel_name} ({channel_id})
Messages analyzed: {channel_data["total_messages"]}

---

{prompt}
"""
        filepath.write_text(content)
        output_files.append(filepath)

    # Display results
    console.print(f"\n[bold green]✓ Generated {len(prompts)} system prompt drafts[/bold green]\n")

    result_table = Table(title="System Prompt Drafts", show_header=True)
    result_table.add_column("Draft", style="cyan", width=8)
    result_table.add_column("File", style="yellow")
    result_table.add_column("Size", justify="right", style="magenta")

    for i, filepath in enumerate(output_files, 1):
        size = f"{filepath.stat().st_size:,} bytes"
        abs_path = str(filepath.absolute())
        result_table.add_row(f"#{i}", f"[link=file://{abs_path}]{abs_path}[/link]", size)

    console.print(result_table)

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

  # Scan a channel interactively and generate prompts
  yos scan --interactive

  # Scan a specific channel
  yos scan --channel-id C1234567890 --limit 500

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
        help="Create .yos.yaml in current directory (default: ~/.config/yap-on-slack/config.yaml)",
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
        help="Path to config file (default: ./.yos.yaml, ./config.yaml, or ~/.config/yap-on-slack/config.yaml)",
    )
    run_parser.add_argument(
        "--channel-id",
        type=str,
        help="Override channel ID from config (e.g., C1234567890)",
    )
    run_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive channel selector",
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
        "--model",
        type=str,
        default="openrouter/auto",
        help="OpenRouter model for AI generation (default: openrouter/auto, see https://openrouter.ai/models)",
    )
    run_parser.add_argument(
        "--use-github",
        action="store_true",
        help="Include GitHub context (commits, PRs, issues) in AI message generation (requires gh CLI or GITHUB_TOKEN)",
    )
    run_parser.add_argument(
        "--github-token",
        type=str,
        default=None,
        help="GitHub API token (overrides GITHUB_TOKEN env var and gh CLI)",
    )
    run_parser.add_argument(
        "--github-limit",
        type=int,
        default=5,
        help="Maximum repositories to fetch GitHub context from (default: 5)",
    )
    run_parser.add_argument(
        "--debug-auth",
        action="store_true",
        help="Print safe (redacted) Slack request/response diagnostics on failures",
    )
    run_parser.set_defaults(func=cmd_run)

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a Slack channel and generate system prompts",
        description="Analyze channel writing style and generate system prompt variations using AI",
    )
    channel_group = scan_parser.add_mutually_exclusive_group(required=True)
    channel_group.add_argument(
        "--channel-id",
        type=str,
        help="Direct channel ID to scan (e.g., C1234567890)",
    )
    channel_group.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive channel selector",
    )
    scan_parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml file",
    )
    scan_parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum messages to fetch (default: 200)",
    )
    scan_parser.add_argument(
        "--throttle",
        type=float,
        default=0.5,
        help="Delay between API call batches in seconds (default: 0.5)",
    )
    scan_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for generated prompts (default: ~/.config/yap-on-slack/scan/)",
    )
    scan_parser.add_argument(
        "--model",
        type=str,
        default="openrouter/auto",
        help="OpenRouter model for prompt generation (default: openrouter/auto)",
    )
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and analyze without generating prompts",
    )
    scan_parser.add_argument(
        "--no-export-data",
        action="store_true",
        help="Skip exporting messages, threads, replies, and reactions to a text file",
    )
    scan_parser.set_defaults(func=cmd_scan)

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
