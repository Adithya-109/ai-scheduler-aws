# Build from the repo root:  docker build -f worker/Dockerfile -t scheduler-worker .
FROM python:3.13-slim

RUN useradd --create-home --uid 10001 worker
WORKDIR /app
COPY requirements-worker.txt .
RUN pip install --no-cache-dir -r requirements-worker.txt
COPY worker/ worker/

USER worker
ENV WORKER_HOST=0.0.0.0 WORKER_PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=4s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('WORKER_PORT','8000'), timeout=3)"
CMD ["python", "worker/worker_server.py"]
