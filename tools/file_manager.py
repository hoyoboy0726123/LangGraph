"""
File Manager Tool：在允許的資料夾白名單內讀寫檔案，無需人工確認。
"""
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

from config import ALLOWED_PATHS, OUTPUT_BASE_PATH


def _is_allowed(path: Path) -> bool:
    """確認路徑在白名單內（防止 path traversal）"""
    resolved = path.resolve()
    for allowed in ALLOWED_PATHS:
        try:
            resolved.relative_to(allowed.resolve())
            return True
        except ValueError:
            continue
    return False


def _resolve_path(filepath: str) -> Path:
    """
    將相對路徑解析為絕對路徑。
    若不帶斜線，預設放在 OUTPUT_BASE_PATH 下。
    """
    p = Path(filepath)
    if not p.is_absolute():
        p = OUTPUT_BASE_PATH / p
    return p.expanduser().resolve()


@tool
def save_to_file(content: str, filename: str) -> str:
    """
    將內容儲存到本地檔案（自動放在 AI 輸出目錄）。

    Args:
        content: 要儲存的文字內容
        filename: 檔案名稱（例如：「stock_report.md」或「data/prices.json」）

    Returns:
        成功訊息或錯誤訊息
    """
    path = _resolve_path(filename)

    if not _is_allowed(path):
        return f"拒絕存取：{path} 不在允許的資料夾清單中。"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"已儲存到：{path}（{len(content)} 字元）"
    except Exception as e:
        return f"儲存失敗：{e}"


@tool
def read_from_file(filepath: str) -> str:
    """
    讀取本地檔案內容。

    Args:
        filepath: 檔案路徑（相對或絕對路徑）

    Returns:
        檔案內容或錯誤訊息
    """
    path = _resolve_path(filepath)

    if not _is_allowed(path):
        return f"拒絕存取：{path} 不在允許的資料夾清單中。"

    if not path.exists():
        return f"檔案不存在：{path}"

    try:
        content = path.read_text(encoding="utf-8")
        return f"【{path}】\n\n{content}"
    except Exception as e:
        return f"讀取失敗：{e}"


def save_to_file_direct(content: str, filename: str) -> str:
    """
    不透過 @tool 的直接呼叫版本（供內部使用）。
    若 filename 中包含 {date}，自動替換為今天日期。
    """
    filename = filename.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
    path = _resolve_path(filename)

    if not _is_allowed(path):
        return f"拒絕存取：{path} 不在允許的資料夾清單中。"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"已儲存到：{path}"
    except Exception as e:
        return f"儲存失敗：{e}"
