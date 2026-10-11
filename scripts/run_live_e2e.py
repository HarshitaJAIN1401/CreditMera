#!/usr/bin/env python3
"""Runner script to launch a live Uvicorn server on PostgreSQL 16 and execute e2e_evaluation.py.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

# 1. Resolve test database password from .env.local
env_path = Path(r"E:\CreditMera project dip\CreditMera\.env.local")
lines = env_path.read_text(encoding="utf-8").splitlines()
password = None
for line in lines:
    line = line.strip()
    if line.startswith("CREDITMERA_DB_PASSWORD="):
        password = line.split("=", 1)[1].strip().strip('"\'')
        break

if not password:
    print("ERROR: CREDITMERA_DB_PASSWORD not found in .env.local")
    sys.exit(1)

test_port = 8008
target_db = "creditmera_migration_test"
db_url = f"postgresql+psycopg2://creditmera:{password}@localhost:5432/{target_db}"

# Environment for backend subprocess
env = os.environ.copy()
env["DATABASE_URL"] = db_url
env["ENVIRONMENT"] = "development"
env["STORAGE_BACKEND"] = "local"
env["PYTHONPATH"] = str(Path(r"E:\CreditMera project dip\CreditMera\backend"))

print("=" * 75)
print(f"STARTING LIVE BACKEND SERVER ON PORT {test_port}")
print(f"Target Database: {target_db} (PostgreSQL 16)")
print("=" * 75)

backend_dir = Path(r"E:\CreditMera project dip\CreditMera\backend")
proc = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(test_port),
        "--log-level",
        "warning",
    ],
    cwd=str(backend_dir),
    env=env,
)

try:
    import httpx
    # Wait for server to become ready
    print("Waiting for /health/ready...")
    ready = False
    for _ in range(30):
        try:
            r = httpx.get(f"http://127.0.0.1:{test_port}/health/ready", timeout=1.0)
            if r.status_code == 200:
                ready = True
                print(f"Server is READY! Response: {r.json()}")
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready:
        print("ERROR: Server failed to become ready within 15 seconds.")
        sys.exit(1)

    # Execute e2e_evaluation.py
    from e2e_evaluation import E2EEvaluationRunner
    runner = E2EEvaluationRunner(base_url=f"http://127.0.0.1:{test_port}", timeout=20.0)
    success = runner.run_all()
    if not success:
        sys.exit(1)

finally:
    print("\nShutting down test Uvicorn server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Server stopped cleanly.")

    # Clean up test rows created by E2E test
    try:
        import psycopg2
        conn = psycopg2.connect(host="localhost", port=5432, user="creditmera", password=password, dbname=target_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email LIKE 'e2e_%';")
        conn.commit()
        print(f"Cleaned up {cur.rowcount} test user(s) and associated records from {target_db}.")
        cur.close()
        conn.close()
    except Exception as err:
        print(f"Note: Post-test cleanup skipped: {err}")

sys.exit(0)
