#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Setting up Veyra for the first time..."
  python3 -m venv .venv || { echo "Python 3 not found. Install it and try again."; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip -q
  python -m pip install -r requirements.txt -q || { echo "Dependency install failed. Run start-verbose.sh to see details."; exit 1; }
else
  source .venv/bin/activate
  python -m pip install -r requirements.txt -q 2>/dev/null
fi

export VEYRA_QUIET=1
echo "Veyra is starting at http://127.0.0.1:5000  (press Ctrl+C to stop)"

( for i in $(seq 1 80); do
    if (exec 3<>/dev/tcp/127.0.0.1/5000) 2>/dev/null; then exec 3>&- 3<&-; break; fi
    sleep 0.25
  done
  sleep 0.5
  if command -v xdg-open >/dev/null; then xdg-open http://127.0.0.1:5000
  elif command -v open >/dev/null; then open http://127.0.0.1:5000
  else start http://127.0.0.1:5000 2>/dev/null || cmd.exe /c start http://127.0.0.1:5000 2>/dev/null
  fi ) &

python app.py
