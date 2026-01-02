---
name: github-actions-workflows
description: Create and maintain GitHub Actions workflows in .github/workflows
---

# GitHub Actions Workflow Skill (.github/workflows)

Use this skill when creating or maintaining CI/CD automation via GitHub Actions workflows.

## Definition: "When to use this skill"

Create or modify a workflow if you need to:

- run automated tests, linting, or code quality checks
- build and publish Docker images to GHCR
- validate pull requests before merging
- publish releases or create deployment artifacts

## Where workflows live

All workflows live in `.github/workflows/`.

- Each workflow is a single `.yml` file in this directory
- Workflows are triggered by GitHub events (push, pull_request, release, etc.)

## Naming conventions

Use descriptive, kebab-case names:

- `build.yml` — lint, test, build and publish Docker images
- `release-please.yml` — automated release management

## Pinning action versions

**Always pin GitHub Actions to specific commit SHAs**, not floating tags (`v3`, `v4`).

### How to pin actions

1. Find the action in GitHub Marketplace or on GitHub
2. Use the commit SHA for a specific version
3. Pin as: `uses: owner/action@<commit-sha> # <version>`

Example:
```yaml
- uses: docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f # v3.12.0
```

Benefits:
- Prevents unexpected behavior from action updates
- Makes dependencies explicit and auditable
- Improves security and reproducibility

## Workflow structure best practices

### Permissions

Be explicit about what the workflow needs:

```yaml
permissions:
  contents: read           # read source code
  packages: write          # push to GHCR
```

### Triggers (on:)

Define what events trigger the workflow:

```yaml
on:
  pull_request:            # on every PR
  push:
    branches:
      - main               # on push to main only
```

### Concurrency

Cancel in-progress runs when a new one is triggered:

```yaml
concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true
```

### Jobs structure

- Use `runs-on: ubuntu-latest` for most jobs
- Use `needs: [job1]` to sequence jobs
- Lint and test before building

### Common steps pattern

```yaml
steps:
  - uses: actions/checkout@v4  # Get code
  - name: Setup mise
    uses: jdx/mise-action@v2
  - name: Install dependencies
    run: mise run install
  - name: Run tests
    run: mise run test
```

## Docker image building

Best practices for `docker/build-push-action`:

1. **Use Buildx** for multi-platform builds: `docker/setup-buildx-action`
2. **Login** before pushing: `docker/login-action`
3. **Extract metadata** for tags/labels: `docker/metadata-action`
4. **Build and push**: `docker/build-push-action`
5. **Use caching** to speed up subsequent builds

Tag strategy:
```yaml
tags: |
  type=ref,event=branch           # Branch name
  type=semver,pattern={{version}} # Semantic version
  type=sha,prefix={{branch}}-     # Commit SHA
  type=raw,value=latest,enable={{is_default_branch}}  # Latest on main
```

Push only on main:
```yaml
push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```

## Testing and linting in workflows

Common patterns:

```yaml
- name: Run tests
  run: mise run test

- name: Run linter
  run: mise run lint
```

Use `mise` commands (not direct tool invocations) for consistency with local development.

## Secrets and environment variables

**Never hardcode secrets:**
```yaml
- run: command
  env:
    API_KEY: ${{ secrets.API_KEY }}  # Use GitHub Secrets
```

## Repository-specific notes for yap-on-slack

- **Simple single-purpose tool**: Python script for posting Slack messages
- **Use `mise run`** for all tool invocations (install, test, lint, build)
- **Docker Buildx** is used for building container images
- **GHCR publishing**: Images push to `ghcr.io/echohello-dev/yap-on-slack`
- **Concurrency is important**: Cancel old builds when new ones are triggered

## "Definition of done" checklist

Before committing a workflow:

- [ ] Workflow file named descriptively (kebab-case)
- [ ] All external actions pinned to commit SHAs (not tags)
- [ ] Permissions explicitly defined
- [ ] Concurrency set up (if applicable)
- [ ] Tests/linting run before build jobs
- [ ] Artifacts uploaded with retention policy (if applicable)
- [ ] Secrets never hardcoded, using `${{ secrets.* }}` pattern
- [ ] Workflow tested in a branch before merging

## Useful commands

```bash
# Validate workflow syntax locally
act -l  # list workflows

# Check for workflow issues
gh workflow view <workflow-name>
gh workflow list
```
