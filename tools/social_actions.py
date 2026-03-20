"""
Social Actions Tools：社群媒體互動（按讚、留言、發文、追蹤、轉發、收藏）。
透過 Adapter 系統取得對應網站的選擇器，再由 BrowserController 執行。
"""
from langchain_core.tools import tool
from browser.controller import get_controller


@tool
def like_post() -> str:
    """
    對當前頁面的貼文/推文/影片按讚。

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("like")


@tool
def reply_to_post(text: str) -> str:
    """
    回覆當前頁面的貼文或留言。

    Args:
        text: 回覆內容

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("reply", text=text)


@tool
def create_post(text: str) -> str:
    """
    在當前網站發佈新貼文、推文或文章。

    Args:
        text: 貼文內容

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("post", text=text)


@tool
def follow_user() -> str:
    """
    追蹤當前頁面的用戶/頻道/帳號。

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("follow")


@tool
def unfollow_user() -> str:
    """
    取消追蹤當前頁面的用戶/頻道/帳號。

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("unfollow")


@tool
def repost() -> str:
    """
    轉發/轉推/分享當前頁面的貼文。

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("repost")


@tool
def bookmark_post() -> str:
    """
    收藏/書籤當前頁面的貼文或文章。

    Returns:
        操作結果訊息
    """
    ctrl = get_controller()
    return ctrl.execute_action("bookmark")
