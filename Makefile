.PHONY: build up run down logs clean demo help

COMPOSE = docker compose
DEMO_CONTAINER = $(shell $(COMPOSE) ps -q sre-demo 2>/dev/null)

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build   Build all images"
	@echo "  up      Start all services (detached)"
	@echo "  run     Build and start all services"
	@echo "  demo    Attach to the sre-demo container (HITL terminal)"
	@echo "  logs    Tail logs for all services"
	@echo "  down    Stop and remove containers"
	@echo "  clean   Stop containers and delete volumes (wipes DB + RSA keys)"

build: .env check-github-token
	$(COMPOSE) build

up: .env
	$(COMPOSE) up -d

run: .env check-github-token
	$(COMPOSE) up --build -d
	@echo ""
	@echo "Services started. Run 'make demo' to attach to the SREDemo terminal."

check-github-token:
	@[ -n "$$GITHUB_TOKEN" ] || (echo "ERROR: GITHUB_TOKEN is not set — required to pull AgentCore from GitHub"; exit 1)

demo:
	$(COMPOSE) attach sre-demo

logs:
	$(COMPOSE) logs -f

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v

.env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — fill in API keys before running."; \
		exit 1; \
	fi
