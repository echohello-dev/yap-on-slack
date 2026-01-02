FROM python:3.13-slim

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml README.md ./

# Install uv and dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv pip install --system --no-cache .

# Copy application code
COPY yap_on_slack/ ./yap_on_slack/

# Run the application
CMD ["python", "-m", "yap_on_slack.post_messages"]
