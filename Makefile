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
