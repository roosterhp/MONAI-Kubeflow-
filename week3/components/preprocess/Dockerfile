FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    monai[all]==1.3.0 \
    nibabel==5.2.0 \
    pydicom==2.4.0 \
    numpy==1.24.4

# Copy preprocessing script
WORKDIR /app
COPY preprocess.py /app/

# Set entrypoint
ENTRYPOINT ["python", "/app/preprocess.py"]
