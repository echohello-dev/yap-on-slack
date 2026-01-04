---
date: 2026-01-05
status: Accepted
---

# 0006: Use XDG ~/.config Standard Instead of platformdirs

## Context

The application needs to determine where to store configuration files. On macOS, Windows, and Linux, the standard locations differ:

- **Linux/Unix**: `~/.config/appname/` (XDG Base Directory specification)
- **macOS**: `~/Library/Application Support/appname/` (Apple convention)
- **Windows**: `%APPDATA%\appname\` (Windows convention)

The `platformdirs` library abstracts these differences and automatically returns platform-specific paths.

However, yap-on-slack made a deliberate choice to use `~/.config` uniformly across all platforms.

## Decision

We will use the explicit path `~/.config/yap-on-slack/` for configuration storage across all platforms (Linux, macOS, Windows), instead of using `platformdirs` to determine platform-specific standard directories.

This decision was made to:
1. Reduce external dependencies (remove `platformdirs` import)
2. Ensure identical behavior across platforms for consistency in testing and user experience
3. Follow the XDG Base Directory specification, which is increasingly adopted even on non-Unix systems
4. Simplify code by using standard library `Path.home()` instead of an additional abstraction layer

## Alternatives Considered

### Alternative 1: Continue Using platformdirs

Use the `platformdirs.user_config_dir()` function to automatically resolve platform-specific directories.

**Why not chosen**: 
- Adds a dependency for a simple use case
- Makes behavior platform-specific, which complicates testing and documentation
- XDG standard is gaining adoption; most developers expect `~/.config` regardless of OS
- User preference for consistency outweighed platform conventions

### Alternative 2: Use Different Paths Per Platform

Implement conditional logic to use XDG on Linux, `~/Library/Application Support` on macOS, and `%APPDATA%` on Windows.

**Why not chosen**:
- Adds complexity and conditional logic throughout the codebase
- Creates platform-specific behavior that's harder to document and support
- Goes against the project's principle of simplicity
- Still requires either platformdirs or manual path logic

### Alternative 3: Support Both XDG and Platform-Specific Paths

Allow users to configure where their config lives, with XDG as the default.

**Why not chosen**:
- Adds configuration option complexity with minimal user benefit
- Most users never need to customize config location
- Simple, predictable path (`~/.config/yap-on-slack/`) is easier to document

## Consequences

### Positive

- **Reduced dependencies**: Removed `platformdirs` dependency entirely
- **Simpler code**: Uses only standard library `Path.home()` and `Path.mkdir(parents=True)`
- **Consistent behavior**: Same config location across all platforms makes troubleshooting easier
- **XDG compliance**: Aligns with growing adoption of XDG standard across platforms
- **Easier documentation**: Single, universal path to document
- **Better testing**: No platform-specific mocking needed for config discovery tests

### Negative

- **Non-standard on macOS/Windows**: `.config` is not the convention on macOS (`~/Library/Application Support`) or Windows (`%APPDATA%`)
- **User expectation mismatch**: Power users familiar with platform conventions may expect standard locations
- **Not reversible without migration**: Users with configs in `~/.config/` would need to migrate if we ever change this decision
- **Potential friction for some users**: Requires educating users about non-standard location on their platform

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [ADR-0004: Unified config.yaml](0004-unified-config-yaml.md) - Related decision on config file format
- PR: Initial config location implementation
