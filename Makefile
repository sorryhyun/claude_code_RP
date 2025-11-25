.PHONY: help install run-backend run-frontend run-tunnel-backend run-tunnel-frontend dev stop clean generate-hash simulate test-agents evaluate-agents evaluate-agents-cross load-test

# Use bash for all commands
SHELL := /bin/bash

help:
	@echo "Claude Code Role Play - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev               - Run backend + frontend (local development)"
	@echo "  make install           - Install all dependencies (backend + frontend)"
	@echo "  make run-backend       - Run backend server only"
	@echo "  make run-frontend      - Run frontend server only"
	@echo ""
	@echo "Setup:"
	@echo "  make generate-hash     - Generate password hash for authentication"
	@echo ""
	@echo "Testing & Simulation:"
	@echo "  make simulate          - Run chatroom simulation (requires args)"
	@echo "  make test-agents       - Test agent capabilities (requires args)"
	@echo "  make evaluate-agents   - Evaluate agent authenticity (requires args)"
	@echo "  make evaluate-agents-cross - Cross-evaluate two agents (both directions in parallel)"
	@echo "  make load-test         - Run network load test (requires args)"
	@echo ""
	@echo "Deployment (Cloudflare tunnels for remote access):"
	@echo "  make run-tunnel-backend - Run Cloudflare tunnel for backend"
	@echo "  make run-tunnel-frontend- Run Cloudflare tunnel for frontend"
	@echo ""
	@echo "Maintenance:"
	@echo "  make stop              - Stop all running servers"
	@echo "  make clean             - Clean build artifacts and caches"

install:
	@echo "Installing backend dependencies with uv..."
	uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "📝 Optional: Install Claude Code CLI globally (not required for basic usage)"
	@echo "   Run: sudo npm install -g @anthropic-ai/claude-code"
	@echo ""

run-backend:
	@echo "Starting backend server..."
	cd backend && PATH="$$HOME/.claude/local/node_modules/.bin:$$PATH" uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	@echo "Starting frontend server..."
	cd frontend && npm run dev

run-tunnel-backend:
	@echo "Starting Cloudflare tunnel for backend..."
	cloudflared tunnel --url http://localhost:8000

run-tunnel-frontend:
	@echo "Starting Cloudflare tunnel for frontend..."
	cloudflared tunnel --url http://localhost:5173

dev:
	@mkdir -p /tmp/claude-empty
	@echo "Starting backend and frontend..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:5173"
	@echo "For remote access, run 'make run-tunnel-backend' and 'make run-tunnel-frontend' in separate terminals"
	@echo "Press Ctrl+C to stop all servers"
# 	@$(MAKE) -j3 run-backend run-frontend run-tunnel-backend
	@$(MAKE) -j3 run-backend run-frontend


stop:
	@echo "Stopping servers..."
	@pkill -f "uvicorn main:app" || true
	@pkill -f "vite" || true
	@pkill -f "cloudflared" || true
	@echo "Servers stopped."

clean:
	@echo "Cleaning build artifacts..."
	rm -rf backend/__pycache__
	rm -rf backend/**/__pycache__
	rm -rf backend/*.db
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.vite
	@echo "Clean complete!"

generate-hash:
	@echo "Generating password hash..."
	cd backend && uv run python generate_hash.py

simulate:
	@echo "Running chatroom simulation..."
	@echo "Usage: make simulate ARGS='--password \"yourpass\" --scenario \"text\" --agents \"agent1,agent2\"'"
	@if [ -z "$(ARGS)" ]; then \
		./scripts/simulation/simulate_chatroom.sh --help; \
	else \
		./scripts/simulation/simulate_chatroom.sh $(ARGS); \
	fi

test-agents:
	@echo "Testing agent capabilities..."
	./scripts/testing/test_agent_questions.sh

evaluate-agents:
	@echo "Evaluating agent authenticity..."
	@echo "Usage: make evaluate-agents ARGS='--target-agent \"프리렌\" --evaluator \"페른\" --questions 3'"
	@if [ -z "$(ARGS)" ]; then \
		./scripts/evaluation/evaluate_authenticity.sh --help; \
	else \
		./scripts/evaluation/evaluate_authenticity.sh $(ARGS); \
	fi

evaluate-agents-cross:
	@echo "Cross-evaluating agents (both directions in parallel)..."
	@echo "Usage: make evaluate-agents-cross AGENT1=\"프리렌\" AGENT2=\"페른\" QUESTIONS=7"
	@if [ -z "$(AGENT1)" ] || [ -z "$(AGENT2)" ]; then \
		echo "Error: Both AGENT1 and AGENT2 must be specified."; \
		echo "Example: make evaluate-agents-cross AGENT1=\"프리렌\" AGENT2=\"페른\" QUESTIONS=7"; \
		exit 1; \
	fi; \
	QUESTIONS=$${QUESTIONS:-7}; \
	echo "Running $(AGENT1) → $(AGENT2) and $(AGENT2) → $(AGENT1) evaluations in parallel..."; \
	./scripts/evaluation/evaluate_authenticity.sh --target-agent "$(AGENT2)" --evaluator "$(AGENT1)" --questions $$QUESTIONS & \
	PID1=$$!; \
	./scripts/evaluation/evaluate_authenticity.sh --target-agent "$(AGENT1)" --evaluator "$(AGENT2)" --questions $$QUESTIONS & \
	PID2=$$!; \
	wait $$PID1 $$PID2; \
	echo "Both evaluations completed!"

load-test:
	@echo "Running network load test..."
	@echo "Usage: make load-test ARGS='--password \"yourpass\" --users 10 --rooms 2 --duration 60'"
	@if [ -z "$(ARGS)" ]; then \
		uv run python scripts/testing/load_test_network.py --help; \
	else \
		uv run python scripts/testing/load_test_network.py $(ARGS); \
	fi
