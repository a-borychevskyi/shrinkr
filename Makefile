.PHONY: makemigration, migrate

makemigration:
	alembic revision --autogenerate -m "Rename Me"

migrate:
	alembic upgrade head