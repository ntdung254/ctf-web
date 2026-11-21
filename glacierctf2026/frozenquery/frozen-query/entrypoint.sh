#!/bin/sh
export PATH="/.venv/bin:$PATH"
export FLAG=$(cat /flag.txt)
export AUDIT_TOKEN=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
python3 /app/backend.py &
exec python3 /app/app.py
