#!/bin/bash
mkdir -p .context

# .context/claude.md
cat > .context/claude.md <<'EOT'
Output unified diffs only. For each change: Goal → Approach → Tests.
Add/modify tests; include exact run commands.
Pin new deps with version + reason.
Python: black+isort, mypy strict, pytest.
JS/TS: eslint+prettier, vitest/jest, Playwright E2E.
Read DB/API settings from .env; treat DBs read-only by default.
Done: lint+types+tests pass; 3 bullets of risks/follow-ups.
EOT

# .env.example
cat > .env.example <<'EOT'
POSTGRES_URL=postgresql://readonly:password@localhost:5432/mydb
SQLITE_DB=./dev.db
OPENAPI_SPEC=https://petstore3.swagger.io/api/v3/openapi.json
CONTEXT7_PORT=8765
POSTGRES_PORT=7771
SQLITE_PORT=7772
OPENAPI_PORT=7773
APP_ENV=dev
APP_PORT=3000
EOT

# .gitignore
cat > .gitignore <<'EOT'
node_modules/
.venv/
venv/
__pycache__/
*.py[cod]
*.pytest_cache/
.mypy_cache/
.coverage
.env
.env.local
.DS_Store
.vscode/
.idea/
logs/
tmp/
dist/
build/
coverage/
EOT

# .editorconfig
cat > .editorconfig <<'EOT'
root = true
[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
indent_style = space
indent_size = 2
trim_trailing_whitespace = true
[*.py]
indent_size = 4
EOT

# Makefile
cat > Makefile <<'EOT'
-include .env
-include .env.example

mcp-up:
	@echo "Starting MCP servers..."
	@pgrep -f "context7-mcp .*--port $(CONTEXT7_PORT)" >/dev/null || \
	context7-mcp --config $$HOME/.context7/context7.toml --port $(CONTEXT7_PORT) --cwd $$PWD >/tmp/context7.log 2>&1 &
	@pgrep -f "@modelcontextprotocol/server-postgres .*--port $(POSTGRES_PORT)" >/dev/null || \
	npx -y @modelcontextprotocol/server-postgres --url "$(POSTGRES_URL)" --mode http --port $(POSTGRES_PORT) >/tmp/postgres-mcp.log 2>&1 &
	@pgrep -f "mcp-sqlite .*--port $(SQLITE_PORT)" >/dev/null || \
	mcp-sqlite --db "$(SQLITE_DB)" --port $(SQLITE_PORT) >/tmp/sqlite-mcp.log 2>&1 &
	@pgrep -f "mcp-openapi-server .*--port $(OPENAPI_PORT)" >/dev/null || \
	mcp-openapi-server --spec "$(OPENAPI_SPEC)" --port $(OPENAPI_PORT) >/tmp/openapi-mcp.log 2>&1 &
	@echo "MCP servers up."

mcp-down:
	@echo "Stopping MCP servers..."
	@pkill -f "context7-mcp .*--port $(CONTEXT7_PORT)" || true
	@pkill -f "@modelcontextprotocol/server-postgres .*--port $(POSTGRES_PORT)" || true
	@pkill -f "mcp-sqlite .*--port $(SQLITE_PORT)" || true
	@pkill -f "mcp-openapi-server .*--port $(OPENAPI_PORT)" || true
	@echo "MCP servers down."

smoke:
	@npm run -s lint || true
	@npm test -s || true
	@pytest -q || true
EOT

# README.md
cat > README.md <<'EOT'
# New Project (MCP-enabled)

## Setup
1. Copy `.env.example` → `.env` and edit values.
2. Start MCP servers: `make mcp-up`.
3. Stop MCP servers: `make mcp-down`.
4. In Cursor, start chat with:

