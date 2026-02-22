.PHONY: help up down build migrate seed test lint format shell db-shell

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all containers
	docker compose build

logs: ## Tail all logs
	docker compose logs -f

migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed: ## Seed mock data
	cd backend && python -m scripts.seed_mock_data

test: ## Run all tests
	cd backend && pytest tests/ -v

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit -v

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration -v

lint: ## Run linter
	ruff check backend/src

format: ## Format code
	ruff format backend/src

shell: ## Open API container shell
	docker compose exec api bash

db-shell: ## Open psql shell
	docker compose exec postgres psql -U solarpros

pipeline: ## Run full pipeline
	cd backend && python -m scripts.run_pipeline

export: ## Export prospects to CSV
	cd backend && python -m scripts.export_prospects

flower: ## Open Flower dashboard URL
	@echo "http://localhost:5555"

health: ## Check API health
	curl -s http://localhost:8000/api/v1/health | python -m json.tool
