# Real target agent (not a mock)

LangChain + LangGraph ReAct agent with **SQLite tools**. AgentEval still talks to it as
black-box HTTP (`POST /chat`). The difference: the model actually calls tools that
**read and write rows**.

## Requirements

## API key — where it goes

You use **OpenRouter**. One place:

`examples/real-agent/.env` (create from the template):

```bash
cp examples/real-agent/.env.example examples/real-agent/.env
```

then edit `.env` and set:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
AGENTEVAL_REAL_AGENT_MODEL=openai/gpt-4o-mini
```

The server loads this file on startup (`_load_dotenv()`); shell env vars also work
and take precedence. Any OpenRouter model slug works
(e.g. `anthropic/claude-3-5-haiku`). Plain `OPENAI_API_KEY` also works if set instead.

```bash
uv pip install langchain-openai langgraph langchain-core
```

## Run

```bash
python3 examples/real-agent/ops_agent_server.py
# http://127.0.0.1:8770/chat
```

Studio: import `examples/real-agent/ops-agent-prd.md`, agent id `ops-agent`,
endpoint `http://127.0.0.1:8770/chat`, create suite, then Assurance → Execute Run.

Inspect mutations:

```bash
sqlite3 .agenteval/real-agent-ops.db 'SELECT * FROM tickets; SELECT * FROM audit_log;'
```

Keyword scoring still cannot prove a row was deleted. Next product slice: assert
`audit_log` / ticket counts after the run (ΔS), then Jev as Tier-1 typed judge.
