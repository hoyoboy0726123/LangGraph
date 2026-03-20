"""
Browser Bridge：連接 OpenCLI Browser Bridge Chrome 擴充元件。
擴充元件在 localhost:19825 提供 HTTP API，讓我們無需重新登入即可操作瀏覽器。
"""
import httpx
from config import BROWSER_BRIDGE_URL


async def is_bridge_running() -> bool:
    """檢查 Browser Bridge 擴充元件是否已啟動"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{BROWSER_BRIDGE_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


async def bridge_execute(command: str, args: dict = None) -> dict:
    """
    透過 Browser Bridge 執行命令。

    Args:
        command: 命令名稱
        args: 命令參數

    Returns:
        執行結果 dict
    """
    payload = {"command": command, "args": args or {}}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BROWSER_BRIDGE_URL}/execute",
                json=payload,
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e), "success": False}


async def bridge_get_dom() -> str:
    """透過 Browser Bridge 取得當前頁面 DOM"""
    result = await bridge_execute("get_dom")
    return result.get("dom", "")


async def bridge_get_screenshot() -> bytes:
    """透過 Browser Bridge 截圖"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BROWSER_BRIDGE_URL}/screenshot")
            return resp.content
    except Exception:
        return b""
