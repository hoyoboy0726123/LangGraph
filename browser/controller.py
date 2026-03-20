"""
Browser Controller：透過 Chrome CDP 執行瀏覽器操作。

用途：
  處理 OpenCLI 尚未支援的客製化操作，例如：
  - 點擊特定元素
  - 填寫表單
  - 截圖分析
  - 滾動頁面

前提：使用者必須已開啟 Chrome 並啟用遠端除錯：
  macOS:   open -a 'Google Chrome' --args --remote-debugging-port=9222
  Windows: chrome.exe --remote-debugging-port=9222
  Linux:   google-chrome --remote-debugging-port=9222

注意：不會自動啟動新瀏覽器。若 Chrome 未開啟會直接報錯，
      避免建立沒有登入狀態的孤立瀏覽器。
"""
import asyncio
import base64
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL_FAST, CHROME_CDP_URL

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_FAST, temperature=0)

_controller: Optional["BrowserController"] = None

_CHROME_NOT_RUNNING = (
    "Chrome 未開啟遠端除錯模式。\n"
    "請用以下指令重新啟動 Chrome：\n\n"
    "  macOS:   open -a 'Google Chrome' --args --remote-debugging-port=9222\n"
    "  Windows: chrome.exe --remote-debugging-port=9222\n"
    "  Linux:   google-chrome --remote-debugging-port=9222\n\n"
    "啟動後把要操作的分頁開好，再重新執行任務。"
)


def get_controller() -> "BrowserController":
    global _controller
    if _controller is None:
        _controller = BrowserController()
    return _controller


class BrowserController:
    """透過 Playwright CDP 連接使用者現有的 Chrome"""

    def __init__(self):
        self._page = None
        self._playwright = None
        self._browser = None

    def _run(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    async def _ensure_page(self):
        """連接使用者現有的 Chrome（若已連接則直接複用）"""
        if self._page and not self._page.is_closed():
            return

        from playwright.async_api import async_playwright
        from browser.session import is_chrome_running

        if not await is_chrome_running():
            raise RuntimeError(_CHROME_NOT_RUNNING)

        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(CHROME_CDP_URL)
        except Exception as e:
            await self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                f"無法連接 Chrome（{CHROME_CDP_URL}）：{e}\n\n{_CHROME_NOT_RUNNING}"
            )

        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError("Chrome 已連接但沒有開啟的分頁。請在 Chrome 中開啟目標網頁。")

        pages = contexts[0].pages
        self._page = pages[-1] if pages else await contexts[0].new_page()

    def navigate(self, url: str) -> str:
        async def _go():
            await self._ensure_page()
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return f"已導航到：{url}（標題：{await self._page.title()}）"
        try:
            return self._run(_go())
        except Exception as e:
            return str(e)

    def click(self, description: str) -> str:
        async def _click():
            await self._ensure_page()
            # 截圖讓 Groq Vision 識別元素
            b64 = base64.b64encode(await self._page.screenshot(type="png")).decode()
            resp = _llm.invoke([HumanMessage(content=[
                {"type": "text", "text": (
                    f"找出符合「{description}」的元素，"
                    "回覆其 CSS selector，只回覆 selector 本身。"
                )},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ])])
            selector = resp.content.strip()
            try:
                await self._page.click(selector, timeout=8000)
                return f"已點擊：{description}"
            except Exception:
                # fallback：直接用文字點擊
                await self._page.get_by_text(description).first.click(timeout=5000)
                return f"已點擊文字「{description}」"
        try:
            return self._run(_click())
        except Exception as e:
            return f"點擊失敗：{e}"

    def type_text(self, selector: str, text: str) -> str:
        async def _type():
            await self._ensure_page()
            try:
                await self._page.fill(selector, text, timeout=8000)
            except Exception:
                await self._page.get_by_placeholder(selector).fill(text)
            return f"已在「{selector}」輸入文字"
        try:
            return self._run(_type())
        except Exception as e:
            return f"輸入失敗：{e}"

    def screenshot_and_describe(self) -> str:
        async def _shot():
            await self._ensure_page()
            img = await self._page.screenshot(type="png", full_page=False)
            b64 = base64.b64encode(img).decode()

            from config import OUTPUT_BASE_PATH
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = OUTPUT_BASE_PATH / f"screenshot_{ts}.png"
            path.write_bytes(img)

            resp = _llm.invoke([HumanMessage(content=[
                {"type": "text", "text": "描述這個網頁截圖，重點說明可互動的元素（按鈕、連結、表單等）。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ])])
            return f"截圖已儲存：{path}\n\n{resp.content}"
        try:
            return self._run(_shot())
        except Exception as e:
            return f"截圖失敗：{e}"

    def scroll(self, direction: str = "down") -> str:
        async def _scroll():
            await self._ensure_page()
            key = "PageUp" if direction == "up" else "PageDown"
            await self._page.keyboard.press(key)
            return f"已向 {direction} 滾動頁面"
        try:
            return self._run(_scroll())
        except Exception as e:
            return f"滾動失敗：{e}"

    def fill_form(self, fields: dict) -> str:
        async def _fill():
            await self._ensure_page()
            results = []
            for field, value in fields.items():
                try:
                    await self._page.fill(
                        f"[name='{field}'], [id='{field}'], [placeholder*='{field}']",
                        str(value),
                    )
                    results.append(f"✓ {field}")
                except Exception as e:
                    results.append(f"✗ {field}：{e}")
            return "表單填寫結果：\n" + "\n".join(results)
        try:
            return self._run(_fill())
        except Exception as e:
            return f"表單填寫失敗：{e}"

    def execute_action(self, action: str, **kwargs) -> str:
        """透過 Adapter 系統執行社群操作"""
        async def _exec():
            await self._ensure_page()
            from adapters.loader import get_adapter_for_url
            url = self._page.url
            adapter = get_adapter_for_url(url)
            if not adapter:
                return (
                    f"找不到 {url} 的 Adapter。\n"
                    "建議改用 run_opencli 工具，或在 adapters/custom/ 新增 YAML 設定。"
                )
            return await adapter.execute(self._page, action, **kwargs)
        try:
            return self._run(_exec())
        except Exception as e:
            return str(e)

    def get_current_url(self) -> str:
        return self._page.url if self._page else ""

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
