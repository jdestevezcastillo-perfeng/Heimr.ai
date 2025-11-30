FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY controller.py .

# Run as non-root user
RUN useradd -m appuser
USER appuser

# Kopf runs synchronously by default
CMD ["kopf", "run", "controller.py", "--verbose"]
