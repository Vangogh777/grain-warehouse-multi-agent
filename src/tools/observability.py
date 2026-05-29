"""可观测性 — trace_id + Token 追踪 + 请求日志"""
import uuid
import json
import os
from datetime import datetime
from typing import Optional

# SQLite 存储
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".trace.db")


def _migrate_add_column(conn, table, column, col_type):
    """安全添加列（如果不存在）"""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass  # 列已存在


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            trace_type TEXT NOT NULL,
            agent_name TEXT,
            tool_name TEXT,
            tool_input TEXT DEFAULT '',
            tool_output TEXT DEFAULT '',
            depends_on TEXT DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            success INTEGER DEFAULT 1,
            error_msg TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # 迁移：给旧表加缺失的列
    _migrate_add_column(conn, "traces", "tool_input", "TEXT DEFAULT ''")
    _migrate_add_column(conn, "traces", "tool_output", "TEXT DEFAULT ''")
    _migrate_add_column(conn, "traces", "depends_on", "TEXT DEFAULT ''")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            query TEXT NOT NULL,
            scenario TEXT,
            agents_used TEXT,
            tool_calls_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            total_duration_ms INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    return conn


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]


def record_llm_call(
    request_id: str,
    agent_name: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    success: bool = True,
    error_msg: str = "",
):
    conn = _get_db()
    conn.execute(
        "INSERT INTO traces (request_id, trace_type, agent_name, input_tokens, output_tokens, duration_ms, success, error_msg) "
        "VALUES (?, 'llm', ?, ?, ?, ?, ?, ?)",
        (request_id, agent_name, input_tokens, output_tokens, duration_ms, int(success), error_msg),
    )
    conn.commit()
    conn.close()


def record_tool_call(
    request_id: str,
    agent_name: str,
    tool_name: str,
    duration_ms: int,
    success: bool = True,
    tool_input: str = "",
    tool_output: str = "",
    depends_on: str = "",
):
    conn = _get_db()
    conn.execute(
        "INSERT INTO traces (request_id, trace_type, agent_name, tool_name, tool_input, tool_output, depends_on, duration_ms, success) "
        "VALUES (?, 'tool', ?, ?, ?, ?, ?, ?, ?)",
        (request_id, agent_name, tool_name, tool_input[:200], tool_output[:200], depends_on, duration_ms, int(success)),
    )
    conn.commit()
    conn.close()


def get_trace_dag(request_id: str) -> list[dict]:
    """获取指定 request 的 DAG 数据"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT agent_name, tool_name, tool_input, tool_output, depends_on, duration_ms, success "
        "FROM traces WHERE request_id = ? AND trace_type = 'tool' ORDER BY id ASC",
        (request_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "agent": r[0],
            "tool": r[1],
            "input": r[2],
            "output": r[3],
            "depends_on": [d for d in r[4].split(",") if d] if r[4] else [],
            "duration_ms": r[5],
            "success": bool(r[6]),
        }
        for r in rows
    ]


def record_conversation(
    request_id: str,
    query: str,
    scenario: str,
    agents_used: list[str],
    tool_calls_count: int,
    total_tokens: int,
    total_duration_ms: int,
):
    conn = _get_db()
    conn.execute(
        "INSERT INTO conversations (request_id, query, scenario, agents_used, tool_calls_count, total_tokens, total_duration_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (request_id, query, scenario, json.dumps(agents_used, ensure_ascii=False),
         tool_calls_count, total_tokens, total_duration_ms),
    )
    conn.commit()
    conn.close()


def get_recent_conversations(limit: int = 10) -> list[dict]:
    """获取最近对话记录（供前端历史面板使用）"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT request_id, query, scenario, agents_used, tool_calls_count, total_tokens, total_duration_ms, created_at "
        "FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        {
            "request_id": r[0],
            "query": r[1],
            "scenario": r[2],
            "agents_used": json.loads(r[3]),
            "tool_calls_count": r[4],
            "total_tokens": r[5],
            "total_duration_ms": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]
