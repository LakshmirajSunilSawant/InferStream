FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# feature_store.yaml, features.py, feast_client.py, push_service.py
COPY . .

# The feature repo (feature_store.yaml + features.py) is the working dir itself
ENV FEAST_REPO_PATH=/app

CMD ["python", "push_service.py"]
