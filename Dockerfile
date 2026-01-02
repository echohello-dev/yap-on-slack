FROM python:3.13-slim

WORKDIR /app

# Copy dependency files and source code for installation
COPY pyproject.toml README.md ./
COPY yap_on_slack/ ./yap_on_slack/

# Install uv and dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv pip install --system --no-cache .

# Application code is already copied above

# Run the application
CMD ["python", "-m", "yap_on_slack.post_messages"]
