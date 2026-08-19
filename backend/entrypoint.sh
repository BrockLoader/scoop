#!/bin/sh
set -e

echo "[entrypoint] waiting for database..."
python -c "
import os, time, socket
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print('[entrypoint] database is reachable')
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit('[entrypoint] database not reachable after 60s')
"

echo "[entrypoint] running alembic upgrade head..."
alembic upgrade head

echo "[entrypoint] starting uvicorn on :${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"