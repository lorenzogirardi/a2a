FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8000

# Default command (API mode for HTTP)
CMD ["python", "run_mcp_server.py", "--api"]
