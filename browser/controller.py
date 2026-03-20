"""
Browser Controller：統一的瀏覽器操作介面。
優先順序：
  1. OpenCLI Browser Bridge（Chrome 擴充元件，保留登入狀態）
  2. Playwright CDP 連接（連接使用者的 Chrome）
  3. Playwright 啟動新 Chromium（後備方案）
"""
import asyncio
import base64
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL_FAST

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_FAST, temperature=0)

# 執行緒安全的單例
_controller: Optional["BrowserController"] = None


def get_controller() -> "BrowserController":
    global _controller
    if _controller is None:
        _controller = BrowserController()
    return _controller


class BrowserController:
    """同步封裝，內部用 asyncio 執行非同步操作"""

    def __init__(self):
        self._page = None
        self._playwright = None
        self._browser = None

    def _run(self, coro):
        """在新事件迴圈中執行 coroutine"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    async def _ensure_page(self):
        """確保有可用的頁面（優先連接使用者的 Chrome）"""
        if self._page and not self._page.is_closed():
            return

        from playwright.async_api import async_playwright
        from browser.session import is_chrome_running
        from config import CHROME_CDP_URL

        self._playwright = await async_playwright().start()

        if await is_chrome_running():
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(CHROME_CDP_URL)
                contexts = self._browser.contexts
                if contexts:
                    pages = contexts[0].pages
                    self._page = pages[-1] if pages else await contexts[0].new_page()
                    return
            except Exception:
                pass

        # 後備：啟動新瀏覽器
        self._browser = await self._playwright.chromium.launch(headless=False)
        context = await self._browser.new_context()
        self._page = await context.new_page()

    def navigate(self, url: str) -> str:
        async def _nav():
            await self._ensure_page()
            try:
                await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await self._page.title()
                return f"已導航到：{url}（標題：{title}）"
            except Exception as e:
                return f"導航失敗：{e}"
        return self._run(_nav())

    def click(self, description: str) -> str:
        async def _click():
            await self._ensure_page()
            try:
                # 先截圖讓 AI 識別元素
                screenshot_bytes = await self._page.screenshot(type="png")
                b64 = base64.b64encode(screenshot_bytes).decode()

                response = _llm.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": f"請找出符合「{description}」的元素，回覆其 CSS selector 或 XPath，只回覆 selector，不要其他說明。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ])
                ])
                selector = response.content.strip()

                await self._page.click(selector, timeout=10000)
                return f"已點擊：{description}"
            except Exception as e:
                # 後備：嘗試直接用文字內容點擊
                try:
                    await self._page.get_by_text(description).first.click(timeout=5000)
                    return f"已點擊文字「{description}」"
                except Exception:
                    return f"點擊失敗：{e}"
        return self._run(_click())

    def type_text(self, selector: str, text: str) -> str:
        async def _type():
            await self._ensure_page()
            try:
                await self._page.fill(selector, text, timeout=10000)
                return f"已在「{selector}」輸入文字"
            except Exception:
                try:
                    await self._page.get_by_placeholder(selector).fill(text)
                    return f"已在欄位輸入文字"
                except Exception as e:
                    return f"輸入失敗：{e}"
        return self._run(_type())

    def screenshot_and_describe(self) -> str:
        async def _shot():
            await self._ensure_page()
            try:
                screenshot_bytes = await self._page.screenshot(type="png", full_page=False)
                b64 = base64.b64encode(screenshot_bytes).decode()

                # 儲存截圖
                from config import OUTPUT_BASE_PATH
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = OUTPUT_BASE_PATH / f"screenshot_{ts}.png"
                path.write_bytes(screenshot_bytes)

                response = _llm.invoke([
                    HumanMessage(content=[
                        {"type": "text", "text": "請描述這個網頁截圖的內容，重點說明可互動的元素（按鈕、連結、表單等）。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ])
                ])
                return f"截圖已儲存到 {path}\n\n頁面描述：\n{response.content}"
            except Exception as e:
                return f"截圖失敗：{e}"
        return self._run(_shot())

    def scroll(self, direction: str = "down") -> str:
        async def _scroll():
            await self._ensure_page()
            try:
                if direction == "up":
                    await self._page.keyboard.press("PageUp")
                else:
                    await self._page.keyboard.press("PageDown")
                return f"已向{direction}滾動頁面"
            except Exception as e:
                return f"滾動失敗：{e}"
        return self._run(_scroll())

    def fill_form(self, fields: dict) -> str:
        async def _fill():
            await self._ensure_page()
            results = []
            for field, value in fields.items():
                try:
                    await self._page.fill(f"[name='{field}'], [id='{field}'], [placeholder*='{field}']", str(value))
                    results.append(f"✓ {field}")
                except Exception as e:
                    results.append(f"✗ {field}：{e}")
            return "表單填寫結果：\n" + "\n".join(results)
        return self._run(_fill())

    def execute_action(self, action: str, **kwargs) -> str:
        """
        透過 Adapter 系統執行社群操作（按讚、回覆、發文等）
        """
        async def _exec():
            await self._ensure_page()
            try:
                from adapters.loader import get_adapter_for_url
                url = self._page.url
                adapter = get_adapter_for_url(url)
                if not adapter:
                    return f"沒有找到適合 {url} 的 Adapter，無法執行 {action}"
                return await adapter.execute(self._page, action, **kwargs)
            except Exception as e:
                return f"執行 {action} 失敗：{e}"
        return self._run(_exec())

    def get_current_url(self) -> str:
        if self._page:
            return self._page.url
        return ""

    def close(self):
        async def _close():
            if self._page:
                await self._page.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        self._run(_close())
        self._page = None
        self._browser = None
        self._playwright = None
