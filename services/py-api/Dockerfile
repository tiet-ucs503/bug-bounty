# By digest, not by tag: Python 3.12.15, slim, from AWS's mirror of
# Docker's official images; the box's own app runs on the same
FROM public.ecr.aws/docker/library/python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 appuser
USER appuser

COPY main.py ./

EXPOSE 8000

# One process: the box's limit is memory, and a starter's traffic
# needs no second worker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]
