"""
Planner Node：接收使用者任務，用 Groq 分析並制定執行計劃。
"""
import json
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from config import GROQ_API_KEY, GROQ_MODEL_MAIN

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_MAIN, temperature=0)

_SYSTEM = """你是一個強大的 AI Agent，專門負責網頁爬蟲、資料擷取和瀏覽器自動化。

你擁有以下工具：
【爬蟲/搜尋】
  scrape_page(url, query)         - 爬取並用 AI 萃取網頁資料
  search_web(query, num_results)  - DuckDuckGo 搜尋

【瀏覽器操作】
  navigate_to(url)                - 導航到指定網址
  click_element(description)      - 點擊描述的元素
  type_text(selector, text)       - 在欄位輸入文字
  take_screenshot()               - 截圖分析當前頁面
  scroll_page(direction)          - 滾動頁面 (up/down)
  fill_form(fields_dict)          - 填寫並提交表單

【社群互動】
  like_post()                     - 對當前貼文按讚
  reply_to_post(text)             - 回覆當前貼文
  create_post(text)               - 發佈新貼文
  follow_user()                   - 追蹤當前用戶
  unfollow_user()                 - 取消追蹤
  repost()                        - 轉發當前貼文
  bookmark_post()                 - 收藏當前貼文

【媒體/檔案】
  download_media(url, filename)   - 用 yt-dlp 下載影片/圖片
  save_to_file(content, filename) - 儲存資料到本地
  read_from_file(filepath)        - 讀取本地檔案

分析任務後，以 JSON 格式回覆執行計劃：
{
  "plan": ["步驟1說明", "步驟2說明", ...],
  "output_format": "table|json|yaml|md|csv",
  "needs_browser": true|false,
  "save_path": "reports/filename.md 或 null"
}

只回覆 JSON，不要加其他說明。"""


def planner_node(state: AgentState) -> dict:
    task = state.get("task", "")

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"任務：{task}"),
    ])

    try:
        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        data = json.loads(match.group()) if match else {}
    except Exception:
        data = {}

    return {
        "plan": data.get("plan", [task]),
        "current_step": 0,
        "output_format": data.get("output_format", "md"),
        "save_path": data.get("save_path"),
        "needs_browser": data.get("needs_browser", False),
        "tool_results": [],
        "error": None,
    }
