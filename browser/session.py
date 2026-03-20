"""
Session Manager：連接使用者現有的 Chrome（保留登入狀態）。

使用方式：
1. 啟動 Chrome 時加入 --remote-debugging-port=9222
   macOS:   open -a "Google Chrome" --args --remote-debugging-port=9222
   Windows: chrome.exe --remote-debugging-port=9222
   Linux:   google-chrome --remote-debugging-port=9222

2. 本模組透過 CDP 連接該 Chrome，複用所有已登入的 session
"""
import asyncio
import httpx
from config import CHROME_CDP_URL


async def get_chrome_targets() -> list[dict]:
    """取得 Chrome 中所有開啟的分頁資訊"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{CHROME_CDP_URL}/json/list")
            return resp.json()
    except Exception:
        return []


async def is_chrome_running() -> bool:
    """檢查 Chrome 遠端除錯是否已啟動"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{CHROME_CDP_URL}/json/version")
            return resp.status_code == 200
    except Exception:
        return False


async def get_active_tab_url() -> str:
    """取得 Chrome 當前活躍分頁的網址"""
    targets = await get_chrome_targets()
    for t in targets:
        if t.get("type") == "page" and t.get("url", "").startswith("http"):
            return t.get("url", "")
    return ""


def get_chrome_launch_instructions() -> str:
    """回傳啟動 Chrome 遠端除錯模式的指令說明"""
    return (
        "請用以下指令啟動 Chrome（加入遠端除錯 Port）：\n\n"
        "macOS:   open -a 'Google Chrome' --args --remote-debugging-port=9222\n"
        "Windows: chrome.exe --remote-debugging-port=9222\n"
        "Linux:   google-chrome --remote-debugging-port=9222\n\n"
        "啟動後，把你要操作的網站分頁開好，再執行任務即可。"
    )
