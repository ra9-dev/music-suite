.PHONY: install install-backend install-frontend dev dev-backend dev-frontend test

# ── Setup ──────────────────────────────────────────────────────────────────

install: install-backend install-frontend
	@echo "✅ All dependencies installed."

install-backend:
	cd backend && poetry install

install-frontend:
	cd frontend && npm install

# ── Development ────────────────────────────────────────────────────────────
# Starts both servers. Requires 'make install' first.

dev:
	@echo "Starting backend (port 8000) and frontend (port 5173)..."
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && poetry run uvicorn app.main:app --reload --port 8000 --log-level debug

dev-frontend:
	cd frontend && npm run dev

# ── Tests ──────────────────────────────────────────────────────────────────

test:
	cd backend && poetry run pytest tests/ -v
