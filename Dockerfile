# Base image
FROM python:3.11-slim

# Environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install git and essential build tools without recommended extras
RUN apt-get update && apt-get install --no-install-recommends -y \
    git \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
ENV PYTHONPATH="/app/src:$PYTHONPATH"
# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project code
COPY . .

# Expose Flask port
EXPOSE 5000

# Start Flask app
CMD ["python", "main.py"]
