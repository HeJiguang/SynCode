import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """
    向 JSONL 文件追加单行 JSON 数据。
    
    工程场景：当有新的用户请求或 AI 响应时，将其作为一行新记录追加到文件末尾。
    """
    # 核心细节：自动创建目录
    # parents=True 表示如果父目录（如 logs/traces/）不存在，会自动连同父目录一起创建。
    # exist_ok=True 表示如果目录已经存在，也不会报错。这省去了大量的 os.path.exists() 检查。
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用 "a" (append) 模式打开文件，确保新数据只会追加在末尾，不会覆盖旧数据。
    with path.open("a", encoding="utf-8") as handle:
        # json.dumps 将 Python 字典序列化为 JSON 字符串。
        # ensure_ascii=False 是关键：它保证中文字符会以原生中文保存，而不是变成 \uXXXX 这种难以阅读的 Unicode 转义符。
        # 最后加上 "\n" 确保这条 JSON 独占一行。
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """
    读取并解析整个 JSONL 文件。
    
    返回一个包含所有数据行的列表（List of Dictionaries）。
    """
    # 防御性检查：如果文件压根不存在，直接返回空列表，防止程序抛出 FileNotFoundError。
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    # 使用 "r" (read) 模式打开文件
    with path.open("r", encoding="utf-8") as handle:
        # 文件句柄 (handle) 本身就是一个迭代器，可以直接 for 循环逐行读取，这非常节省内存（不用一次性把大文件全塞进内存）。
        for line in handle:
            stripped = line.strip()
            # 跳过空行（防止文件末尾多余的换行符导致 JSON 解析失败）
            if not stripped:
                continue
            # 将每一行的 JSON 字符串反序列化为 Python 字典，并存入列表
            rows.append(json.loads(stripped))
    return rows


def clear_jsonl(path: Path) -> None:
    """
    清空（删除）指定的 JSONL 文件。
    
    通常用于重置测试环境，或者定期清理过期的日志数据。
    """
    # 先检查文件是否存在，防止 unlink() 抛出异常
    if path.exists():
        # path.unlink() 是 pathlib 中删除文件的标准方法，相当于 os.remove()
        path.unlink()