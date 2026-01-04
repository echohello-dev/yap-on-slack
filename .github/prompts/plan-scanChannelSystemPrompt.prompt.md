# Plan: Channel Scanning and System Prompt Generation Feature

## Overview

Add `yos scan` command to analyze Slack channel writing style and generate system prompt variations using OpenRouter. The feature extracts messages, replies, and reactions to create context-aware prompts optimized for the yap-on-slack tool's AI generation capabilities.

## Implementation Steps

### 1. CLI Command Structure (`cli.py`)

**Add `scan` subcommand with arguments:**
```
yos scan [OPTIONS]

Required (mutually exclusive):
  --channel-id TEXT       Direct channel ID (e.g., C1234567890)
  --interactive          Interactive channel selector

Optional:
  --limit INTEGER         Max messages to fetch [default: 200]
  --throttle FLOAT       Delay between API calls in seconds [default: 1.0]
  --output-dir PATH      Directory for drafts [default: ./prompts]
  --model TEXT           OpenRouter model [default: anthropic/claude-3.5-sonnet]
  --dry-run             Fetch and analyze without generating prompts
```

**Implementation details:**
- Create `cmd_scan()` handler following existing pattern
- Validate that exactly one of `--channel-id` or `--interactive` is provided
- Use `config_manager.load_config()` to get Slack credentials
- Display rich progress bars during fetch/analysis/generation phases
- Return exit code 0 on success, 1 on failure

### 2. Slack Conversations API Integration (`post_messages.py`)

**Add authenticated API wrapper functions:**

**`list_channels(config: dict, types: str = "public_channel,private_channel") -> list[dict]`**
- Endpoint: `POST {SLACK_ORG_URL}/api/conversations.list`
- Parameters: `token`, `types`, `exclude_archived=true`, `limit=200`
- Returns: List of `{"id": "C123", "name": "general", "num_members": 42}`
- Use existing XOXC/XOXD token pattern with cookies
- Apply `@retry` decorator for network resilience
- Handle pagination via `cursor` if >200 channels exist

**`fetch_channel_messages(config: dict, channel_id: str, limit: int, throttle: float) -> dict`**
- Endpoint: `POST {SLACK_ORG_URL}/api/conversations.history`
- Parameters: `token`, `channel`, `limit=100` per page
- Returns structured data:
  ```python
  {
      "messages": [
          {
              "text": "...",
              "user": "U123",
              "ts": "1234567890.123456",
              "reply_count": 3,
              "reactions": [{"name": "thumbsup", "count": 5}]
          }
      ],
      "total_messages": 200,
      "total_replies": 45,
      "total_reactions": 78
  }
  ```
- For each message with `reply_count > 0`, call `conversations.replies` to fetch thread
- Sleep `throttle` seconds between each API call (history + each replies call)
- Apply `@retry` decorator with exponential backoff
- Catch `SlackRateLimitError` and display helpful message with `Retry-After` value
- Stop pagination when `limit` total messages reached

**Data aggregation logic:**
- Deduplicate messages (parent message appears in both history and replies)
- Extract text content, strip Slack formatting (use existing `parse_markdown_like` in reverse)
- Count reaction types and frequencies across all messages
- Calculate stats: avg message length, reply ratio, most used emoji, active users

### 3. Interactive Channel Selector

**Build terminal UI with Rich:**
- Fetch channels via `list_channels()`
- Display table with columns: `Name`, `ID`, `Members`, `Type` (public/private)
- Use `rich.table.Table` with highlighting
- Prompt user with `rich.prompt.Prompt.ask()` to enter channel name or number
- Support partial name matching (e.g., "gen" matches "general")
- Handle invalid input with retry loop (max 3 attempts)
- Display selected channel info before proceeding

**Fallback behavior:**
- If only 1 channel accessible, auto-select with confirmation prompt
- If 0 channels accessible, error message about permissions
- If `--channel-id` provided, validate channel exists and is accessible

### 4. OpenRouter Prompt Generation

**Create `generate_system_prompts(channel_data: dict, model: str) -> list[str]`:**

**API call details:**
- Endpoint: `POST https://openrouter.ai/api/v1/chat/completions`
- Headers: `Authorization: Bearer {OPENROUTER_API_KEY}`, `Content-Type: application/json`
- Model: `anthropic/claude-3.5-sonnet` (configurable via `--model` arg)
- Use existing OpenRouter pattern from `generate_ai_messages()` in `post_messages.py`

**Prompt engineering:**
```python
system_message = """You are an expert at analyzing communication styles and creating system prompts.
Analyze the provided Slack channel data and generate 3 distinct system prompt variations
that capture the writing style, tone, and patterns used in this channel.

Each prompt should:
- Be optimized for LLM message generation (for the yap-on-slack tool)
- Capture unique aspects: formality level, emoji usage, humor style, message length
- Include specific examples from the data
- Be 500-1000 words
- Focus on different aspects (e.g., Prompt 1: tone/style, Prompt 2: structure/format, Prompt 3: content themes)

Output as JSON array with 3 strings."""

user_message = f"""Channel: #{channel_data['name']}
Total messages: {channel_data['total_messages']}
Total replies: {channel_data['total_replies']}
Common reactions: {channel_data['top_reactions']}

Sample messages:
{format_sample_messages(channel_data['messages'][:50])}

Generate 3 system prompt variations."""
```

**Response parsing:**
- Parse JSON array from response
- Validate 3 prompts returned
- Fallback: If JSON parsing fails, split response by markdown headers or numbered sections
- Add metadata header to each prompt: generation timestamp, model used, channel analyzed

**Environment variable:**
- Check `OPENROUTER_API_KEY` from existing config loading
- If missing, display error with link to https://openrouter.ai/keys
- Handle API errors: rate limits, invalid model, network failures

### 5. Output and User Experience

**Save drafts with rich metadata:**
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)

for i, prompt in enumerate(prompts, 1):
    filename = f"system_prompt_draft_{timestamp}_{i}.md"
    filepath = output_dir / filename
    
    content = f"""# System Prompt Draft {i}
Generated: {datetime.now().isoformat()}
Model: {model}
Channel: #{channel_data['name']} ({channel_id})
Messages analyzed: {channel_data['total_messages']}

---

{prompt}
"""
    filepath.write_text(content)
```

**Terminal output with Rich:**
```python
console.print("\n[bold green]✓ Generated 3 system prompt drafts[/bold green]\n")

table = Table(title="System Prompt Drafts", show_header=True)
table.add_column("Draft", style="cyan", width=8)
table.add_column("File", style="yellow")
table.add_column("Size", justify="right", style="magenta")
table.add_column("Quick Link", style="blue")

for i, filepath in enumerate(output_files, 1):
    size = f"{filepath.stat().st_size:,} chars"
    file_url = f"file://{filepath.absolute()}"
    # Clickable link in terminal:
    table.add_row(f"#{i}", filepath.name, size, f"[link={file_url}]Open[/link]")

console.print(table)
console.print(f"\n[dim]Saved to: {output_dir.absolute()}[/dim]")
```

**Validation before generation:**
- Check if output directory is writable
- Warn if files will be overwritten (timestamp collision unlikely but possible)
- Display summary stats before generation:
  - Messages fetched: X
  - Replies included: Y
  - Reactions counted: Z
  - Estimated API cost: ~$0.XX (based on input tokens)

## Design Decisions

### Token Authentication
**Decision:** Support session tokens (XOXC/XOXD) only initially, add bot token support later if needed.

**Rationale:**
- Existing codebase uses session tokens exclusively
- Bot token support requires different auth pattern (`Authorization: Bearer` header)
- Session tokens have higher rate limits for read operations
- Can be added in future without breaking changes

### Model Selection
**Decision:** Default to `anthropic/claude-3.5-sonnet`, allow override via `--model` arg and `OPENROUTER_MODEL` env var.

**Rationale:**
- Claude 3.5 Sonnet excels at prompt engineering and style analysis
- More expensive than Gemini Flash but produces higher quality system prompts
- Existing code uses Gemini for message generation (cost-sensitive, high volume)
- This is one-time generation, quality > cost
- User can override for experimentation

### Rate Limit Handling
**Decision:** Conservative throttle (1.0s default), fail gracefully on rate limits with clear error message.

**Rationale:**
- Slack Tier 3 allows ~50/min, but other factors affect limits (per-user, per-workspace)
- Auto-adjusting throttle adds complexity and unpredictable runtime
- Conservative default (1.0s = 60/min) keeps headroom
- User can increase `--throttle` if hitting limits
- Display clear error: "Rate limited. Try --throttle 2.0 or wait X seconds"

### Data Privacy
**Decision:** Store raw messages in memory only, never write to disk. Save only generated prompts.

**Rationale:**
- Channel messages may contain sensitive information
- System prompts are generalized/anonymized by LLM
- If user wants raw data, add `--export-data` flag later
- Comply with common data retention policies

## Error Handling

**Network failures:**
- Retry up to 3 times with exponential backoff (existing `@retry` pattern)
- Display progress: "Retrying... (attempt 2/3)"

**Rate limit errors:**
- Catch `SlackRateLimitError`, display `Retry-After` header value
- Suggest: "Rate limited. Wait 60s or use --throttle 2.0"
- Do not auto-retry (could extend wait time significantly)

**Invalid channel:**
- Check channel exists via `conversations.info` before fetching history
- Error: "Channel C123 not found or not accessible with current credentials"

**OpenRouter failures:**
- Invalid API key: "OPENROUTER_API_KEY invalid. Get one at https://openrouter.ai/keys"
- Model not available: "Model X not found. Try: anthropic/claude-3.5-sonnet"
- Rate limit: "OpenRouter rate limit. Try again in 60s"
- Response parsing error: "Failed to parse prompts. Raw response saved to prompts/error_{timestamp}.txt"

**Insufficient data:**
- If channel has <10 messages: "Warning: Only X messages found. Prompts may be low quality."
- If channel has no replies: "Note: No threaded conversations found."
- If channel has no reactions: "Note: No reactions found."

## Testing Considerations

**Unit tests:**
- Mock `httpx.post()` for Slack API calls
- Test pagination logic with multiple `cursor` values
- Test rate limit error handling
- Test OpenRouter response parsing (valid JSON, malformed JSON, empty response)
- Test file writing with read-only directory

**Integration tests:**
- Use real Slack workspace test channel (if credentials available)
- Mock OpenRouter with pre-generated prompts
- Validate output file format and content

**Manual testing scenarios:**
- Empty channel (0 messages)
- Channel with 1000+ messages (pagination)
- Private channel (permission check)
- Invalid channel ID
- Missing OpenRouter API key
- Network timeout during fetch

## Future Enhancements

1. **Export formats:** `--format json|yaml|txt` to save analysis data
2. **Comparison mode:** Compare prompts from multiple channels
3. **Interactive editing:** Launch $EDITOR to refine prompt before final save
4. **Bot token support:** Add `--bot-token` flag for xoxb- tokens
5. **Time-based filtering:** `--since 2025-01-01` to analyze recent messages only
6. **User-based filtering:** `--users alice,bob` to focus on specific authors
7. **Prompt testing:** `yos test-prompt` to generate sample messages with each draft
8. **Streaming mode:** Display partial analysis as messages are fetched
