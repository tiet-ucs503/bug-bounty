# The mock sign-in, for the dev stack alone (docs/onboarding/local-dev.md),
# on py-api's base by the same digest
FROM public.ecr.aws/docker/library/python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 1000 appuser
USER appuser
COPY server.py ./

EXPOSE 9000
CMD ["python", "server.py"]
