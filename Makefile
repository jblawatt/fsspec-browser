#!/bin/env make

UV=uv run

serve:
	$(UV) uvicorn app:app --reload

test:
	$(UV) python -m unittest discover -p '*_test.py'

coverage:
	$(UV) coverage run -m unittest discover -p '*_test.py'
	$(UV) coverage report -m 

.PHONY: serve test
