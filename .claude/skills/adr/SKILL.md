---
name: adr-writing
description: Write and maintain ADRs under docs/adrs when architecture decisions are made
---

# ADR Writing Skill (docs/adrs)

Use this skill whenever a meaningful technical/architecture decision has been made (or is being proposed) and it should be recorded for future maintainers.

## Definition: "Architecture decision"

Write an ADR if the decision is likely to matter in 1–6 months to someone other than the author.

Examples that require an ADR:

- introducing or replacing a major dependency (e.g., HTTP client, terminal UI library)
- changing package/module boundaries or public API surface
- adopting a new pattern that should be repeated
- changing data models with compatibility/migration implications
- decisions that are hard to reverse or have non-obvious trade-offs

Examples that typically do NOT need an ADR:

- small refactors localized to one file
- renames, formatting, and mechanical cleanups
- fixes that don't change behavior or long-term direction

## Where ADRs live

All ADRs live in `docs/adrs/`.

- Index and conventions: `docs/adrs/README.md`
- Template: `docs/adrs/0000-template.md`

## Naming and numbering

Use a monotonic numeric prefix:

- `0001-short-decision-title.md`
- `0002-some-other-decision.md`

Rules:

- pick the next available number in `docs/adrs/`
- filenames are lowercase, words separated by hyphens
- never renumber existing ADRs

## Status model

Allowed statuses:

- Proposed
- Accepted
- Deprecated
- Superseded by [000X-...](000X-...)

Guidance:

- If writing before merging a change, use **Proposed**.
- When the change lands, update to **Accepted**.
- If the decision is replaced, mark the old ADR as **Superseded**; do not delete it.

## ADR content requirements

An ADR must include (in this order):

1. YAML frontmatter at the very top of the file (first line) with `date` and `status`
2. Title line: `# NNNN: <Decision Title>`
3. Context
4. Decision
5. Alternatives considered
6. Consequences
7. References (PR/issue/related docs)

Keep it short and concrete:

- Prefer specific "we will…" statements.
- Name the impacted modules/files at a high level (don't paste code).
- Record the trade-offs that caused debate.

## Workflow (what to do when you detect a decision)

When the user asks for a change that implies an architectural choice (or you notice one while implementing):

1. Search `docs/adrs/` for an existing ADR that already covers the decision.
2. If none exists, create a new ADR using `docs/adrs/0000-template.md`.
3. Add the ADR to `docs/adrs/README.md` index.
4. If implementation changes are part of the same work, ensure the ADR's decision matches what was actually implemented.

## Writing style constraints

- Avoid sensitive data and secrets.
- Don't include personal opinions or blame.
- Avoid vendor marketing language.
- Prefer "we chose X because…" over lengthy background.

## "Definition of done" checklist

Before finishing:

- [ ] ADR file created under `docs/adrs/` with next number
- [ ] Status set correctly (Proposed vs Accepted)
- [ ] At least 1 real alternative recorded
- [ ] Consequences include at least 1 downside
- [ ] `docs/adrs/README.md` index updated
- [ ] References include the PR/issue link if available

## Repository-specific notes

- yap-on-slack is a simple Python tool for posting Slack messages
- Prefer verifying behavior with `mise run test` when the ADR accompanies code changes
- Most decisions will be about dependencies (httpx, rich) or message formatting approaches
