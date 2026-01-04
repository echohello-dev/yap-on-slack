# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for yap-on-slack.

## What is an ADR?

An ADR is a document that captures an important architectural decision made along with its context and consequences.

## When to write an ADR?

Write an ADR when:
- Introducing or replacing a major dependency
- Making decisions that affect the project's architecture
- Choosing between multiple viable approaches
- Making decisions that are hard to reverse

Don't write an ADR for:
- Small refactors or bug fixes
- Formatting or style changes
- Routine maintenance

## ADR Format

Use the template in [0000-template.md](0000-template.md).

## Status Definitions

- **Proposed**: Under discussion
- **Accepted**: Approved and implemented
- **Deprecated**: No longer relevant but kept for history
- **Superseded**: Replaced by a newer ADR

## Index

<!-- Add ADRs below in chronological order -->

- [0001: Use Slack Session Tokens Instead of Bot API](0001-slack-session-tokens.md) - **Accepted** (2026-01-02)
- [0002: Multi-User YAML Configuration](0002-multi-user-yaml-configuration.md) - **Accepted** (2026-01-02)
- [0003: Use Form-Urlencoded Instead of Multipart for Slack API](0003-slack-api-form-urlencoded.md) - **Accepted** (2026-01-02)
- [0004: Unified config.yaml Configuration System](0004-unified-config-yaml.md) - **Accepted** (2026-01-04)
- [0005: Channel Scanning for AI System Prompt Generation](0005-channel-scanning-ai-prompts.md) - **Accepted** (2026-01-04)
- [0006: Use XDG ~/.config Standard Instead of platformdirs](0006-xdg-config-over-platformdirs.md) - **Accepted** (2026-01-05)
