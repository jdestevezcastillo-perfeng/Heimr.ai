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
    kubernetes

# Copy application code
COPY data-pipeline/ /app/data-pipeline/
COPY docs/data/failure_scenarios.yaml /app/docs/data/failure_scenarios.yaml

# Set environment variables
ENV PYTHONPATH=/app
ENV SCENARIOS_FILE=/app/docs/data/failure_scenarios.yaml
ENV OUTPUT_DIR=/app/data/training_data

# Entrypoint
ENTRYPOINT ["python3", "data-pipeline/run_gke_generation.py"]
