"""RAG 知识库 — BM25 关键词检索（无需 embedding API）"""

import os
import glob
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# BM25 关键词检索（无需 embedding）
from langchain_community.retrievers import BM25Retriever

# ---------- 配置 ----------
RAG_DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_docs")

_retriever: Optional[BM25Retriever] = None


def _load_docs() -> list[Document]:
    """从 rag_docs/ 目录加载所有 Markdown 文档"""
    docs = []
    for fp in glob.glob(os.path.join(RAG_DOCS_DIR, "*.md")):
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        filename = os.path.basename(fp)
        docs.append(Document(
            page_content=content,
            metadata={"source": filename, "title": filename.replace(".md", "")}
        ))
    return docs


def _split_docs(docs: list[Document]) -> list[Document]:
    """递归字符分块"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n", "。", "；", "，"],
    )
    return splitter.split_documents(docs)


def _build_retriever() -> BM25Retriever:
    """构建 BM25 关键词检索器（无需 embedding API）"""
    docs = _load_docs()
    chunks = _split_docs(docs)

    # BM25 关键词检索
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = 3
    return retriever


def ensure_retriever():
    """懒加载检索器"""
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever()


def query_knowledge(query: str, k: int = 3) -> list[dict]:
    """检索知识库，返回相关文档片段"""
    ensure_retriever()
    docs = _retriever.invoke(query)[:k]
    return [
        {
            "content": d.page_content,
            "source": d.metadata.get("source", "未知"),
            "relevance_score": d.metadata.get("relevance_score", None),
        }
        for d in docs
    ]


def format_knowledge(query: str, k: int = 3) -> str:
    """检索并格式化为 Agent 可读的文本"""
    results = query_knowledge(query, k)
    if not results:
        return "知识库中未找到相关信息。"

    lines = ["📚 检索到以下相关标准/规程：\n"]
    for i, r in enumerate(results, 1):
        source = r["source"].replace("国标_", "GB ").replace(".md", "")
        lines.append(f"【来源 {i}】{source}")
        lines.append(r["content"][:500])
        lines.append("")
    return "\n".join(lines)
