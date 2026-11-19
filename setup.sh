#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
npm run build
printf '\nReady. Run npm start, then open http://127.0.0.1:8501\n'
