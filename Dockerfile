FROM python:3.14-slim

WORKDIR /app

COPY main.py .
COPY writeoff ./writeoff

CMD ["python", "main.py"]
