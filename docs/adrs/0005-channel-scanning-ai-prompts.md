---
date: 2026-01-04
status: Accepted
---

# 0005: Channel Scanning for AI System Prompt Generation

## Context

When using AI to generate realistic Slack messages, the quality depends heavily on the system prompt. Users needed to manually craft prompts that match their channel's communication style, which was time-consuming and often resulted in generic outputs that didn't feel authentic to the channel's culture.

We needed a way to analyze existing channel conversations and automatically generate tailored system prompts that capture:
- Communication patterns and formality level
- Common emoji usage and reactions
- Thread reply conventions
- Topic focus and terminology

## Decision

We will add a `yos scan` command that:

1. **Fetches channel history**: Uses Slack's `conversations.history` API to retrieve recent messages (configurable limit, default 200)
2. **Includes thread context**: Fetches replies for threaded conversations to understand discussion patterns
3. **Analyzes with AI**: Sends the message data to OpenRouter API for analysis
4. **Generates system prompts**: Produces a tailored prompt based on the channel's actual communication style
5. **Supports interactive mode**: `yos scan -i` allows channel selection, `yos scan --channel-id C123` for direct specification
6. **Exports data**: Optionally saves raw messages to a text file for manual review

Configuration is added under a new `scan:` section in config.yaml with settings for:
- `limit`: Maximum messages to fetch (10-5000)
- `throttle`: Delay between API batches to avoid rate limiting
- `output_dir`: Where to save generated prompts
- `model`: Which OpenRouter model to use for analysis
- `export_data`: Whether to save raw message exports

## Alternatives Considered

### Alternative 1: Manual prompt templates only

Provide a library of pre-written prompt templates for different channel types (engineering, support, social). Rejected because channels have unique cultures that templates can't capture, and this doesn't leverage the actual channel data available.

### Alternative 2: Client-side analysis without AI

Analyze messages locally using heuristics (emoji frequency, message length, reply patterns) and generate prompts from rules. Rejected because capturing communication "feel" and style nuances requires language understanding that simple heuristics can't provide.

### Alternative 3: Continuous learning from posted messages

Track which AI-generated messages get reactions/replies and iteratively improve prompts. Rejected as overly complex for the current scope and raises concerns about feedback loops affecting real channels.

## Consequences

### Positive

- Generated prompts match actual channel culture and style
- Reduces manual effort in crafting effective prompts
- Exported data helps users understand their channel patterns
- Configurable limits prevent excessive API usage
- Throttling prevents Slack rate limit issues

### Negative

- Requires OpenRouter API key and incurs API costs
- Fetching large channel histories can be slow
- Generated prompts may need manual refinement
- Privacy consideration: channel data is sent to external AI API
- Added complexity to the CLI with new command and config section

## References

- [Commit 900f3b7](https://github.com/echohello-dev/yap-on-slack/commit/900f3b7) - Implementation commit
- [OpenRouter API](https://openrouter.ai/) - AI provider used for analysis
- [Slack conversations.history API](https://api.slack.com/methods/conversations.history) - Message fetching endpoint
