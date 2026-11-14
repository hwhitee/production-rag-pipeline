.PHONY: install test lint run migrate up down

install:
	python -m pip install -e '.[dev]'

test:
	pytest -q

lint:
	ruff check src tests

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

up:
	docker compose up --build -d

down:
	docker compose down
