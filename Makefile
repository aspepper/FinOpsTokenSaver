PYTHON ?= python

.PHONY: format lint smoke test

format:
	$(PYTHON) -m ruff format src tests scripts

lint:
	$(PYTHON) -m ruff check src tests scripts

smoke:
	$(PYTHON) scripts/smoke_main_flow.py

test:
	$(PYTHON) -m pytest
