"""
Browser Actions Tools：透過 Playwright 控制瀏覽器。
所有操作都會先嘗試連接使用者現有的 Chrome，若連接失敗則啟動新的。
"""
from langchain_core.tools import tool
from browser.controller import get_controller


@tool
def navigate_to(url: str) -> str:
    """
    在瀏覽器中導航到指定網址。

    Args:
        url: 目標網址

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.navigate(url)


@tool
def click_element(description: str) -> str:
    """
    點擊瀏覽器中符合描述的元素（用自然語言描述按鈕/連結/元素）。

    Args:
        description: 元素描述（例如：「購買按鈕」、「登入連結」、「搜尋框」）

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.click(description)


@tool
def type_text(selector: str, text: str) -> str:
    """
    在指定的輸入框中輸入文字。

    Args:
        selector: 輸入框描述或 CSS selector（例如：「搜尋框」或「input[name='q']」）
        text: 要輸入的文字

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.type_text(selector, text)


@tool
def take_screenshot() -> str:
    """
    截取當前瀏覽器頁面截圖，分析頁面內容。

    Returns:
        頁面描述（由 AI 分析截圖後的文字說明）
    """
    ctrl = get_controller()
    return ctrl.screenshot_and_describe()


@tool
def scroll_page(direction: str = "down") -> str:
    """
    滾動當前頁面。

    Args:
        direction: 滾動方向 「up」 或 「down」

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.scroll(direction)


@tool
def fill_form(fields: str) -> str:
    """
    填寫並提交表單。

    Args:
        fields: JSON 格式的表單欄位（例如：'{"username": "myuser", "password": "mypass"}'）

    Returns:
        操作結果訊息
    """
    import json
    try:
        fields_dict = json.loads(fields)
    except Exception:
        return f"fields 格式錯誤，請提供合法 JSON 字串：{fields}"

    ctrl = get_controller()
    return ctrl.fill_form(fields_dict)
