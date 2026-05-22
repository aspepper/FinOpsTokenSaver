.PHONY: format lint test

format:
	python -m ruff format src tests

lint:
	python -m ruff check src tests

test:
	python -m pytest
