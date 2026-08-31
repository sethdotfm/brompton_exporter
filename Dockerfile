FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.py tessera_exporter.py tessera.yml ./
COPY schema/ ./schema/

EXPOSE 19800

ENTRYPOINT ["python", "tessera_exporter.py"]
CMD ["--web.listen-address", ":19800"]
