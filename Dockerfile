# Use a lightweight Python image
FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535

# Set the working directory
WORKDIR /app

# Copy the dependencies file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application without root privileges.
RUN addgroup --system torrentbot && adduser --system --ingroup torrentbot torrentbot

# Copy the bot script and other necessary files
COPY . .
RUN chown -R torrentbot:torrentbot /app

USER torrentbot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')"

# Command to run the bot
CMD ["python", "bot.py"]
