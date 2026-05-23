PYTHON ?= python

.PHONY: format lint smoke smoke-postgres smoke-redis test

format:
	$(PYTHON) -m ruff format src tests scripts

lint:
	$(PYTHON) -m ruff check src tests scripts

smoke:
	$(PYTHON) scripts/smoke_main_flow.py

smoke-postgres:
	$(PYTHON) -m pytest -m integration tests/test_postgres_integration.py

smoke-redis:
	$(PYTHON) -m pytest -m integration tests/test_redis_integration.py

test:
	$(PYTHON) -m pytest
