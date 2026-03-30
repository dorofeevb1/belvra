.PHONY: help build up down logs ps shell migrate createsuperuser test lint

# Colors
GREEN := \033[0;32m
NC := \033[0m

help:
	@echo "$(GREEN)Belvra$(NC)"
	@echo ""
	@echo "Available commands:"
	@echo "  make build            - Build all Docker images"
	@echo "  make up               - Start all services"
	@echo "  make down             - Stop all services"
	@echo "  make logs             - View all logs"
	@echo "  make logs-backend     - View backend logs"
	@echo "  make logs-frontend    - View frontend logs"
	@echo "  make ps               - List running containers"
	@echo "  make shell            - Open Django shell"
	@echo "  make bash             - Open bash in backend container"
	@echo "  make migrate          - Run database migrations"
	@echo "  make makemigrations   - Create new migrations"
	@echo "  make createsuperuser  - Create admin user"
	@echo "  make test             - Run backend tests"
	@echo "  make lint             - Run linters"
	@echo ""
	@echo "Dev environment (port 8080):"
	@echo "  make dev-build        - Build dev images"
	@echo "  make dev-up           - Start dev"
	@echo "  make dev-down         - Stop dev"
	@echo "  make dev-logs         - View dev logs"
	@echo "  make deploy-dev       - Deploy to dev server"
	@echo ""
	@echo "Production (port 80):"
	@echo "  make prod-build       - Build production images"
	@echo "  make prod-up          - Start production"
	@echo "  make prod-down        - Stop production"
	@echo "  make deploy-prod      - Deploy to production server"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make gitlab-setup     - Install GitLab CE on server"
	@echo "  make gitlab-runner    - Setup GitLab CI Runner"

# Development
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

ps:
	docker compose ps

shell:
	docker compose exec backend python manage.py shell_plus

bash:
	docker compose exec backend bash

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

createsuperuser:
	docker compose exec backend python manage.py createsuperuser

test:
	docker compose exec backend pytest -v

lint:
	docker compose exec backend flake8 apps/
	docker compose exec backend black --check apps/

format:
	docker compose exec backend isort apps/
	docker compose exec backend black apps/

# Dev environment
dev-build:
	docker compose -f docker-compose.dev.yml build

dev-up:
	docker compose -f docker-compose.dev.yml up -d

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

# Production
prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

# Utilities
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

restart:
	docker compose restart

restart-backend:
	docker compose restart backend celery celery-beat

# Deploy
deploy-dev:
	bash infra/deploy.sh dev

deploy-prod:
	bash infra/deploy.sh prod

# Infrastructure
gitlab-setup:
	bash infra/gitlab/setup.sh

gitlab-runner:
	bash infra/gitlab/setup-runner.sh
