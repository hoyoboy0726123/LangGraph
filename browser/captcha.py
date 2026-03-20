"""
Captcha Handler：當偵測到驗證碼時通知使用者，並等待手動解決。
"""
import asyncio
import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from config import GROQ_API_KEY, GROQ_MODEL_FAST

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_FAST, temperature=0)

CAPTCHA_KEYWORDS = [
    "captcha", "recaptcha", "hcaptcha", "verify you are human",
    "i'm not a robot", "人機驗證", "驗證碼", "安全驗證",
]


async def detect_captcha(page) -> bool:
    """偵測當前頁面是否有驗證碼"""
    try:
        screenshot_bytes = await page.screenshot(type="png")
        b64 = base64.b64encode(screenshot_bytes).decode()
        response = _llm.invoke([
            HumanMessage(content=[
                {"type": "text", "text": "這個截圖是否顯示驗證碼（CAPTCHA）？只回覆 yes 或 no。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ])
        ])
        return "yes" in response.content.lower()
    except Exception:
        return False


async def wait_for_captcha_solved(page, timeout: int = 120) -> bool:
    """
    等待使用者手動解決驗證碼。
    每 3 秒檢查一次，最多等待 timeout 秒。
    """
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(3)
        elapsed += 3
        if not await detect_captcha(page):
            return True
    return False


async def handle_captcha_if_present(page, notify_callback=None) -> bool:
    """
    若有驗證碼，通知使用者並等待解決。

    Args:
        page: Playwright page
        notify_callback: 可選的通知函式 (message: str) -> None

    Returns:
        True 表示驗證碼已解決或不存在，False 表示逾時未解決
    """
    if not await detect_captcha(page):
        return True

    msg = "⚠️ 偵測到驗證碼！請在瀏覽器中手動完成驗證（等待最多 2 分鐘）..."
    print(msg)
    if notify_callback:
        notify_callback(msg)

    solved = await wait_for_captcha_solved(page)
    if solved:
        success_msg = "✅ 驗證碼已解決，繼續執行任務..."
        print(success_msg)
        if notify_callback:
            notify_callback(success_msg)
    else:
        fail_msg = "❌ 等待驗證碼超時，請重新嘗試。"
        print(fail_msg)
        if notify_callback:
            notify_callback(fail_msg)

    return solved
