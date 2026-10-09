#!/bin/sh
# Mise - starts the local web UI on http://127.0.0.1:5055
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python webapp/app.py
