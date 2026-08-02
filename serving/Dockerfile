FROM python:3.11-slim

WORKDIR /app
# libgomp1 = OpenMP runtime; LightGBM's native lib dlopens libgomp.so.1 at import
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 3000
CMD ["bentoml", "serve", "service:StockPredictionService", "--host", "0.0.0.0", "--port", "3000"]
