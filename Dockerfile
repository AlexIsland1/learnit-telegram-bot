FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Expose port (not really needed for Telegram bot, but some platforms require it)
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"]