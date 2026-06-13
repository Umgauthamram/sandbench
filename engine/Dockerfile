# Use a lightweight python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (git for semgrep/patching if required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage caching
COPY requirements.txt ./

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all engine source code files
COPY . .

# Set python path environment variable
ENV PYTHONPATH=/app

# Run the worker script
CMD ["python", "worker.py"]
