# COVID-19 Detection Pipeline Container - OPTIMIZED
# Week5 Implementation - Fast Build with Layer Caching

FROM python:3.11-slim

# Set working directory early
WORKDIR /app

# Upgrade pip and install wheel for faster compilation
RUN pip install --upgrade pip setuptools wheel

# Install system dependencies in single layer with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements FIRST for optimal layer caching
# This layer only rebuilds when requirements.txt changes
COPY config/requirements.txt .

# Install Python requirements with pip cache optimizations
RUN pip install --no-cache-dir --compile --prefer-binary \
    -r requirements.txt

# Copy application code LAST
# This layer only rebuilds when application code changes
COPY components/ /app/components/

# Create data directories and set permissions in single layer
RUN mkdir -p /mnt/data/covid_inputs/week_current \
         /mnt/data/covid_outputs/week_current \
    && chmod +x /app/components/*.py

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; import monai; print('Container healthy')" || exit 1

# Default command
CMD ["python", "-c", "print('COVID-19 Detection Container Ready - Optimized Build')"]