# ---------------------------------------------------------------------------
# Observability stack - developer task runner.
# ---------------------------------------------------------------------------
COMPOSE        ?= docker compose
PROM_IMAGE     ?= prom/prometheus:v3.1.0
APP_URL        ?= http://localhost:8000
LOAD_REQUESTS  ?= 400

.DEFAULT_GOAL := help

.PHONY: help up down restart logs ps load validate validate-config validate-rules clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Build images and start the full stack (detached).
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  Grafana       http://localhost:3000  (admin / admin)"
	@echo "  Prometheus    http://localhost:9090"
	@echo "  Alertmanager  http://localhost:9093"
	@echo "  Sample app    http://localhost:8000  (/metrics for raw metrics)"

down: ## Stop the stack and remove containers + named volumes.
	$(COMPOSE) down -v

restart: down up ## Recreate the stack from scratch.

logs: ## Tail logs from all services.
	$(COMPOSE) logs -f

ps: ## Show running services.
	$(COMPOSE) ps

load: ## Generate sample traffic against the app (mix of ok / work / error).
	@echo "Sending $(LOAD_REQUESTS) requests to $(APP_URL) ..."
	@i=0; while [ $$i -lt $(LOAD_REQUESTS) ]; do \
		curl -s -o /dev/null $(APP_URL)/ ; \
		curl -s -o /dev/null $(APP_URL)/work ; \
		curl -s -o /dev/null $(APP_URL)/error ; \
		i=$$((i+1)); \
	done
	@echo "Done. Open the Grafana 'Sample App - RED / SLO' dashboard."

validate: validate-config validate-rules ## Validate Prometheus config + rules with promtool.

validate-config: ## promtool check config (runs in a Prometheus container).
	docker run --rm -v "$(CURDIR)/prometheus:/etc/prometheus:ro" \
		--entrypoint promtool $(PROM_IMAGE) \
		check config /etc/prometheus/prometheus.yml

validate-rules: ## promtool check rules (runs in a Prometheus container).
	docker run --rm -v "$(CURDIR)/prometheus:/etc/prometheus:ro" \
		--entrypoint promtool $(PROM_IMAGE) \
		check rules /etc/prometheus/rules/recording-rules.yml /etc/prometheus/rules/alerts.yml

clean: down ## Alias for down (remove everything).
