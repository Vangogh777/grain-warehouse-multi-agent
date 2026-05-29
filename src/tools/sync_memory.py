"""记忆导出/导入工具 — 通过 JSON 在电脑间同步对话记忆"""
import json
import os
from datetime import datetime


def export_memory(output_path: str = "memory_backup.json") -> str:
    """导出所有对话记忆为 JSON"""
    from src.tools.memory import get_all_sessions, get_conversation_list

    sessions = get_all_sessions(limit=100)
    data = []
    for s in sessions:
        sid = s["session_id"]
        items = get_conversation_list(sid, limit=200)
        data.append({
            "session_id": sid,
            "conversations": items,
        })

    output = {
        "exported_at": datetime.now().isoformat(),
        "session_count": len(sessions),
        "data": data,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output_path


def import_memory(input_path: str = "memory_backup.json") -> int:
    """从 JSON 导入对话记忆到 SQLite"""
    from src.tools.memory import save_exchange

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for session in data.get("data", []):
        sid = session["session_id"]
        for conv in session.get("conversations", []):
            # 避免重复导入
            save_exchange(
                session_id=sid,
                query=conv.get("query", ""),
                answer=conv.get("answer", ""),
                role=conv.get("role", "keeper"),
                scenario=conv.get("scenario", ""),
                agents_used=conv.get("agents_used", []),
            )
            count += 1

    return count


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "import":
        path = sys.argv[2] if len(sys.argv) >= 3 else "memory_backup.json"
        n = import_memory(path)
        print(f"✅ 已导入 {n} 条对话记录")
    else:
        path = sys.argv[1] if len(sys.argv) >= 2 else "memory_backup.json"
        out = export_memory(path)
        print(f"✅ 已导出到 {out}")
