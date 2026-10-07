# The mock static bucket, for the dev stack alone
# (docs/tutorials/6-uploads/4-the-store.md), on py-api's base by the
# same digest. Python's standard library alone: no packages
FROM public.ecr.aws/docker/library/python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

WORKDIR /app
RUN useradd -m -u 1000 appuser && mkdir /store && chown appuser /store
USER appuser
COPY server.py ./

EXPOSE 9100
CMD ["python", "server.py"]
