FROM python:3.11-slim

# Install system libraries required by OpenCV, PyTorch, and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libx11-xcb1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure outputs directory exists
RUN mkdir -p outputs

# Environment defaults for production on Railway
ENV PYTHONUNBUFFERED=1
ENV DEVICE=cpu

# Railway dynamically assigns $PORT; use sh -c to expand it correctly
CMD ["sh", "-c", "uvicorn api_chat:app --host 0.0.0.0 --port ${PORT:-8000}"]
