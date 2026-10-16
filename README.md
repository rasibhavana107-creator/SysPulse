# SysPulse - Intelligent System Monitoring and Anomaly Detection System

Mini project using four engineering modules, simulated on one laptop.

| Module | File(s) | What it does |
|---|---|---|
| 1 Data Engineering | src/collector.py, src/spark_pipeline.py | psutil collector + labelled fault generator, PySpark 1-minute window features |
| 2 Cloud Engineering | src/cloud_api.py, src/agent.py | Local HTTP ingestion API + SQLite, live scoring and alerts |
| 3 AI Engineering | src/anomaly.py | Isolation Forest vs fixed-threshold baseline |
| 4 Security Engineering | src/security.py | HMAC signing, replay protection, schema validation, rate limit, hash-chained audit ledger |

## Setup
    pip install pyspark scikit-learn psutil pandas numpy matplotlib joblib
    (PySpark also needs Java 11+ installed)

## Run (from this folder, in order)
    python src/collector.py          # creates data/raw_metrics.csv
    python src/spark_pipeline.py     # creates data/features.csv
    python src/anomaly.py            # trains model, writes results/ml_results.json
    PYTHONPATH=src python src/run_tests.py    # API throughput + security tests (Windows: set PYTHONPATH=src)
    PYTHONPATH=src python src/make_figs.py    # regenerates the report figures

Timings (Spark time, API latency) depend on your machine, so re-run and update those numbers in the report if you want them to match your laptop.
