"""对话记忆 — SQLite 持久化 + 记忆压缩 + 向量召回"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MEMORY_MAX_EXCHANGES,
)

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".memory.db")
_MEMORY_VECTOR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".memory_vector")
_COMPRESSION_THRESHOLD = 8  # 超过 N 轮触发压缩


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT DEFAULT 'keeper',
            query TEXT NOT NULL,
            answer TEXT NOT NULL,
            scenario TEXT DEFAULT '',
            agents_used TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            session_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id, id)
    """)
    conn.commit()
    return conn


# ========== 基础存储 ==========

def save_exchange(session_id: str, query: str, answer: str,
                  role: str = "keeper", scenario: str = "",
                  agents_used: list[str] = None):
    conn = _get_db()
    conn.execute(
        "INSERT INTO conversations (session_id, role, query, answer, scenario, agents_used) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, query, answer[:2000], scenario,
         json.dumps(agents_used or [], ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    # 异步存向量（同步调用，数据量小不影响性能）
    _save_to_vector_store(session_id, query, answer)


def get_recent_history(session_id: str, limit: int = 5) -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT query, answer, role, scenario, created_at "
        "FROM conversations WHERE session_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    result = []
    for r in reversed(rows):
        result.append({
            "query": r[0],
            "answer": r[1],
            "role": r[2],
            "scenario": r[3],
            "time": r[4],
        })
    return result


def get_history_count(session_id: str) -> int:
    conn = _get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    conn.close()
    return count


# ========== 记忆压缩（方案 A）==========

def compress_history(session_id: str) -> str:
    """当历史超过阈值时，压缩早期对话为摘要"""
    count = get_history_count(session_id)
    if count <= _COMPRESSION_THRESHOLD:
        return ""

    conn = _get_db()
    # 取最早的(总数-阈值)条做压缩
    rows = conn.execute(
        "SELECT query, answer FROM conversations WHERE session_id = ? "
        "ORDER BY id ASC LIMIT ?",
        (session_id, count - _COMPRESSION_THRESHOLD),
    ).fetchall()
    conn.close()

    if not rows:
        return ""

    # 拼接早期对话
    text_parts = []
    for q, a in rows:
        text_parts.append(f"用户: {q}\nAI: {a[:200]}")
    text = "\n".join(text_parts)

    # 用 LLM 压缩
    summary = _llm_summarize(text)
    if not summary:
        return ""

    # 存数据库
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO summaries (session_id, summary) VALUES (?, ?)",
        (session_id, summary),
    )
    conn.commit()
    conn.close()

    # 删除已被压缩的旧记录
    conn = _get_db()
    conn.execute(
        "DELETE FROM conversations WHERE id IN ("
        "SELECT id FROM conversations WHERE session_id = ? "
        "ORDER BY id ASC LIMIT ?"
        ")", (session_id, count - _COMPRESSION_THRESHOLD),
    )
    conn.commit()
    conn.close()

    return summary


def get_summary(session_id: str) -> str:
    conn = _get_db()
    row = conn.execute(
        "SELECT summary FROM summaries WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else ""


def _llm_summarize(text: str) -> str:
    """调用 LLM 压缩对话"""
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            timeout=15,
        )
        prompt = f"将以下粮库管理对话压缩为 100 字以内的中文摘要，保留关键信息：\n\n{text[:3000]}"
        result = llm.invoke(prompt)
        return result.content.strip()
    except Exception:
        return ""


# ========== 向量召回（方案 B）==========

def _get_vector_store():
    """获取记忆向量存储（与知识库共用 embedding，独立 collection）"""
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )
    return Chroma(
        collection_name="conversation_memory",
        embedding_function=embeddings,
        persist_directory=_MEMORY_VECTOR_DIR,
    )


def _save_to_vector_store(session_id: str, query: str, answer: str):
    """将对话存入向量库"""
    try:
        vectorstore = _get_vector_store()
        text = f"用户：{query}\n系统：{answer[:500]}"
        vectorstore.add_documents([
            Document(
                page_content=text,
                metadata={"session_id": session_id, "time": datetime.now().isoformat()},
            )
        ])
        vectorstore.persist()
    except Exception:
        pass  # 向量存储失败不影响主流程


def recall_similar(query: str, session_id: str, k: int = 2) -> list[str]:
    """语义召回相关历史对话"""
    try:
        vectorstore = _get_vector_store()
        docs = vectorstore.similarity_search(query, k=k)
        # 过滤当前会话
        docs = [d for d in docs if d.metadata.get("session_id") == session_id]
        return [d.page_content[:200] for d in docs]
    except Exception:
        return []


# ========== 格式化输出 ==========

def format_history(session_id: str, limit: int = 5, query: str = "") -> str:
    """增强版格式化历史 — 最近对话 + 压缩摘要 + 语义召回"""
    parts = []

    # 1. 压缩摘要
    summary = get_summary(session_id)
    if summary:
        parts.append(f"📋 早期对话摘要：{summary}\n")

    # 2. 最近对话
    recent = get_recent_history(session_id, limit)
    if recent:
        lines = ["📝 最近对话："]
        for i, h in enumerate(recent, 1):
            lines.append(f"  [{i}] 用户: {h['query']}")
            lines.append(f"      AI: {h['answer'][:120]}...")
        parts.append("\n".join(lines))

    # 3. 语义召回（如果当前有 query）
    if query:
        similar = recall_similar(query, session_id)
        if similar:
            lines = ["\n🔍 相关历史："]
            for s in similar:
                lines.append(f"  · {s[:120]}...")
            parts.append("\n".join(lines))

    return "\n\n".join(parts)


# ========== 前端历史查询 ==========

def get_conversation_list(session_id: str, limit: int = 20) -> list[dict]:
    """获取对话列表（前端展示用）"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, query, answer, scenario, agents_used, created_at "
        "FROM conversations WHERE session_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    result = []
    for r in reversed(rows):
        result.append({
            "id": r[0],
            "query": r[1],
            "answer": r[2][:100],
            "scenario": r[3],
            "agents_used": json.loads(r[4]) if r[4] else [],
            "time": r[5],
        })
    return result


def get_all_sessions(limit: int = 10) -> list[dict]:
    """获取所有会话列表"""
    conn = _get_db()
    rows = conn.execute(
        "SELECT session_id, COUNT(*) as cnt, MAX(created_at) as last "
        "FROM conversations GROUP BY session_id "
        "ORDER BY last DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"session_id": r[0], "count": r[1], "last_time": r[2]} for r in rows]
