FROM python:3.9-slim

WORKDIR /app

COPY requirements_heimr.txt .
RUN pip install --no-cache-dir -r requirements_heimr.txt

COPY . .
RUN pip install .

ENTRYPOINT ["heimr"]
CMD ["--help"]
