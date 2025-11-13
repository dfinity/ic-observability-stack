FROM python:3.12-slim

RUN pip install --no-cache-dir \
    pyyaml \
    requests \
    ic-py

RUN apt-get update && \
    apt-get install -y --no-install-recommends git

ENTRYPOINT ["python3"]
