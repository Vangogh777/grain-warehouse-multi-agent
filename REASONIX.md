# REASONIX.md — 粮库仓储多智能体系统

## Stack
- **Language:** Python 3.x
- **API server:** FastAPI + Uvicorn [`src/api/server.py`](src/api/server.py:1)
- **Agent framework:** LangChain (AgentExecutor + create_openai_tools_agent) [`src/agents/base_agent.py`](src/agents/base_agent.py:1)
- **LLM:** DeepSeek API via OpenAI-compatible ChatOpenAI [`src/config.py`](src/config.py:14)
- **Data validation:** Pydantic v2 [`src/models/schemas.py`](src/models/schemas.py)

## Layout

| Path | Purpose |
|------|---------|
| `src/agents/` | 4 agents + base class: grain_condition, operation, inoutbound, report |
| `src/orchestrator/` | Multi-agent dispatcher + result aggregation |
| `src/tools/` | LangChain BaseTool functions + mock sensor/data layer |
| `src/api/` | FastAPI server (CORS enabled, streaming support) |
| `src/models/` | Pydantic schemas |
| `tests/` | Empty — `__init__.py` only, no test files found |
| `index.html` | Chat UI frontend (single HTML file) |
| `dashboard.html` | 3D digital twin dashboard |

## Commands
No `pyproject.toml` or `setup.py` scripts configured. Run via:
- **CLI demo:** `python src/main.py`
- **API server:** `uvicorn src.api.server:app --reload`

## Conventions
- **Docstrings** in Chinese throughout the codebase.
- **Agent construction:** each agent file (`src/agents/*.py`) exports a `create_*_agent()` factory function.
- **Tool registration:** tools are plain LangChain `BaseTool` subclasses with `name` + `description` + `_run()`.
- **Mock data:** 12 silos simulated in `src/tools/mock_data.py`; call `refresh_sensor_data()` once on startup.
- **CORS:** API server allows all origins (`*`).

## Watch out for
- **`sys.path.insert(0, ...)` path hack** in `src/main.py` and `src/api/server.py` — run scripts from project root, not from `src/`.
- **`.env` required** for `DEEPSEEK_API_KEY` — see `.env.example`. Missing key crashes at agent construction.
- **`tests/` is empty** — any test infrastructure must be built from scratch.
- **Mock data layer** — sensor/device/inventory tools return hardcoded data; swapping for real DB will require rewriting all `*_tools.py` files.
