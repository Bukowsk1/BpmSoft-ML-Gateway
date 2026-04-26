PYTHON ?= python3.11

.PHONY: install api dashboard health docker-up docker-down

install:
	$(PYTHON) -m pip install -r requirements.txt

api:
	$(PYTHON) -m uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8000 --reload

dashboard:
	$(PYTHON) -m streamlit run dashboard.py

health:
	curl http://127.0.0.1:8000/api/health

doctor:
	$(PYTHON) -c "from app.core.runtime_checks import libomp_hint; print(libomp_hint())"

docker-up:
	docker compose up --build

docker-down:
	docker compose down
