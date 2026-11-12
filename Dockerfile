# Use a lightweight Python image
FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535

# Set the working directory
WORKDIR /app

# Copy the dependencies file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script and other necessary files
COPY . .

# Expose a port (if required, e.g., for webhook)
EXPOSE 8080

# Command to run the bot
CMD ["python", "bot.py"]
