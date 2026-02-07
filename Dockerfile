FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY youtube_summarizer.py .
COPY web_app.py .
COPY database.py .
COPY migrate_to_sqlite.py .
COPY supervisord.conf .
COPY start.sh .

# Copy templates and static directories
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory for state persistence
RUN mkdir -p /data

# Run the application via supervisord
CMD ["bash", "start.sh"]
