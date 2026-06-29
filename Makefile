PROJECT := $(shell pwd)
PYTHON  := python3
PIP     := pip3

.DEFAULT_GOAL := help

# ─── help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  Morocco Market Intel"
	@echo ""
	@echo "  make install      Install all Python + Node dependencies"
	@echo "  make scrape       Run scrapers once right now"
	@echo "  make cron         Install daily 11:00 AM cron job"
	@echo "  make cron-remove  Remove the cron job"
	@echo "  make backend      Start FastAPI backend  (port 8000)"
	@echo "  make frontend     Start Next.js frontend (port 3000)"
	@echo "  make start        Start backend + frontend together"
	@echo "  make setup        install + cron  (full first-time setup)"
	@echo ""

# ─── install ───────────────────────────────────────────────────────────────────
.PHONY: install
install: install-python install-node
	@echo "✓ All dependencies installed"

.PHONY: install-python
install-python:
	$(PIP) install -r requirements.txt --break-system-packages -q
	$(PIP) install -r platform/backend/requirements.txt --break-system-packages -q
	$(PYTHON) -m playwright install chromium

.PHONY: install-node
install-node:
	cd platform/frontend && npm install --silent

# ─── scrape ────────────────────────────────────────────────────────────────────
.PHONY: scrape
scrape:
	$(PYTHON) market_runner.py

# ─── cron ──────────────────────────────────────────────────────────────────────
.PHONY: cron
cron:
	chmod +x $(PROJECT)/scrape.sh
	@( crontab -l 2>/dev/null | grep -v "scrape.sh" ; \
	   echo "0 11 * * * $(PROJECT)/scrape.sh" ) | crontab -
	@echo "✓ Cron installed: runs daily at 11:00 AM"
	@crontab -l | grep scrape.sh

.PHONY: cron-remove
cron-remove:
	@crontab -l 2>/dev/null | grep -v "scrape.sh" | crontab - || true
	@echo "✓ Cron removed"

# ─── backend ───────────────────────────────────────────────────────────────────
.PHONY: backend
backend:
	cd platform/backend && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ─── frontend ──────────────────────────────────────────────────────────────────
.PHONY: frontend
frontend:
	cd platform/frontend && npm run dev -- --port 3000

# ─── start both ────────────────────────────────────────────────────────────────
.PHONY: start
start:
	@echo "Starting backend on :8000 and frontend on :3000 ..."
	@echo "→ Dashboard: http://localhost:3000"
	@echo "→ API:       http://localhost:8000"
	@echo "(Ctrl+C to stop both)"
	@trap 'kill 0' INT; \
	  (cd $(PROJECT)/platform/backend && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000) & \
	  (cd $(PROJECT)/platform/frontend && npm run dev -- --port 3000) & \
	  wait

# ─── full setup ────────────────────────────────────────────────────────────────
.PHONY: setup
setup: install cron
	@echo ""
	@echo "✓ Setup complete. Run 'make start' to launch the platform."
