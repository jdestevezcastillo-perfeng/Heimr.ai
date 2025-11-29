FROM python:3.11-slim

WORKDIR /app

# Install libpq-dev for psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

# Run as non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8000"]
