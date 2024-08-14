#!/bin/env make

serve:
	uvicorn app:app --reload
