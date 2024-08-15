#!/usr/bin/env bash
set -e
export PYTHONPATH=".:$PYTHONPATH"
set -u
pytest -v -v --cov-report=term --cov-report=html:htmlcov tests/*
