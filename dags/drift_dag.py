"""
StreamML — Airflow DAG: Drift Detection Pipeline
Runs every hour to check model drift using Evidently AI.
Sends alerts if drift score exceeds threshold.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner":            "streamml",
    "retries":          1,
    "retry_delay":      timedelta(minutes=2),
    "email_on_failure": False,
}

with DAG(
    dag_id="streamml_drift_detection",
    default_args=default_args,
    description="Hourly model drift detection using Evidently AI",
    schedule_interval="0 * * * *",   # every hour
    start_date=datetime(2026, 3, 1),
    catchup=False,
    tags=["streamml", "monitoring", "evidently"],
) as dag:

    def run_drift_monitor():
        import sys
        sys.path.insert(0, "/opt/airflow/monitoring")
        from drift_monitor import run_drift_check
        result = run_drift_check()
        print(f"Drift result: {result}")
        if result.get("drift_detected"):
            print("⚠️  DRIFT DETECTED — consider retraining!")
        return result

    def log_to_prometheus():
        """Export drift score to Prometheus pushgateway."""
        import os
        import requests
        # Push drift metric (best-effort)
        try:
            score = float(os.environ.get("LAST_DRIFT_SCORE", "0"))
            requests.post(
                "http://prometheus:9091/metrics/job/drift_monitor",
                data=f"streamml_drift_score {score}\n",
                timeout=5,
            )
        except Exception:
            pass  # Non-blocking

    t_drift = PythonOperator(
        task_id="run_evidently_drift_check",
        python_callable=run_drift_monitor,
    )

    t_prom = PythonOperator(
        task_id="push_drift_to_prometheus",
        python_callable=log_to_prometheus,
    )

    t_drift >> t_prom
