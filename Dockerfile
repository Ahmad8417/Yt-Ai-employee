# AI Employee Gold Tier - Dockerfile
# Multi-stage build for smaller final image

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/vault /app/logs /app/mcp_servers

# Copy application code
COPY orchestrator.py .
COPY AI_Employee_Vault/ ./vault/
COPY mcp_servers/ ./mcp_servers/
COPY .claude/ ./.claude/

# Copy Gold Tier modules (will be created)
COPY ralph_loop.py . 2>/dev/null || echo "ralph_loop.py will be mounted"
COPY mcp_registry.py . 2>/dev/null || echo "mcp_registry.py will be mounted"
COPY audit_logger.py . 2>/dev/null || echo "audit_logger.py will be mounted"
COPY error_recovery.py . 2>/dev/null || echo "error_recovery.py will be mounted"
COPY audit_generator.py . 2>/dev/null || echo "audit_generator.py will be mounted"

# Health check script
COPY --chmod=755 <<'EOF' /app/healthcheck.py
#!/usr/bin/env python3
import sys
import os

# Check if vault is accessible
vault_path = os.getenv('AI_EMPLOYEE_VAULT', '/app/vault')
if not os.path.exists(vault_path):
    print(f"Vault not accessible: {vault_path}")
    sys.exit(1)

# Check if required folders exist
required_folders = ['Inbox', 'Needs_Action', 'Done', 'Logs']
for folder in required_folders:
    if not os.path.exists(os.path.join(vault_path, folder)):
        print(f"Missing folder: {folder}")
        sys.exit(1)

print("Health check passed")
sys.exit(0)
EOF

# Create non-root user for security
RUN useradd -m -u 1000 aiemployee && \
    chown -R aiemployee:aiemployee /app
USER aiemployee

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/healthcheck.py

# Expose port for health checks
EXPOSE 8080

# Default command
CMD ["python", "orchestrator.py", "daemon"]
