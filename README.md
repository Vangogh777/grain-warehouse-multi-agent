# 🌾 粮库仓储多智能体系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python">
  <img src="https://img.shields.io/badge/LangChain-0.2-green?logo=langchain">
  <img src="https://img.shields.io/badge/LangGraph-0.2-purple">
  <img src="https://img.shields.io/badge/FastAPI-0.100-teal?logo=fastapi">
  <img src="https://img.shields.io/badge/DeepSeek-API-orange">
  <img src="https://img.shields.io/badge/GLM--5-supported-brightgreen">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

基于 **LangChain** + **LangGraph** + **FastAPI** 的多智能体粮库管理系统。
5 个专业 Agent 协同工作，覆盖粮情分析、智能作业、出入库管理、质量检测、报表分析全流程。

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (index.html)                         │
│  角色切换 · 模型选择 · 历史面板 · DAG 推理链路 · 明暗主题       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/SSE 流式
┌────────────────────────▼────────────────────────────────────────┐
│                    FastAPI Server (src/api/server.py)             │
│  /api/query(流式)  /api/debate  /api/trace  /api/history        │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              LangGraph 状态机编排器 (graph_orchestrator.py)       │
│   意图识别 → Agent 节点 → 条件路由 → 结果聚合                  │
│              Debate 辩论器 (debate.py)                            │
│   多 Agent 独立分析 → 加权投票 → 结论                          │
└──────────┬──────────┬──────────┬──────────┬─────────────────────┘
           │          │          │          │
     ┌─────▼──┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌────────┐
     │ 粮情分析 │ │ 智能作业 │ │ 出入库  │ │ 报表分析 │ │ 质量检测 │
     │ Agent   │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
     └────┬────┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬────┘
          │          │         │         │         │
          └──────────┴─────────┴─────────┴─────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      Tool 工具层 (15+ 工具)                      │
│  传感器查询 · 设备控制 · 天气电价 · 出入库管理                  │
│  报表分析 · 质检记录 · RAG 知识库检索 · 记忆管理               │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  数据层                                                         │
│  Mock 数据 (12个仓房) · ChromaDB (向量库) · SQLite (记忆/可观测) │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ 功能特性

### 🤖 5 个专业 Agent

| Agent | 工具数 | 职责 |
|:------|:-----:|:-----|
| 🌡 **粮情分析** | 3 | 温湿度/水分/虫害监测、异常预警、趋势分析 |
| ⚙ **智能作业** | 6 | 通风/熏蒸方案、设备控制、天气电价查询 |
| 🚛 **出入库** | 6 | 预约/质检/称重/仓房分配/结算全流程 |
| 📋 **报表分析** | 6 | 库存汇总、趋势分析、异常检测、日报生成 |
| 🧪 **质量检测** | 6 | 质检记录、等级判定、国标合规、趋势分析 |

### 🔧 核心技术亮点

| 特性 | 说明 |
|:----|:------|
| **RAG 知识库** | BM25 关键词检索国标文档（小麦/稻谷/玉米/操作规程），无需 embedding API |
| **LangGraph 编排** | StateGraph 状态机替代手写 if-else，支持条件路由和并行执行 |
| **多级记忆系统** | SQLite 短期记忆 + ChromaDB 语义召回 + LLM 自动压缩 |
| **Agent 辩论投票** | 多 Agent 独立分析后加权投票，结论更可靠 |
| **混合模型加速** | 推理模型（GLM-5）自动走双模型模式：快模型调工具 + 强模型分析 |
| **流式 SSE** | 实时展示 thinking → tool_calls → agent_done → conclusion |
| **工具调用 DAG** | 可视化推理链路，展示工具调用顺序和耗时 |
| **角色系统** | 保管员/科长/质检员三种视角，Prompt 注入差异化回答 |
| **模型切换** | DeepSeek V3 / V4 Flash / V4 Pro / GLM-5 运行时切换 |
| **可观测性** | trace_id 全链路追踪 + Token 计量 + SQLite 日志 |
| **明暗主题** | 一键切换，偏好持久化到 localStorage |

## 🚀 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

支持多模型：DeepSeek 官方 / 硅基流动 / 智谱 GLM-5

### 3. 启动后端

```bash
python -X utf8 -m uvicorn src.api.server:app --host 0.0.0.0 --port 8080
```

### 4. 打开前端

| 页面 | 说明 |
|:----|:------|
| **💬 智能对话** | `index.html` — 浏览器直接打开 |
| **🏭 3D 大屏** | `dashboard.html` — 浏览器直接打开 |
| **📡 API 文档** | `http://localhost:8000/` |

## 🎯 场景示例

```bash
# 通风条件判断（典型 3~5 秒）
"🌡 S-07满足通风条件？"

# 质量检测 + RAG 知识库
"🧪 小麦一等的容重要求是多少？"

# 多 Agent 辩论
"🤝 S-07是否满足通风条件？"  → 弹出模态框 → 多 Agent 投票

# 角色切换
"分析S-07粮情"  → 保管员看到操作指令，科长看到管理指标

# 出入库日报
"🚛 今天出入库情况怎么样？"
```

## 📂 项目结构

```
grain-warehouse-multi-agent/
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置（模型列表、角色、记忆参数）
│   ├── agents/                    # Agent 定义
│   │   ├── base_agent.py          # 基类（混合模型加速、自动重试）
│   │   ├── grain_condition.py     # 粮情分析 Agent
│   │   ├── operation.py           # 智能作业 Agent
│   │   ├── inoutbound.py          # 出入库 Agent
│   │   ├── report.py              # 报表分析 Agent
│   │   └── quality.py             # 质量检测 Agent
│   ├── tools/                     # 工具层
│   │   ├── mock_data.py           # 12仓模拟数据 + 质检记录
│   │   ├── sensor_tools.py        # 传感器工具
│   │   ├── weather_tools.py       # 天气/电价工具
│   │   ├── device_tools.py        # 设备控制工具
│   │   ├── inout_tools.py         # 出入库工具
│   │   ├── report_tools.py        # 报表工具
│   │   ├── quality_tools.py       # 质检工具（5个）
│   │   ├── rag_tool.py            # RAG 检索工具
│   │   ├── knowledge_base.py      # BM25 知识库引擎
│   │   ├── memory.py              # 多级记忆系统
│   │   └── observability.py       # 可观测性追踪
│   ├── orchestrator/
│   │   ├── graph_orchestrator.py  # LangGraph 状态机编排
│   │   ├── debate.py              # Agent 辩论投票机制
│   │   └── orchestrator.py        # 旧版编排器（已弃用）
│   ├── api/server.py              # FastAPI 接口
│   ├── models/schemas.py          # Pydantic 数据模型
│   └── rag_docs/                  # 国标知识文档
│       ├── 国标_小麦.md
│       ├── 国标_稻谷.md
│       ├── 国标_玉米.md
│       └── 仓储操作规程.md
├── doc/                           # 设计文档
│   ├── 项目架构.html
│   ├── 面试话术与知识点.html
│   ├── 记忆机制设计.html
│   ├── DAG+辩论设计.html
│   └── 推理模型加速方案.html
├── index.html                     # 智能对话前端
├── dashboard.html                 # 3D 数字孪生大屏
├── REASONIX.md                    # 项目记忆（Reasonix 自动读取）
├── requirements.txt
└── .env.example
```

## 🛠 技术栈

| 组件 | 选型 |
|:----|:------|
| Agent 框架 | LangChain (OpenAI Tools Agent) |
| 状态机编排 | LangGraph (StateGraph) |
| LLM | DeepSeek V3/V4 + GLM-5（可切换） |
| RAG 知识库 | BM25 关键词检索 |
| 向量存储 | ChromaDB（记忆系统） |
| 后端 | FastAPI + Uvicorn + SSE 流式 |
| 前端 | 原生 HTML/CSS/JS + marked.js |
| 数据持久化 | SQLite（记忆 + 可观测性） |
| 数据源 | 模拟数据（12 仓房 + 质检记录） |

## 📊 性能参考

| 场景 | DeepSeek V3 | GLM-5（混合模式） |
|:----|:----------:|:----------------:|
| 粮情查询 | 3~5 秒 | 15~20 秒 |
| 通风条件判断 | 5~8 秒 | 20~30 秒 |
| 出入库日报 | 6~10 秒 | 20~25 秒 |
| 多 Agent 辩论 | 8~15 秒 | 30~45 秒 |

## 🎬 面试演示场景

| 场景 | 演示什么 | 话术要点 |
|:----|:---------|:---------|
| S-07 通风条件判断 | 多 Agent 并行 + 工具调用 | "粮情查数据 + 作业查天气/电价/设备 → 综合决策" |
| 今天出入库情况 | 业务 Agent + 结构化输出 | "出入库 Agent 查订单、地磅、仓房、结算" |
| 小麦一等容重要求 | RAG 知识库检索 | "国标文档 → BM25 召回 → Agent 回答" |
| S-07 是否需要熏蒸 | 辩论机制 | "三个 Agent 各自分析 → 投票 → 结论" |

## 🔐 安全

- API Key 通过 `.env` 文件配置，不提交到 Git
- 多模型 Key 各自独立配置
- 模型配置支持运行时切换，无需重启
