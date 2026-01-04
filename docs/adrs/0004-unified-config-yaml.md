---
date: 2026-01-04
status: Accepted
---

# 0004: Unified config.yaml Configuration System

## Context

The project previously used multiple configuration files for different purposes:
- `.env` for credentials and workspace settings
- `users.yaml` for multi-user token configuration
- `messages.json` for message definitions

This fragmented approach created several issues:
- Users had to manage and synchronize multiple files
- No validation of configuration values
- Inconsistent file formats (env vars, YAML, JSON)
- Unclear which settings took precedence
- Difficult to provide sensible defaults

## Decision

We will consolidate all configuration into a single `config.yaml` file with the following characteristics:

1. **Single file**: All settings (workspace, credentials, users, messages, AI) live in one YAML file
2. **JSON Schema validation**: `schema/config.schema.json` provides IDE autocompletion and validation
3. **XDG-compliant paths**: Default location is `~/.config/yap-on-slack/config.yaml` using `platformdirs`
4. **Config discovery order**: `--config` flag → `./config.yaml` → `~/.config/yap-on-slack/config.yaml`
5. **Environment variable override**: Env vars still work and take precedence for CI/CD flexibility
6. **Init command**: `yos init` creates config in home dir, `yos init --local` for current directory

## Alternatives Considered

### Alternative 1: Keep separate files with a wrapper

Keep the existing .env, users.yaml, and messages.json files but add a central config loader that merges them. Rejected because it doesn't solve the core problem of users managing multiple files and formats.

### Alternative 2: TOML configuration

Use TOML instead of YAML for configuration. Rejected because YAML is already used for users.yaml, the team has YAML experience, and YAML handles nested structures (messages with replies) more readably than TOML.

### Alternative 3: JSON-only configuration

Use JSON for configuration since we already have JSON Schema. Rejected because JSON lacks comments, which are valuable for self-documenting configuration files.

## Consequences

### Positive

- Single source of truth for all configuration
- IDE autocompletion and validation via JSON Schema
- Clearer migration path with `yos init` command
- XDG-compliant config location is more discoverable
- Comments in YAML help users understand options

### Negative

- Breaking change requiring user migration
- Users must update existing setups (mitigated by migration guide in commit message)
- Added dependency on `platformdirs` for XDG paths
- YAML parsing is slightly slower than env file loading (negligible for this use case)

## References

- [Commit fd48d84](https://github.com/echohello-dev/yap-on-slack/commit/fd48d84) - Implementation commit
- [config.yaml.example](../../config.yaml.example) - Configuration template
- [schema/config.schema.json](../../schema/config.schema.json) - JSON Schema for validation
- [ADR 0002](0002-multi-user-yaml-configuration.md) - Previous multi-user configuration (partially superseded)
