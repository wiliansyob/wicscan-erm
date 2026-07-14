# WicScan Risk Manager — Development commands

.PHONY: up down logs build migrate seed clean status

up:
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend worker scanner-manager ai-gateway

build:
	docker compose build --no-cache

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.scripts.seed

clean:
	docker compose down -v --remove-orphans

status:
	docker compose ps

ollama-pull:
	docker compose exec ollama ollama pull llama3.2

sonar-token:
	@echo "Generating SonarQube token..."
	@docker compose exec sonarqube curl -s -u admin:admin \
	  -X POST "http://localhost:9000/api/user_tokens/generate" \
	  -d "name=wicscan-token&type=GLOBAL_ANALYSIS_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"

backend-shell:
	docker compose exec backend bash

test-backend:
	docker compose exec backend pytest -v

health:
	@echo "Backend:        $$(curl -sf http://localhost:8000/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"down\"))')"
	@echo "Scanner Mgr:    $$(curl -sf http://localhost:8001/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"down\"))')"
	@echo "AI Gateway:     $$(curl -sf http://localhost:8002/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"down\"))')"
	@echo "SonarQube:      $$(curl -sf http://localhost:9000/api/system/status | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"status\",\"down\"))')"
