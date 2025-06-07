# Base image
FROM python:3.11-slim

# Prevent .pyc files & enable stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install git and build dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy rest of the app
COPY . .

# Expose Flask default port
EXPOSE 5000

# Start Flask server — make sure `main.py` runs app with `app.run(...)`
CMD ["python", "main.py"]
