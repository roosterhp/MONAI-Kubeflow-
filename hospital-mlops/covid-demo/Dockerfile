FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install PyTorch CPU version first
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install scientific packages
RUN pip install --no-cache-dir \
    numpy==1.26.3 \
    SimpleITK==2.3.1 \
    nibabel==5.2.0 \
    matplotlib==3.8.2

# Install MONAI
RUN pip install --no-cache-dir monai==1.3.0

# Install LungMask
RUN pip install --no-cache-dir git+https://github.com/JoHof/lungmask

# Copy pipeline components
COPY components/ /app/components/

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Default command
CMD ["python", "--version"]
