# Use a lightweight Python base image
FROM python:3.11-slim

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser

# Set the working directory
WORKDIR /app

# Copy and install dependencies separately for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Create data directory and set ownership
RUN mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

# Expose the FastAPI server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI server (no --reload in production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
