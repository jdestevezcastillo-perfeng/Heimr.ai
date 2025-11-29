FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install FastAPI dependencies
# We don't need to install torch again as it's in the base image
RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY main.py .

# Run as non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
