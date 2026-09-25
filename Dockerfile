FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
RUN mkdir static
COPY index.html app.js style.css ./static/
RUN mkdir /data && useradd --uid 10001 app && chown app /data
USER app
ENV DATABASE_PATH=/data/rooms.sqlite3
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "8192"]
