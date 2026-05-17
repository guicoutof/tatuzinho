.PHONY: dev prod up down install-deps import db-push

dev: up
	ENV=development uvicorn app.main:app --reload

prod:
	ENV=production uvicorn app.main:app

up:
	docker-compose up -d

down:
	docker-compose down

install-deps:
	pip install -r requirements.txt

import:
	PYTHONPATH=. venv/bin/python app/statsbomb_importer.py

db-push:
	scripts/db_push.sh
