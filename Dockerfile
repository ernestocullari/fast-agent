FROM python:3.11-slim

RUN apt-get update && apt-get install --no-install-recommends -y \
    git gcc build-essential libffi-dev libssl-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .

ENV PYTHONPATH=/app

# Use the Python script directly (it handles PORT internally)
CMD ["python", "src/mcp_agent/railway_app.py"]
