.PHONY: up down test demo sample

up:
	docker compose up --build -d

down:
	docker compose down

test:
	python3 -m pytest -q

sample:
	python3 tools/generate_sample.py

demo: up
	python3 tools/demo.py
