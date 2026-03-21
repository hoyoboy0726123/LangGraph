"""
OpenCLI Tool：透過 subprocess 呼叫 opencli CLI，
複用使用者已登入的 Chrome session 爬取/操作網站。

OpenCLI 架構：
  opencli [site] [command] [options]
        ↓
  Chrome Extension (Browser Bridge) ←→ daemon (localhost:19825)
        ↓
  使用者現有的 Chrome（保留所有登入狀態）

不需要另外啟動瀏覽器，不需要 API Key，直接複用 Chrome session。
"""
import shlex
import subprocess
from langchain_core.tools import tool


def _run(args: list[str], timeout: int = 60) -> str:
    """執行 opencli 命令，回傳輸出字串"""
    try:
        result = subprocess.run(
            ["opencli"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "（無輸出）"
        else:
            err = result.stderr.strip()
            # 給出更友善的錯誤提示
            if "command not found" in err or "No such file" in err:
                return (
                    "opencli 工具未安裝，無法使用此工具。\n"
                    "請立即改用 scrape_page 或 search_web 工具來完成任務，不要再嘗試 run_opencli。"
                )
            if "bridge" in err.lower() or "daemon" in err.lower() or "19825" in err:
                return (
                    "OpenCLI Browser Bridge 未連接。\n"
                    "請確認：\n"
                    "1. Chrome 已開啟\n"
                    "2. OpenCLI Browser Bridge 擴充元件已安裝並啟用\n"
                    f"原始錯誤：{err}"
                )
            return f"opencli 錯誤（exit {result.returncode}）：{err}"
    except FileNotFoundError:
        return (
            "opencli 工具未安裝，無法使用此工具。\n"
            "請立即改用 scrape_page 或 search_web 工具來完成任務，不要再嘗試 run_opencli。"
        )
    except subprocess.TimeoutExpired:
        return f"opencli 執行超時（>{timeout}s），請嘗試縮小範圍或增加 timeout。"
    except Exception as e:
        return f"執行失敗：{e}"


@tool
def run_opencli(command: str) -> str:
    """
    使用 OpenCLI 爬取網站資料或執行社群操作。
    OpenCLI 透過 Chrome Browser Bridge 直接複用已登入的 Chrome session，
    無需重新登入，支援 Twitter/X、Bilibili、知乎、小紅書等 40+ 網站。

    Args:
        command: opencli 命令（不含 'opencli' 前綴）

    範例：
        "list"                                     → 列出所有可用命令
        "twitter timeline --format json --limit 20" → 爬取 Twitter 時間軸
        "twitter tweet --text '今天天氣真好'"         → 發推文
        "twitter like --id 1234567890"             → 對推文按讚
        "bilibili trending --format table"         → B站熱榜
        "bilibili search 'LangGraph' --limit 10"   → 搜尋影片
        "zhihu hot --format md"                    → 知乎熱榜
        "xiaohongshu search '穿搭' --limit 20"      → 搜尋小紅書

    Returns:
        命令輸出結果（格式依 --format 參數決定）
    """
    args = shlex.split(command)
    return _run(args)


@tool
def opencli_list() -> str:
    """
    列出 OpenCLI 目前支援的所有網站和命令。
    執行前請先呼叫此工具了解有哪些可用命令。

    Returns:
        支援的命令清單
    """
    return _run(["list"])


@tool
def opencli_explore(url: str) -> str:
    """
    讓 OpenCLI 自動探索指定網址的 API，
    找出可以爬取的資料結構（用於尚無 adapter 的網站）。

    Args:
        url: 要探索的網址

    Returns:
        探索結果與建議的命令格式
    """
    return _run(["explore", url], timeout=120)


@tool
def opencli_status() -> str:
    """
    檢查 OpenCLI Browser Bridge daemon 的連線狀態。
    如果瀏覽器操作出現問題，先執行此工具診斷。

    Returns:
        daemon 狀態資訊
    """
    import httpx
    try:
        resp = httpx.get("http://localhost:19825/status", timeout=3)
        return f"Browser Bridge 狀態：\n{resp.text}"
    except Exception:
        return (
            "無法連接 Browser Bridge daemon（localhost:19825）。\n"
            "請確認：\n"
            "1. Chrome 已開啟\n"
            "2. OpenCLI Browser Bridge 擴充元件已安裝並啟用\n"
            "3. opencli 已安裝（npm install -g opencli 或依官方文件）"
        )
