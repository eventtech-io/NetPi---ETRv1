# NetPi Testing & Development Makefile

.PHONY: install test test-verbose lint format clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip hatchling
	@for pkg in packages/netpi-core packages/netpi-analyzer packages/netpi-cabletester packages/netpi-discovery packages/netpi-dmx packages/netpi-tests packages/netpi-db packages/netpi-osc packages/netpi-oca packages/netpi-server; do 		$(PIP) install -e "$$pkg"; 	done
	$(PIP) install pytest pytest-asyncio httpx pytest-cov

test:
	$(PYTEST) tests/ -v --tb=short

test-verbose:
	$(PYTEST) tests/ -vv --tb=long --log-cli-level=DEBUG

test-coverage:
	$(PYTEST) tests/ -v --cov=packages --cov-report=term-missing --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:
	$(PYTHON) -m py_compile packages/*/netpi_*/*.py

format:
	@echo "Install black/ruff to enable formatting"

clean:
	rm -rf $(VENV) htmlcov .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete



