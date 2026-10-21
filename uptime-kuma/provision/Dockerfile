FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir uptime-kuma-api==1.2.1

COPY provision.py .

CMD ["python", "provision.py"]
