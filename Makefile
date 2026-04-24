.PHONY: help build up down logs shell migrate create-admin test lint format

help:
	@echo "GoldVault - Luxury Gold Trading Bot"
	@echo "====================================="
	@echo "make build          - Build all Docker images"
	@echo "make up             - Start all services"
	@echo "make down           - Stop all services"
	@echo "make logs           - Tail logs"
	@echo "make shell-api      - Shell into API container"
	@echo "make shell-bot      - Shell into Bot container"
	@echo "make migrate        - Run database migrations"
	@echo "make create-admin   - Create admin user"
	@echo "make test           - Run tests"
	@echo "make lint           - Run linter"
	@echo "make format         - Format code"

build:
	docker-compose build

up:
	docker-compose up -d

up-dev:
	docker-compose up

down:
	docker-compose down

down-volumes:
	docker-compose down -v

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-bot:
	docker-compose logs -f bot

logs-worker:
	docker-compose logs -f worker

shell-api:
	docker-compose exec api bash

shell-bot:
	docker-compose exec bot bash

shell-db:
	docker-compose exec db psql -U gold_user -d gold_db

migrate:
	docker-compose exec api alembic -c migrations/alembic.ini upgrade head

migrate-down:
	docker-compose exec api alembic -c migrations/alembic.ini downgrade -1

migrate-create:
	@read -p "Migration name: " name; \
	docker-compose exec api alembic -c migrations/alembic.ini revision --autogenerate -m "$$name"

create-admin:
	docker-compose exec api python scripts/create_admin.py

seed:
	docker-compose exec api python scripts/seed_data.py

test:
	docker-compose exec api pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-fast:
	docker-compose exec api pytest tests/ -v -x

lint:
	docker-compose exec api ruff check app/ tests/

format:
	docker-compose exec api ruff format app/ tests/

typecheck:
	docker-compose exec api mypy app/

restart-bot:
	docker-compose restart bot

restart-api:
	docker-compose restart api

restart-worker:
	docker-compose restart worker

# Local development (without Docker)
install:
	pip install -r requirements/base.txt -r requirements/api.txt -r requirements/bot.txt -r requirements/worker.txt

migrate-local:
	alembic -c migrations/alembic.ini upgrade head

run-api-local:
	uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

run-bot-local:
	python -m app.bot.main

run-worker-local:
	celery -A app.worker.celery_app worker --loglevel=info
