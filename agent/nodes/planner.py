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

## 工具優先順序

【第一優先：OpenCLI】複用使用者已登入的 Chrome session，支援 40+ 網站
  opencli_list()                           - 先執行這個，確認哪些網站/命令可用
  run_opencli("twitter timeline -f json")  - 執行 opencli 命令爬取或操作網站
  opencli_explore(url)                     - 探索網站 API（無 adapter 時用）
  opencli_status()                         - 診斷 Browser Bridge 連線

  常見用法範例：
    run_opencli("twitter timeline --format json --limit 20")
    run_opencli("bilibili trending --format table")
    run_opencli("zhihu hot --format md")

【第二優先：HTTP 爬蟲】用於公開頁面，不需登入
  scrape_page(url, query)          - 爬取網頁並用 AI 萃取資料
  search_web(query, num_results)   - DuckDuckGo 搜尋

【第三優先：CDP 瀏覽器操作】opencli 無法處理的客製互動
  navigate_to(url)                 - 導航
  click_element(description)       - 點擊
  type_text(selector, text)        - 輸入文字
  take_screenshot()                - 截圖分析
  scroll_page(direction)           - 滾動
  like_post() / reply_to_post(text) / create_post(text)
  follow_user() / repost() / bookmark_post()

【工具型】
  download_media(url, filename)    - yt-dlp 下載影片/圖片
  save_to_file(content, filename)  - 儲存到本地
  read_from_file(filepath)         - 讀取本地檔案

## 決策邏輯
- 涉及已知社群網站 → 先用 opencli_list 確認，再用 run_opencli
- 公開頁面不需登入 → scrape_page 或 search_web
- 需要複雜互動 → CDP 瀏覽器工具

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
