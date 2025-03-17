#!/usr/bin/env bash
set -e
export PYTHONPATH=".:$PYTHONPATH"
set -u
# rm -f .coverage coverage.json
python -m coverage run -m \
  pytest -v -v --cov-report=term tests/*
python -m coverage json
