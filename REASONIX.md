# REASONIX.md — 粮库仓储多智能体系统

## Stack
- **Language:** Python 3.10+
- **API server:** FastAPI + Uvicorn [`src/api/server.py`](src/api/server.py:1)
- **Agent framework:** LangChain (AgentExecutor + create_openai_tools_agent) [`src/agents/base_agent.py`](src/agents/base_agent.py:1)
- **Graph orchestrator:** LangGraph (StateGraph) [`src/orchestrator/graph_orchestrator.py`](src/orchestrator/graph_orchestrator.py:1)
- **LLM:** DeepSeek API via OpenAI-compatible ChatOpenAI [`src/config.py`](src/config.py:14)
- **Frontend:** Single-file HTML (no bundler) [`index.html`](index.html:1) · [`dashboard.html`](dashboard.html:1)
- **RAG:** ChromaDB + `langchain-chroma` [`src/tools/rag_tool.py`](src/tools/rag_tool.py:1)
- **Memory:** Short-term + long-term store via `src/tools/memory.py`

## Layout

| Path | Purpose |
|------|---------|
| `src/agents/` | 5 agents: grain_condition, operation, inoutbound, report, quality |
| `src/orchestrator/` | `orchestrator.py` (if/else dispatch) and `graph_orchestrator.py` (LangGraph) |
| `src/tools/` | LangChain BaseTool subclasses + mock data + RAG/knowledge_base + memory |
| `src/api/` | FastAPI server with SSE streaming and CORS all-origins |
| `src/rag_docs/` | Knowledge base documents (grain standards, operation procedures) |
| `doc/` | Design documentation (HTML/Markdown) |
| `index.html` | Chat frontend (role switching, model selection, DAG viewer, dark theme) |
| `dashboard.html` | 3D digital twin (Three.js via importmap) |
| `tests/` | Empty (`__init__.py` only) |

## Commands
- **API server:** `uvicorn src.api.server:app --reload --port 8000`
- **CLI demo:** `python src/main.py`

## Conventions
- **Agent factory pattern:** each `src/agents/*.py` exports `create_*_agent(llm=None) -> BaseGrainAgent`.
- **Tool pattern:** each tool is a `BaseTool` subclass with `name` + `description` + `args_schema` + `_run()`, exposed in `/src/tools/` and loaded into agents via `tools=[...]` list.
- **Chinese docstrings** throughout codebase (agents, tools, config).
- **Mock data layer:** `src/tools/mock_data.py` provides `get_sensor_data()` / `get_weather()` / `get_device_status()` etc.; call `refresh_sensor_data()` once at startup.
- **Commit style:** Conventional Commits prefix (`docs:`, `chore:`, `fix:`, `feat:`) observed in git history.
- **Env config:** `DEEPSEEK_API_KEY` via `.env` file (`.env.example` template provided); `.env` in `.gitignore`.
- **CORS:** `allow_origins=["*"]` in `src/api/server.py`.

## Watch out for
- **`sys.path.insert(0, ...)`** in both `src/main.py` and `src/api/server.py` — run scripts from project root, never from `src/`.
- **LangGraph vs Orchestrator:** `graph_orchestrator.py` is the newer active path; `orchestrator.py` is the legacy if/else version.
- **Tests directory empty** — any test infrastructure must be built from scratch.
- **Mock data is in-memory** — `refresh_sensor_data()` must be called before any query; no persistence across restarts.
