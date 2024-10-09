#!/bin/env make

UV=uv run

serve:
	$(UV) uvicorn app:app --reload

test:
	$(UV) python -m unittest app_test.py

.PHONY: serve test
