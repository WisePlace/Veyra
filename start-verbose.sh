#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Setting up Veyra for the first time..."
  python3 -m venv .venv || { echo "Python 3 not found. Install it and try again."; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  source .venv/bin/activate
  python -m pip install -r requirements.txt
fi

echo
echo "Veyra running at http://127.0.0.1:5000  (press Ctrl+C to stop)"
( for i in $(seq 1 80); do
    if command -v curl >/dev/null && curl -sf -o /dev/null http://127.0.0.1:5000; then break; fi
    sleep 0.25
  done
  if command -v xdg-open >/dev/null; then xdg-open http://127.0.0.1:5000
  elif command -v open >/dev/null; then open http://127.0.0.1:5000
  fi ) &

python app.py
