"""
Search Tool：使用 DuckDuckGo 搜尋網路（免費，不需要 API Key）。
"""
from langchain_core.tools import tool


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    使用 DuckDuckGo 搜尋網路，回傳搜尋結果摘要。

    Args:
        query: 搜尋關鍵字
        num_results: 回傳結果數量（預設 5）

    Returns:
        搜尋結果字串（含標題、網址、摘要）
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append(
                    f"標題：{r.get('title', '')}\n"
                    f"網址：{r.get('href', '')}\n"
                    f"摘要：{r.get('body', '')}\n"
                )

        if not results:
            return f"搜尋「{query}」沒有找到結果。"

        return f"搜尋「{query}」找到 {len(results)} 筆結果：\n\n" + "\n---\n".join(results)

    except Exception as e:
        return f"搜尋失敗：{e}"
