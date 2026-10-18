#!/usr/bin/env bash
set -e
export PYTHONPATH=".:$PYTHONPATH"
set -u
# rm -f .coverage coverage.json
ruff check pathaction/*.py
python -m coverage run -m \
  pytest -p no:libtmux -v --cov-report=term tests/*
python -m coverage json
