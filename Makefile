start-dev: up
	uvicorn app.main:app --reload

start:
	uvicorn app.main:app

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f postgres

install-deps:
	pip install -r requirements.txt.