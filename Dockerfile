FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY youtube_summarizer.py .

# Create data directory for state persistence
RUN mkdir -p /data

# Run the application
CMD ["python", "-u", "youtube_summarizer.py"]
