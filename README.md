# ⚡ InferStream — Real-Time ML Feature Store & Model Serving Pipeline

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-KRaft-231F20?logo=apachekafka)
![Flink](https://img.shields.io/badge/Apache%20Flink-PyFlink-E6526F?logo=apacheflink)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)
![MLflow](https://img.shields.io/badge/MLflow-2.11-0194E2?logo=mlflow)
![Streamlit](https://img.shields.io/badge/Streamlit-1.34-FF4B4B?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![CI/CD](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?logo=githubactions)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

**Production-grade MLOps infrastructure — from raw events to real-time predictions in < 100ms.**

[📖 API Docs](#-api-reference) · [🏗️ Architecture](#️-architecture) · [🚀 Quick Start](#-quick-start) · [📊 Dashboard](#-dashboard)

</div>

---

## 🎯 What Is InferStream?

Most ML demos train a model and call it done. **InferStream** builds the infrastructure layer that real production systems need:

| Problem | InferStream Solution |
|---|---|
| Real-time data ingestion | Apache Kafka (KRaft, no ZooKeeper) |
| Online feature computation | PyFlink sliding windows (VWAP, momentum, volatility) |
| Training/serving skew | Feast unified feature store (Redis + DuckDB) |
| Model versioning & A/B serving | MLflow registry + BentoML |
| Drift detection & alerting | Evidently AI + Prometheus + Grafana |
| One-command start | `docker compose up` |

---

## 🏗️ Architecture

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      REAL-TIME (ONLINE) PATH                              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  [Event Producer]  ──►  Kafka (raw-events)  ──►  Flink Job               ║
║   ~100 ticks/sec         KRaft mode              • 5m avg price           ║
║   7 stock symbols                                • 1m momentum            ║
║                                                  • 10m VWAP               ║
║                               ┌──────────────────• 10m volatility         ║
║                               ▼                  └─────────────────────┐   ║
║                     Redis (Online Store) ◄─── Feast SDK               │   ║
║                     sub-ms lookups                                     │   ║
║                               │                DuckDB (Offline Store) ◄┘   ║
╠═══════════════════════════════│════════════════════════════════════════════╣
║                      SERVING PATH                   │                     ║
╠═══════════════════════════════│════════════════════════════════════════════╣
║                               │                                           ║
║  [API Request]  ──►  FastAPI Gateway  ──►  BentoML Server                ║
║                       /predict              load Production model         ║
║                       /features/{sym}       fetch Feast features          ║
║                       /models               return UP/DOWN + confidence   ║
║                       /drift/report         < 100ms p99 latency           ║
║                       /health                                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                      BATCH / TRAINING PATH                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  [Airflow DAG]  ──►  DuckDB Features  ──►  LightGBM  ──►  MLflow         ║
║   nightly @ 2am        historical             train          registry     ║
║                                                        ──►  BentoML deploy║
╠═══════════════════════════════════════════════════════════════════════════╣
║                      MONITORING                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  [Airflow hourly]  ──►  Evidently AI  ──►  Prometheus  ──►  Grafana      ║
║                          PSI / KS test     /metrics        dashboards     ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## 📦 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Event Streaming** | Apache Kafka 7.6 (KRaft) | Industry standard; no ZooKeeper needed |
| **Stream Processing** | PyFlink (custom sliding windows) | Stateful real-time computation |
| **Feature Store** | Feast (open source) | Used at Uber/Twitter; prevents skew |
| **Online Store** | Redis Stack (RedisJSON) | Sub-ms lookups; TTL expiry |
| **Offline Store** | DuckDB | In-process OLAP; blazing fast queries |
| **Model Registry** | MLflow 2.11 | Industry standard; tracks runs/artifacts |
| **Model Serving** | BentoML 1.2 | Pythonic; built-in batching; dynamic swap |
| **Orchestration** | Apache Airflow 2.9 | DAG-based; nightly training + hourly drift |
| **Drift Detection** | Evidently AI | PSI + KS test; HTML + JSON reports |
| **Metrics** | Prometheus + Grafana | Free; dashboards out of the box |
| **API Gateway** | FastAPI 0.110 | Async; auto OpenAPI docs; rate limiting |
| **Dashboard** | Streamlit 1.34 | Python-native; real-time visualizations |
| **CI/CD** | GitHub Actions | Free for public repos |
| **Container** | Docker Compose | Single command startup |

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (with Compose plugin) — [install](https://docs.docker.com/desktop/)
- 8 GB RAM recommended (all services together)
- Ports free: 8000, 8080, 8501, 9090, 3001, 5000, 6379, 9092

### 1. Clone & Start

```bash
git clone https://github.com/yourusername/inferstream.git
cd inferstream

# Copy and review environment config
cp .env .env.local

# Start the entire stack (Kafka, Redis, MLflow, Airflow, API, Dashboard...)
docker compose up -d

# Watch logs
docker compose logs -f
```

> ⏱️ **Cold start takes ~2-3 minutes** for all containers to become healthy.

### 2. Verify Everything Is Up

```bash
# System health check
curl http://localhost:8000/health

# Should return:
# {"status":"ok","redis":true,"mlflow":true,"bentoml":true,"model":"v1"}
```

### 3. Make a Prediction

```bash
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"symbol": "AAPL"}'

# Response:
# {
#   "symbol": "AAPL",
#   "prediction": "UP",
#   "confidence": 0.7823,
#   "probability": 0.7823,
#   "features": {"avg_price_5m": 185.42, "momentum_1m": 0.0024, ...},
#   "model_version": "v3",
#   "latency_ms": 42.1
# }
```

---

## 📊 Dashboard & UIs

| Service | URL | Credentials |
|---|---|---|
| 🎨 **Streamlit Dashboard** | http://localhost:8501 | — |
| 📖 **API Docs (Swagger)** | http://localhost:8000/docs | — |
| 🧪 **MLflow Registry** | http://localhost:5000 | — |
| 🌊 **Airflow DAGs** | http://localhost:8080 | admin / inferstream123 |
| 📊 **Grafana** | http://localhost:3001 | admin / inferstream123 |
| 🔴 **RedisInsight** | http://localhost:8001 | — |
| 🟠 **Kafka UI** | http://localhost:9080 | — |
| 📈 **Prometheus** | http://localhost:9090 | — |

---

## 🔌 API Reference

### `POST /predict`
Real-time stock direction prediction (UP/DOWN).

```json
Request:  { "symbol": "AAPL" }
Response: {
  "symbol": "AAPL",
  "prediction": "UP",
  "confidence": 0.78,
  "probability": 0.78,
  "features": { "avg_price_5m": 185.4, "momentum_1m": 0.0024, "vwap_10m": 185.1, ... },
  "model_version": "v3",
  "latency_ms": 42.1
}
```

### `GET /features/{symbol}`
Live feature values from Redis online store.

```json
Response: {
  "symbol": "AAPL",
  "avg_price_5m": 185.42,
  "momentum_1m": 0.0024,
  "vwap_10m": 185.15,
  "volatility_10m": 0.32,
  "trade_count_5m": 2341,
  "current_price": 185.88,
  "source": "redis-online-store"
}
```

### `GET /models`
List all registered MLflow model versions.

### `PUT /models/{version}/promote`
Promote a model version to production/staging/archived.

```json
Request:  { "stage": "production" }
Response: { "model": "stock_predictor", "version": "3", "stage": "Production", "status": "ok" }
```

### `GET /drift/report`
Latest Evidently AI drift report summary.

### `GET /health`
Full system health check (Redis, MLflow, BentoML, model version).

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest httpx pytest-cov

# Install service dependencies  
pip install -r api/requirements.txt -r producer/requirements.txt -r flink_jobs/requirements.txt

# Run all tests
pytest tests/ -v --tb=short

# With coverage
pytest tests/ -v --cov=api --cov=producer --cov=flink_jobs --cov-report=term-missing
```

Expected output:
```
tests/test_producer.py::TestStockTick::test_serialize_returns_bytes PASSED
tests/test_producer.py::TestStockTick::test_bid_ask_spread_valid PASSED
tests/test_producer.py::TestStockMarketSimulator::... PASSED  (5 tests)
tests/test_features.py::TestTickWindow::... PASSED  (7 tests)
tests/test_api.py::TestHealthEndpoint::... PASSED  (12 tests)

24 passed in 3.4s
```

---

## 📁 Repository Structure

```
inferstream/
├── docker-compose.yml          ← Full stack: Kafka, Redis, MLflow, Airflow...
├── .env                        ← Environment configuration
├── producer/                   ← Synthetic stock tick generator (GBM model)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── flink_jobs/                 ← PyFlink streaming feature computation
│   ├── feature_job.py          ← VWAP, momentum, volatility, count
│   ├── Dockerfile
│   └── requirements.txt
├── feature_store/              ← Feast feature definitions
│   ├── feature_store.yaml      ← Redis online + DuckDB offline
│   └── features.py             ← Entity, FeatureView, FeatureService
├── training/                   ← LightGBM training + MLflow logging
│   ├── train.py
│   └── requirements.txt
├── dags/                       ← Airflow DAGs
│   ├── training_dag.py         ← Nightly retraining @ 2AM
│   └── drift_dag.py            ← Hourly drift monitoring
├── serving/                    ← BentoML model server
│   ├── service.py              ← POST /predict with MLflow + Feast
│   ├── Dockerfile
│   └── requirements.txt
├── api/                        ← FastAPI gateway (public-facing)
│   ├── main.py                 ← 6 endpoints + rate limiting + Prometheus
│   ├── Dockerfile
│   └── requirements.txt
├── monitoring/                 ← Drift detection + Prometheus config
│   ├── drift_monitor.py        ← Evidently AI PSI/KS tests
│   ├── prometheus.yml          ← Scrape config
│   └── requirements.txt
├── dashboard/                  ← Streamlit real-time UI
│   ├── app.py                  ← Dark mode + live charts + demo mode
│   ├── Dockerfile
│   └── requirements.txt
├── grafana/                    ← Grafana provisioning
│   ├── provisioning/
│   │   ├── datasources/        ← Prometheus datasource
│   │   └── dashboards/         ← Dashboard provider
│   └── dashboards/
├── tests/                      ← Unit + integration tests
│   ├── test_producer.py
│   ├── test_features.py
│   └── test_api.py
├── .github/workflows/
│   └── ci.yml                  ← pytest + Docker build on every push
└── README.md
```

---

## 📏 Non-Functional Requirements

| Requirement | Target | How |
|---|---|---|
| Prediction API latency (p99) | < 100ms | BentoML + Redis + async FastAPI |
| Feature freshness | < 2 seconds | Flink 500ms publish interval + Redis TTL |
| Kafka consumer lag | < 1000 messages | KRaft + consumer group auto-commit |
| Drift check frequency | Every 1 hour | Airflow `drift_dag.py` |
| Test coverage | > 70% core modules | pytest-cov |
| Cold start | < 3 minutes | Docker health checks + dependency ordering |

---

## 🔧 Configuration

All configuration via `.env` (see `.env` for full list):

```bash
KAFKA_TOPIC_RAW_EVENTS=raw-events     # Kafka topic
PRODUCER_SYMBOLS=AAPL,GOOGL,MSFT,... # Symbols to simulate
PRODUCER_RATE=100                      # Events/second
DRIFT_THRESHOLD=0.2                    # PSI threshold for alerts
MODEL_NAME=stock_predictor             # MLflow model name
```

---

## 👤 Author

**Lakshmiraj S. Sawant**  
📧 sawantlakshmiraj22@gmail.com  
🔗 [GitHub](https://github.com/LakshmirajSunilSawant)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">
<strong>⚡ InferStream v1.0 &nbsp;·&nbsp; Real-Time ML Feature Store & Model Serving Pipeline</strong>
</div>
