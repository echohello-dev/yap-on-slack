# Contributing to yap-on-slack

Thank you for considering contributing to yap-on-slack! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions professional

## Getting Started

### Prerequisites

- Python 3.13+
- [mise](https://mise.jdx.dev/) for task running
- [uv](https://github.com/astral-sh/uv) for dependency management (installed via mise)
- Git for version control

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/yap-on-slack.git
cd yap-on-slack

# Add upstream remote
git remote add upstream https://github.com/echohello-dev/yap-on-slack.git
```

## Development Setup

### 1. Install Dependencies

```bash
# Install all dependencies including dev tools
mise run install

# This installs: httpx, pydantic, python-dotenv, rich, tenacity
# Dev tools: pytest, ruff, mypy, pre-commit
```

### 2. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Test hooks manually
uv run pre-commit run --all-files
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your test workspace credentials
nano .env

# See docs/usage.md for how to get credentials
```

### 4. Verify Setup

```bash
# Run all checks
mise run check  # Runs lint, typecheck, and tests

# Or individually:
mise run lint       # Run ruff linter
mise run typecheck  # Run mypy type checking
mise run test       # Run pytest
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-cli-arguments` - New features
- `fix/rate-limiting-issue` - Bug fixes
- `docs/update-usage-guide` - Documentation
- `refactor/improve-validation` - Code refactoring
- `test/add-integration-tests` - Test additions

```bash
# Create a new branch
git checkout -b feature/your-feature-name
```

### Development Workflow

1. **Make your changes** in small, logical commits
2. **Run checks** frequently during development
3. **Test thoroughly** before pushing
4. **Update docs** if changing functionality

```bash
# After making changes
mise run format      # Auto-format code
mise run check       # Run all checks
mise run run -- --dry-run  # Test the tool
```

## Testing

### Running Tests

```bash
# Run all tests
mise run test

# Run specific test file
uv run pytest tests/test_formatting.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=yap_on_slack --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use pytest fixtures for reusable setup
- Test edge cases and error conditions

Example test:

```python
def test_message_validation():
    """Test that message validation works correctly."""
    valid_msg = Message(text="Test message", replies=["Reply 1"])
    assert valid_msg.text == "Test message"
    assert len(valid_msg.replies) == 1
    
    with pytest.raises(ValidationError):
        Message(text="", replies=["Reply"])  # Empty text should fail
```

## Code Style

### Python Style Guide

- **Formatter**: ruff format (runs automatically via pre-commit)
- **Linter**: ruff check with E, F, I, N, W, UP rules
- **Type Checker**: mypy in strict mode
- **Line Length**: 100 characters max
- **Python Version**: 3.13+ features allowed

### Type Annotations

All functions must have type annotations:

```python
def post_message(
    text: str, 
    config: dict[str, str], 
    thread_ts: str | None = None
) -> dict | None:
    """Post a single message to Slack."""
    ...
```

### Documentation

- Add docstrings to all public functions/classes
- Use clear, descriptive variable names
- Comment complex logic
- Update docs when changing functionality

### Formatting Examples

```python
# Good
def load_config() -> dict[str, str]:
    """Load configuration from .env file."""
    config = dotenv_values(".env")
    return config

# Bad
def load_config():  # Missing return type
    config=dotenv_values(".env")  # Missing spaces
    return config  # No docstring
```

## Commit Messages

### Format

```
type(scope): short description

Longer explanation if needed.

Fixes #123
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting (no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (deps, build, etc.)

### Examples

```bash
# Good commits
git commit -m "feat(cli): add --dry-run flag for validation without posting"
git commit -m "fix(auth): handle expired session tokens gracefully"
git commit -m "docs(usage): add troubleshooting section for common errors"
git commit -m "test(validation): add tests for empty message handling"

# Bad commits
git commit -m "fix stuff"
git commit -m "update"
git commit -m "WIP"
```

## Pull Request Process

### Before Submitting

1. **Sync with upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**
   ```bash
   mise run check
   ```

3. **Test thoroughly**
   ```bash
   mise run test
   mise run run -- --dry-run
   ```

4. **Update documentation**
   - Update README.md if adding features
   - Update docs/usage.md for usage changes
   - Add/update ADRs for architecture decisions

### Submitting PR

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub

3. **Fill out PR template** with:
   - Clear description of changes
   - Motivation and context
   - How to test the changes
   - Screenshots if UI-related
   - Related issues/PRs

4. **Wait for review**
   - Address feedback promptly
   - Keep discussions focused
   - Be open to suggestions

### PR Title Format

```
feat(scope): add feature X
fix(scope): resolve issue Y
docs: update usage guide
```

### After PR is Merged

```bash
# Update your local main
git checkout main
git pull upstream main

# Delete your feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Code Review Guidelines

### For Authors

- Keep PRs focused and reasonably sized
- Respond to feedback constructively
- Explain reasoning for decisions
- Update based on feedback

### For Reviewers

- Be constructive and respectful
- Focus on code, not the person
- Suggest improvements with examples
- Approve when ready, even if minor nits remain

## Development Tips

### Quick Checks

```bash
# Before committing
mise run format && mise run check

# Quick validation test
mise run run -- --limit 1 --dry-run --verbose
```

### Debugging

```bash
# Enable verbose logging
mise run run -- --verbose

# Use Python debugger
python -m pdb -m yap_on_slack.post_messages

# Check specific functionality
python -c "from yap_on_slack.post_messages import parse_rich_text_from_string; print(parse_rich_text_from_string('*bold*'))"
```

### Working with Messages

```bash
# Create test messages file
cat > test-messages.json << 'EOF'
[
  {
    "text": "Test message with *formatting*",
    "replies": ["Test reply"]
  }
]
EOF

# Test with custom file
mise run run -- --messages test-messages.json --dry-run
```

## Project Structure

```
yap-on-slack/
├── yap_on_slack/          # Main package
│   ├── __init__.py
│   └── post_messages.py   # Core functionality
├── tests/                 # Test suite
│   ├── test_formatting.py
│   ├── test_slack_api.py
│   └── ...
├── docs/                  # Documentation
│   ├── usage.md          # Usage guide
│   └── adrs/             # Architecture decisions
├── SECURITY.md           # Security documentation
├── .pre-commit-config.yaml
├── pyproject.toml        # Python project config
├── mise.toml             # Task definitions
└── README.md
```

## Need Help?

- **Documentation**: Check [docs/usage.md](docs/usage.md)
- **Security**: Read [SECURITY.md](SECURITY.md)
- **ADRs**: Review [docs/adrs/](docs/adrs/) for context
- **Issues**: Open an issue for questions or bugs

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for contributing! 🎉
