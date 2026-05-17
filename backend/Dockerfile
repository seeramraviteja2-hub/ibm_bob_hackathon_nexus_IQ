FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000

# start.sh runs: alembic upgrade head && uvicorn main:app
# This ensures DB schema is always current before the server accepts traffic.
CMD ["./start.sh"]
