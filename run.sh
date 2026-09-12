#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo "Open http://localhost:8000 in your browser."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
