#!/bin/sh
# Mise - runs the CLI pipeline (driver.py) with this project's virtualenv.
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python driver.py "$@"
