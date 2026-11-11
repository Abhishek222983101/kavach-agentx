set dotenv-load := true
export PYTHONPATH := "backend"

# list recipes
default:
    @just --list

# run all three backend processes (api, trust, store) locally
up:
    uv run honcho -f infra/Procfile start

# unit + acceptance tests (throwaway Postgres in Docker)
test *args:
    uv run pytest -q {{args}}

# apply schema + roles to DATABASE_URL (Neon); --reset wipes demo data
migrate *args:
    uv run python -m kavach.db.migrate {{args}}

# load the demo store (customers, orders, policy, settings)
seed *args:
    uv run python -m kavach.db.seed {{args}}

# security scans: code (bandit, semgrep) and dependencies (pip-audit)
security:
    uv run bandit -q -r backend -x backend/kavach/llm.py -ll
    semgrep scan --config p/python --config p/secrets --quiet --error backend
    uv run pip-audit --progress-spinner off --skip-editable

# build the code map for agents
graft:
    graft build .
