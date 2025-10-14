# Code quality
format:
    pre-commit run --hook-stage manual --all-files

lint:
    uv run ruff check .

fmt:
    uv run ruff format .

# Local development (without Docker)
install:
    uv sync

migrate:
    uv run python manage.py migrate

runserver port="0.0.0.0:8000":
    uv run python manage.py runserver {{port}}

worker level="info":
    uv run celery -A core worker -l {{level}}

beat level="info":
    uv run celery -A core beat -l {{level}}

test target="":
    mkdir -p .uv-cache
    UV_CACHE_DIR=.uv-cache uv run python manage.py test {{target}}

setup:
    just install
    just migrate

# Docker commands

# Start just infrastructure (PostgreSQL + Redis)
infra:
    docker-compose up -d postgres redis

# Build and start all services (Django + Celery + infrastructure)
up:
    docker-compose up -d

# Build Docker images
build:
    docker-compose build

# Stop all services
down:
    docker-compose down

# Stop and remove volumes (clean slate)
down-clean:
    docker-compose down -v

# View logs (all services or specific one)
logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f {{service}}
    fi

# Run migrations in Docker
docker-migrate:
    docker-compose exec web uv run python manage.py migrate

# Create Django superuser in Docker
docker-createsuperuser:
    docker-compose exec web uv run python manage.py createsuperuser

# Make migrations in Docker
docker-makemigrations:
    docker-compose exec web uv run python manage.py makemigrations

# Django shell in Docker
docker-shell:
    docker-compose exec web uv run python manage.py shell

# Access Django container bash
bash:
    docker-compose exec web bash

# Restart a specific service
restart service:
    docker-compose restart {{service}}

# View service status
ps:
    docker-compose ps

# Clean up Docker resources
clean:
    docker-compose down -v --remove-orphans
    docker system prune -f

# Complete Docker setup (build, up, migrate, create superuser)
docker-setup:
    just build
    just up
    sleep 5
    just docker-migrate
    @echo "Now run: just docker-createsuperuser"
