#!/bin/bash
export PYTHONUNBUFFERED=1
uv run python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
