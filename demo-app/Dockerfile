# Simple demo Dockerfile for CI/CD testing
FROM alpine:latest

# Metadata
LABEL maintainer="demo"
LABEL description="Simple demo app for CI/CD pipeline testing"

# Install basic tools
RUN apk add --no-cache curl

# Create app directory
WORKDIR /app

# Add simple script
RUN echo '#!/bin/sh' > /app/run.sh && \
    echo 'echo "Demo app running successfully"' >> /app/run.sh && \
    chmod +x /app/run.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Run the app
CMD ["/app/run.sh"]
