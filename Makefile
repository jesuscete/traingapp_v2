DOCKER ?= docker

.PHONY: up down infra-up infra-down test lint format

up: infra-up

infra-up:
	$(DOCKER) compose -f infra/docker-compose.yml up -d

infra-down:
	$(DOCKER) compose -f infra/docker-compose.yml down

test:
	cd shared/contracts && uv run pytest
	cd services/api-gateway && uv run pytest
	cd services/ai-parser && uv run pytest

lint:
	cd shared/contracts && uv run ruff check .
	cd services/api-gateway && uv run ruff check .
	cd services/api-gateway && uv run mypy app
	cd services/ai-parser && uv run ruff check .
	cd services/ai-parser && uv run mypy app

format:
	cd services/api-gateway && uv run ruff format .
	cd services/ai-parser && uv run ruff format .
