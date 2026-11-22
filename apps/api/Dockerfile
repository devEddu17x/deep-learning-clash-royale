FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SM_MODEL_DIR=/opt/ml/model

WORKDIR /opt/program

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY serve /usr/local/bin/serve
RUN chmod +x /usr/local/bin/serve \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /opt/program

EXPOSE 8080

USER appuser

CMD ["serve"]
