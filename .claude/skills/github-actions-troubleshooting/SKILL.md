---
name: github-actions-troubleshooting
description: Troubleshoot and fix GitHub Actions workflow failures
---

# GitHub Actions Troubleshooting Skill

Use this skill when GitHub Actions workflows are failing and need to be debugged and fixed.

## When to use this skill

Apply this skill when:

- CI/CD workflow runs are failing after push or merge
- Docker builds or image publishes are failing in Actions
- Tests or linting fail only in CI (but work locally)
- Workflow logs show errors that need investigation

## Troubleshooting workflow

### 1. Check the workflow YAML file first

**Always start by examining the workflow configuration:**

```bash
# Find the workflow file
ls .github/workflows/

# Read the workflow to understand what it does
cat .github/workflows/<workflow-name>.yml
```

**Key things to check:**
- Which commands are being run in each step?
- What's the context path?
- What triggers the workflow (push, pull_request, etc.)?

### 2. Test commands locally first

**Before diving into CI logs, reproduce the issue locally:**

```bash
# Run the exact commands from the workflow
mise run install
mise run lint
mise run test
docker build -t test .

# Check for errors
echo $?  # Exit code (0 = success)
```

**Benefits:**
- Faster feedback loop (no push/wait cycle)
- Can inspect files and environment directly
- Can test fixes before committing

### 3. Get workflow run logs

**Use GitHub CLI:**

```bash
# List recent workflow runs
gh run list --workflow="<workflow-name>" --limit 5

# View the latest run
gh run view

# View only failed jobs (most useful)
gh run view --log-failed

# View specific run by ID
gh run view <run-id> --log-failed
```

### 4. Analyze the failure

**Common failure patterns:**

#### Docker build failures
```
ERROR: failed to build: failed to solve
```
- Check Dockerfile commands (COPY, RUN, etc.)
- Verify files exist in build context
- Check for missing dependencies or wrong paths

#### Module/file not found
```
Module not found: Can't resolve '@/lib/api'
ERROR: COPY requirements.txt .: not found
```
- Check if files are committed to git: `git ls-files <path>`
- Check .gitignore exclusions: `cat .gitignore | grep <pattern>`
- Force add if needed: `git add -f <path>`

#### Dependency conflicts
```
error: Unsupported compiler -- at least C++11 support is needed!
```
- Check Dockerfile system dependencies (gcc, g++, etc.)
- Verify Python version compatibility
- Check package versions in pyproject.toml

### 5. Fix iteratively

**Pattern: Fix → Commit → Push → Wait → Check**

```bash
# 1. Make a fix based on logs
edit <file>

# 2. Test locally if possible
mise run test
docker build -t test .

# 3. Commit with descriptive message
git add <file>
git commit -m "fix(ci): <specific issue fixed>"

# 4. Push to trigger workflow
git push

# 5. Wait for workflow to start
sleep 15
gh run list --workflow="Build" --limit 1

# 6. Wait for completion and check status
sleep 90  # Typical build time
gh run list --workflow="Build" --limit 1

# 7. If failed, get logs and repeat
gh run view --log-failed | grep -A 10 "ERROR:"
```

**Important: Use timeouts and sleep commands**
- Don't spam the API with rapid requests
- `sleep 15` after push (wait for workflow to trigger)
- `sleep 60-90` for builds to complete

### 6. Common fixes by error type

#### Fix: Missing file in build context
```bash
# Check if file is in git
git ls-files <path>

# If missing, check .gitignore
grep <pattern> .gitignore

# Force add and commit
git add -f <path>
git commit -m "fix: add <file> to git (was ignored)"
```

#### Fix: Wrong Dockerfile commands
```bash
# Update Dockerfile to match project structure
# For uv projects:
COPY pyproject.toml .
RUN uv pip install --system --no-cache .
```

#### Fix: Missing system dependencies
```bash
# Add to Dockerfile RUN apt-get install
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

### 7. Verification checklist

After each fix iteration:

- [ ] Workflow status is ✓ (green check)
- [ ] All jobs completed successfully
- [ ] No warnings or deprecation notices
- [ ] Build artifacts/images created (if applicable)
- [ ] Tests passed

View final status:
```bash
# List recent runs to see status
gh run list --workflow="Build" --limit 3

# Verify images were pushed (for Docker builds)
gh api /user/packages/container/yap-on-slack/versions
```

## Pro tips

**Efficient log searching:**
```bash
# Find errors quickly
gh run view --log-failed 2>&1 | grep -A 10 "ERROR:"

# Find specific failure point
gh run view --log-failed 2>&1 | grep -B 5 "module-not-found"

# Save logs for analysis
gh run view --log-failed > failure-logs.txt
```

**Testing fixes locally first:**
```bash
# Always test Docker builds locally before pushing
docker build -t test . 2>&1 | tee build.log

# Check exit code
echo $?  # 0 = success

# Test specific commands from workflow
mise run test
mise run lint
```

## Anti-patterns to avoid

❌ **Don't:**
- Push multiple rapid fixes without waiting for workflow results
- Make changes without reading the logs first
- Guess at fixes without understanding the root cause
- Skip local testing when possible

✅ **Do:**
- Read logs thoroughly to understand the failure
- Test locally before pushing (when possible)
- Make incremental fixes (one issue at a time)
- Use descriptive commit messages for each fix
- Wait appropriate time between checks (use sleep)

## Summary checklist

When troubleshooting workflows:

- [ ] Read the workflow YAML file to understand what should happen
- [ ] Test workflow commands locally first (when possible)
- [ ] Use `gh run view --log-failed` to get detailed logs
- [ ] Identify the root cause before making fixes
- [ ] Test fixes locally (Docker builds, commands, etc.)
- [ ] Commit with clear message describing the fix
- [ ] Push and wait (use `sleep 15-90` depending on build time)
- [ ] Check status with `gh run list`
- [ ] Repeat until workflow passes (✓)
- [ ] Verify all jobs completed successfully
