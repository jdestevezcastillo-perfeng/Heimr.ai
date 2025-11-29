FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Helm, Kubectl, Curl)
RUN apt-get update && apt-get install -y curl git && \
    # Install Kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/ && \
    # Install Helm
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash && \
    # Cleanup
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY generate_training_data.py .

# Copy failure scenarios data
# We assume the build context is the project root, or we copy specifically.
# Better to expect it in a standard location or mount it.
# For now, let's copy it if we build from root, or assume it's mounted.
# Let's assume we copy it in the build process or mount it.
# But to be self-contained, let's try to COPY it.
# NOTE: Docker build context matters here. 

CMD ["python", "generate_training_data.py"]
