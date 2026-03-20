"""
Scraper Tool：爬取網頁內容，用 Groq 萃取使用者需要的資訊。
"""
import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import GROQ_API_KEY, GROQ_MODEL_MAIN

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_MAIN, temperature=0)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}


def _fetch_html(url: str) -> str:
    """取得網頁原始 HTML"""
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _clean_html(html: str, max_chars: int = 8000) -> str:
    """清理 HTML，只保留有意義的文字內容"""
    soup = BeautifulSoup(html, "lxml")

    # 移除不需要的標籤
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # 移除空白行
    lines = [line for line in text.splitlines() if line.strip()]
    clean = "\n".join(lines)

    return clean[:max_chars]


@tool
def scrape_page(url: str, extraction_query: str = "") -> str:
    """
    爬取指定 URL 的網頁內容，並用 AI 萃取你需要的資料。

    Args:
        url: 要爬取的網頁網址
        extraction_query: 描述你想取得的資料（例如：「所有商品名稱和價格」）
                         若留空，則回傳整理後的網頁文字

    Returns:
        萃取結果字串
    """
    try:
        html = _fetch_html(url)
        page_text = _clean_html(html)
    except Exception as e:
        return f"爬取失敗：{e}"

    if not extraction_query:
        return f"【{url}】\n\n{page_text[:3000]}"

    # 用 Groq 萃取特定資訊
    prompt = (
        f"以下是網頁內容（來自 {url}）：\n\n"
        f"{page_text}\n\n"
        f"請萃取以下資訊：{extraction_query}\n\n"
        "以結構化方式回覆，若找不到相關資訊請說明。"
    )

    response = _llm.invoke([
        SystemMessage(content="你是資料萃取專家，從網頁內容中精確提取使用者需要的資訊。"),
        HumanMessage(content=prompt),
    ])

    return response.content
