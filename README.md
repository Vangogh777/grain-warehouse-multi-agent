# 🌾 粮库仓储多智能体系统

基于 **AgentScope** + **LangChain** + **DeepSeek** 的多智能体粮库智能管理系统，实现粮情分析、智能作业、出入库管理、报表分析的 AI 自动化协同。

---

## 🏗 系统架构

```
用户 / 前端界面
      │
      ▼
┌──────────────────────────────────┐
│     AgentScope Orchestrator      │  ← 编排层
├──────────┬──────────┬───────────┤
│ 粮情分析  │ 智能作业  │ 出入库    │  ← LangChain Agent
│  Agent    │  Agent   │  Agent    │
├──────────┴──────────┴───────────┤
│         报表分析 Agent           │
├──────────────────────────────────┤
│      Tool 工具层 (12个工具)       │  ← 函数调用
├──────────────────────────────────┤
│   Mock 数据层 (12个仓房模拟)      │  ← 数据
└──────────────────────────────────┘
```

## ✨ 功能特性

| Agent | 工具 | 能力 |
|:-----|:-----|:-----|
| 🌡 **粮情分析** | `get_sensor_data` `get_silo_info` | 温湿度/水分/虫害监测、异常预警、趋势分析 |
| ⚙ **智能作业** | `get_weather` `get_elec_price` `check_device` `control_device` | 通风/熏蒸方案生成、设备控制、安全校验 |
| 🚛 **出入库** | `query_inbounds` `query_outbounds` `allocate_silo` `calc_settlement` | 预约/质检/称重/仓房分配/结算全流程 |
| 📋 **报表分析** | `query_inventory` `query_trend` `analyze_anomaly` `generate_report` | 库存汇总、趋势分析、异常检测、日报生成 |

## 🚀 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

### 3. 启动后端

```bash
uvicorn src.api.server:app --reload --port 8000
```

### 4. 打开前端

| 页面 | 说明 | 打开方式 |
|:----|:-----|:---------|
| **💬 智能对话** | `index.html` | 浏览器直接打开 |
| **🏭 3D 大屏** | `dashboard.html` | 浏览器直接打开 |
| **📡 API 状态** | `http://localhost:8000` | 浏览器打开 |

### 5. CLI 交互模式

```bash
python src/main.py
```

## 🎯 场景示例

```bash
# 通风条件判断
"S-07仓是否满足通风条件？请分析并给出方案"

# 粮情查询
"最近粮情有什么异常？S-03仓温度多少？"

# 出入库查询
"今天出入库情况怎么样？汇总一下业务数据"

# 报表生成
"生成今日粮库库存日报，检查哪些仓房有异常"
```

## 📂 项目结构

```
wms-mulit-agent/
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置（.env）
│   ├── agents/                    # Agent 定义
│   │   ├── base_agent.py          # LangChain 基类
│   │   ├── bridge.py              # AgentScope 桥接
│   │   ├── grain_condition.py     # 粮情分析 Agent
│   │   ├── operation.py           # 智能作业 Agent
│   │   ├── inoutbound.py          # 出入库 Agent
│   │   └── report.py              # 报表分析 Agent
│   ├── tools/                     # 工具层
│   │   ├── mock_data.py           # 12仓模拟数据
│   │   ├── sensor_tools.py        # 传感器工具
│   │   ├── weather_tools.py       # 天气/电价工具
│   │   ├── device_tools.py        # 设备控制工具
│   │   ├── inout_tools.py         # 出入库工具
│   │   └── report_tools.py        # 报表工具
│   ├── orchestrator/              # 编排层
│   │   └── orchestrator.py        # 并行调度/流式输出
│   ├── api/server.py              # FastAPI 接口
│   └── models/schemas.py          # 数据模型
├── index.html                     # 智能对话前端
├── dashboard.html                 # 3D 数字孪生大屏
├── 需求设计文档.md                 # 完整设计文档
├── requirements.txt
└── .env.example
```

## 📊 3D 数字孪生大屏

- 12 个仓房 3D 可视化，颜色编码温湿度状态
- 点击仓房查看详细传感器数据
- 温度/湿度/虫害指标一键切换
- 30 秒自动刷新，实时监测

## ⚡ 并行执行

编排器使用 `asyncio.gather` 实现多 Agent 并行调用，典型场景执行时间对比：

| 场景 | 串行 | 并行 | 提升 |
|:----|:---:|:---:|:----:|
| 通风条件判断 | ~35s | ~22s | **37%** |
| 粮情+报表 | ~50s | ~32s | **36%** |

## 🛠 技术栈

| 组件 | 选型 |
|:----|:------|
| 多 Agent 编排 | AgentScope |
| Agent 框架 | LangChain (OpenAI Tools Agent) |
| LLM | DeepSeek (OpenAI 兼容 API) |
| 后端 | FastAPI + Uvicorn |
| 前端 | Three.js (3D) + marked (Markdown) |
| 数据 | 模拟数据 (12 仓房传感器) |

## 🔐 安全

- API Key 通过 `.env` 文件配置，不提交到 Git
- `.env` 已在 `.gitignore` 中排除
- 首次使用请执行 `cp .env.example .env` 并填入你的 Key
