.PHONY: up down ingest run test eval frontend setup clean help

PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
PYTEST ?= .venv/bin/pytest

help:
	@echo "TruthGuard AI - Makefile Commands:"
	@echo "  make setup     - Create virtual environment and install backend dependencies"
	@echo "  make up        - Start PostgreSQL via Docker Compose"
	@echo "  make down      - Stop PostgreSQL container"
	@echo "  make ingest    - Ingest regulation PDFs from data/raw_pdfs into ChromaDB and BM25"
	@echo "  make run       - Run FastAPI backend development server"
	@echo "  make test      - Run test suite"
	@echo "  make eval      - Run evaluation benchmark on gold test set"
	@echo "  make frontend  - Start Next.js frontend dev server"
	@echo "  make clean     - Remove cache and compiled files"

setup:
	python3.11 -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r backend/requirements.txt

up:
	docker compose up -d postgres || brew services start postgresql@14

down:
	docker compose down || brew services stop postgresql@14

ingest:
	$(PYTHON) scripts/ingest.py

run:
	PYTHONPATH=backend $(UVICORN) app.api.main:app --reload --port 8000

test:
	PYTHONPATH=backend $(PYTEST) backend/tests -v

eval:
	$(PYTHON) scripts/run_eval.py

frontend:
	cd frontend && npm run dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
