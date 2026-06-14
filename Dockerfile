# Use a lightweight Python image
FROM python:3.14-slim

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
