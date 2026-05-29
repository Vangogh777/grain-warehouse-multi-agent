# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# CLI interactive mode
python src/main.py

# API server (with hot reload)
uvicorn src.api.server:app --reload --port 8000

# Install dependencies
pip install -r requirements.txt
```

## Architecture

This is a multi-agent grain warehouse management system using **LangChain agents** orchestrated by **LangGraph**.

```
User Query → LangGraphOrchestrator → Router (intent detection) → Agent(s) → Tools → Response
```

### Core Components

| Layer | Location | Purpose |
|-------|----------|---------|
| **Orchestrator** | `src/orchestrator/graph_orchestrator.py` | LangGraph state machine for routing queries to agents |
| **Agents** | `src/agents/*.py` | 5 domain-specific agents, each with tools |
| **Tools** | `src/tools/*.py` | LangChain `BaseTool` subclasses for data access |
| **Mock Data** | `src/tools/mock_data.py` | 12 silos with simulated sensors, weather, devices |
| **API** | `src/api/server.py` | FastAPI with `/api/query` and SSE streaming |

### Agent Registry

| Agent | Tools | Scenarios |
|-------|-------|-----------|
| 粮情分析 (GrainCondition) | `get_sensor_data`, `get_silo_info`, `query_knowledge_base` | Temperature/humidity monitoring, anomaly detection |
| 智能作业 (Operation) | Sensor + Weather + Electricity + Device tools + RAG | Ventilation/fumigation planning, device control |
| 出入库 (InOutBound) | Inbound/outbound query tools | Daily business reports, transaction tracking |
| 报表分析 (Report) | Inventory + Trend + Anomaly tools | Daily/monthly reports, statistics |
| 质量检测 (Quality) | Quality query + stats tools | Grade distribution, quality alerts |

### Scenario Routing

The orchestrator detects intent via keyword matching in `detect_scenario()`:
- `ventilation` → 粮情分析 + 智能作业
- `grain_analysis` → 粮情分析
- `inoutbound` → 出入库
- `report` → 报表分析 + 粮情分析
- `quality` → 质量检测
- `general` → single agent fallback

## Configuration

- **Required**: `.env` file with `DEEPSEEK_API_KEY` (copy from `.env.example`)
- **LLM**: DeepSeek via OpenAI-compatible API (`ChatOpenAI` from langchain-openai)
- **Reasoning models**: `deepseek-v4-flash`, `deepseek-v4-pro` use a custom ReAct loop (not LangChain executor)
- **Roles**: 3 personas (keeper/manager/inspector) defined in `src/config.py:ROLES`

## Key Patterns

### Agent Creation
Each agent file exports a `create_*_agent()` factory:
```python
def create_grain_condition_agent(llm=None) -> BaseGrainAgent:
    tools = [SensorDataTool(), SiloInfoTool(), QueryKnowledgeTool()]
    return BaseGrainAgent(name="粮情分析", system_prompt=PROMPT, tools=tools, llm=llm)
```

### Tool Definition
Tools are `BaseTool` subclasses with `name`, `description`, and `_run()`:
```python
class SensorDataTool(BaseTool):
    name = "get_sensor_data"
    description = "获取仓房传感器数据..."
    def _run(self, silo_id: str) -> str: ...
```

### Mock Data Initialization
Call `refresh_sensor_data()` once at startup (in `main.py` and `server.py:startup`).

## Important Notes

- **Path hack**: `sys.path.insert(0, ...)` in `main.py` and `server.py` — run scripts from project root, not from `src/`
- **Tests directory is empty** — test infrastructure must be built from scratch
- **Mock data layer**: All tools return hardcoded data; swapping for real DB requires rewriting `*_tools.py` files
- **CORS**: API allows all origins (`*`)
- **Silo IDs**: Format `S-01` through `S-12` (12 silos total)
