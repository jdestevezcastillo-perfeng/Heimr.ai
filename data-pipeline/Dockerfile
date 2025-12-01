FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (kubectl)
RUN apt-get update && apt-get install -y curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Copy requirements and install
# We'll create a requirements.txt on the fly or assume one exists.
# Let's write the dependencies here to be safe.
RUN pip install --no-cache-dir \
    pandas \
    pyarrow \
    requests \
    pyyaml \
    google-cloud-storage \
    kubernetes \
    aiohttp

# Copy application code
COPY data-pipeline/ /app/data-pipeline/
# Copy scenarios
COPY FAILURE_SCENARIOS.yaml /app/FAILURE_SCENARIOS.yaml

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SCENARIOS_FILE=/app/FAILURE_SCENARIOS.yaml
ENV OUTPUT_DIR=/app/data/training_data

# Entrypoint
ENTRYPOINT ["python3", "data-pipeline/run_gke_generation.py"]
