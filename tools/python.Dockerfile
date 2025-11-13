FROM python:3.12-slim

RUN pip install --no-cache-dir \
    pyyaml \
    requests \
    ic-py

ENTRYPOINT ["python3"]
