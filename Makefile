.PHONY: help up down migrate createsuperuser test lint run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Docker containers
	docker compose up -d

down: ## Stop Docker containers
	docker compose down

migrate: ## Run database migrations
	python manage.py migrate

createsuperuser: ## Create a superuser
	python manage.py createsuperuser

test: ## Run tests
	python -m pytest

test-coverage: ## Run tests with coverage
	python -m pytest --cov --cov-report=html

lint: ## Run linters and formatters
	ruff check .
	mypy .

run: ## Run development server
	python manage.py runserver

shell: ## Run Django shell
	python manage.py shell

celery: ## Run Celery worker
	celery -A config.celery worker -l info

beat: ## Run Celery beat scheduler
	celery -A config.celery beat -l info

fresh: ## Fresh start (down, up, migrate, createsuperuser)
	@make down
	@make up
	@make migrate
	@echo "Run 'make createsuperuser' to create admin user"