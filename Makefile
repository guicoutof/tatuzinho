.PHONY: help venv install-deps up down dev prod start-dev import db-maintenance db-push clean logs test lint format

VENV := venv/bin
PYTHON := $(VENV)/python
PIP := $(VENV)/pip

help:
	@echo "📚 Tatuzinho - Comandos disponíveis:"
	@echo ""
	@echo "🚀 Inicialização:"
	@echo "  make venv           - Criar virtual environment"
	@echo "  make install-deps   - Instalar dependências Python"
	@echo "  make up             - Subir containers Docker (PostgreSQL + Redis)"
	@echo "  make down           - Parar containers Docker"
	@echo ""
	@echo "▶️  Execução:"
	@echo "  make dev            - Subir containers + servidor dev (com reload)"
	@echo "  make prod           - Subir servidor em produção"
	@echo "  make start-dev      - Apenas servidor dev (sem subir containers)"
	@echo ""
	@echo "📊 Dados:"
	@echo "  make import         - Importar dados do StatsBomb"
	@echo "  make db-maintenance - Sincronizar relações e estatísticas derivadas"
	@echo "  make db-push        - Push do schema para banco remoto"
	@echo ""
	@echo "🧹 Limpeza e Logs:"
	@echo "  make clean          - Remover arquivos temporários (__pycache__, .pyc)"
	@echo "  make logs           - Ver logs dos containers"
	@echo ""
	@echo "🧪 Qualidade:"
	@echo "  make test           - Rodar testes (se existirem)"
	@echo "  make lint           - Rodar linter (pylint/flake8)"
	@echo "  make format         - Formatar código (black, isort)"

venv:
	python3 -m venv venv

install-deps: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

up:
	docker-compose up -d

down:
	docker-compose down

dev: up start-dev

start-dev:
	ENV=development $(PYTHON) -m uvicorn app.main:app --reload

prod:
	ENV=production $(PYTHON) -m uvicorn app.main:app

import: venv
	PYTHONPATH=. $(PYTHON) app/statsbomb_importer.py

db-maintenance:
	PYTHONPATH=. ENV=development $(PYTHON) app/db_maintenance.py

db-push:
	bash scripts/db_push.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

logs:
	docker-compose logs -f

test:
	$(PYTHON) -m pytest -v

lint:
	$(PYTHON) -m pylint app/

format:
	$(PYTHON) -m black app/
	$(PYTHON) -m isort app/
