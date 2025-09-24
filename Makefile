# Retrieval Agent Makefile

.PHONY: help install start start-api test clean docker-start docker-stop

help: ## Show this help message
	@echo "Retrieval Agent - Available Commands:"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

start: ## Full startup (install + Weaviate + ingest + API)
	python start.py

start-api: ## Start API server only
	python start.py --api-only

start-chat: ## Start chat GUI only
	python start.py --chat-only

start-full: ## Start both API and chat GUI
	python start.py --full-stack

start-offline: ## Start without Docker/Weaviate
	python start.py --skip-docker

test: ## Run tests
	python -m pytest -v

test-api: ## Test API endpoints
	curl -f http://localhost:8001/health || echo "API not running"

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

docker-start: ## Start Weaviate with Docker
	docker run -d -p 8080:8080 -p 50051:50051 --name weaviate \
		-e QUERY_DEFAULTS_LIMIT=25 \
		-e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
		-e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
		-e DEFAULT_VECTORIZER_MODULE='none' \
		-e ENABLE_MODULES='' \
		-e CLUSTER_HOSTNAME='node1' \
		semitechnologies/weaviate:latest

docker-stop: ## Stop Weaviate container
	docker stop weaviate || true
	docker rm weaviate || true

docker-status: ## Check Weaviate status
	curl -f http://localhost:8080/v1/meta && echo "✅ Weaviate is running" || echo "❌ Weaviate is not running"

ingest: ## Ingest PDFs from data directory
	curl -X POST "http://localhost:8001/ingest/data-directory" \
		-H "Content-Type: application/json" \
		-d '{"doc_type": "regulation", "jurisdiction": "KR", "lang": "ko"}'

query: ## Test query (replace with your query)
	curl -X POST "http://localhost:8001/agent/query" \
		-H "Content-Type: application/json" \
		-d '{"query": "전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?", "lang": "ko"}' | python -m json.tool

rebuild-vectors: ## Rebuild metadata vectors
	curl -X POST "http://localhost:8001/maintenance/rebuild-metadata-vectors"

dev: ## Development mode (API only, no test)
	python start.py --api-only --skip-test

chat: ## Start chat GUI
	python chat.py

prod: ## Production mode (full startup)
	python start.py --verbose
