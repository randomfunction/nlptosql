FROM python:3.10-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.10-slim

WORKDIR /app

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Make sure scripts in .local are usable:
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy project files and set ownership
COPY --chown=appuser:appgroup . .

# Run as non-root user
USER appuser

EXPOSE 8000
CMD uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
