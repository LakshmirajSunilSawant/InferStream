"""
StreamML — Airflow DAG: Model Training Pipeline
Runs nightly to retrain LightGBM on freshest features from DuckDB.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    "owner":            "streamml",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="streamml_training_pipeline",
    default_args=default_args,
    description="Nightly LightGBM retraining from DuckDB features",
    schedule_interval="0 2 * * *",   # 2 AM daily
    start_date=datetime(2026, 3, 1),
    catchup=False,
    tags=["streamml", "training", "mlflow"],
) as dag:

    def run_training():
        import sys
        sys.path.insert(0, "/opt/airflow/training")
        from train import train_and_register
        result = train_and_register()
        print(f"Training result: {result}")
        return result

    def validate_model():
        """Check MLflow has a Production model registered."""
        import mlflow
        import os
        client = mlflow.tracking.MlflowClient(
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        )
        models = client.search_model_versions("name='stock_predictor'")
        prod = [m for m in models if m.current_stage == "Production"]
        if not prod:
            raise ValueError("No Production model found after training!")
        print(f"✅ Production model: v{prod[0].version}")

    t_train = PythonOperator(
        task_id="train_lgbm_model",
        python_callable=run_training,
    )

    t_validate = PythonOperator(
        task_id="validate_production_model",
        python_callable=validate_model,
    )

    t_train >> t_validate
