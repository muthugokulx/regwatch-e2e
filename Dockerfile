# Recipe for packaging the RegWatch app into a container image
FROM python:3.10-slim

WORKDIR /app

# Install only what the app needs to RUN (test tools stay out of the image)
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY app/ app/
COPY scripts/ scripts/

ENV DB_PATH=/data/regwatch.db
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]