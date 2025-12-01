FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests pandas google-cloud-storage aiohttp pyyaml

# Copy scripts
COPY data-pipeline/ /app/data-pipeline/
COPY run_parallel_generation.py /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Entrypoint
CMD ["python", "run_parallel_generation.py"]
