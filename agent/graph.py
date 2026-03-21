"""
LangGraph 核心圖定義。

架構：
  START
    │
    ▼
  planner          ← Groq 分析任務，制定步驟
    │
    ▼
  agent_call       ← LLM + 工具綁定，決定呼叫哪個工具
    │
    ├── (有工具呼叫) ──▶ tool_executor ──▶ agent_call (loop)
    │
    └── (完成) ──▶ reporter ──▶ (可選: save_file) ──▶ END
"""
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.nodes.planner import planner_node
from agent.nodes.reporter import reporter_node
from config import GROQ_API_KEY, GROQ_MODEL_MAIN, OPENCLI_COMMANDS


def build_graph(tools: list):
    """
    動態接收工具清單，建立並回傳編譯好的 LangGraph。

    Args:
        tools: LangChain @tool 裝飾的工具函式清單

    Returns:
        CompiledGraph
    """
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL_MAIN,
        temperature=0,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    # ── Agent Call Node ─────────────────────────────────────
    AGENT_SYSTEM = f"""你是一個強大的 AI Agent，可以使用各種工具完成使用者任務。

## OpenCLI 可用命令（已預載，直接選用，不需呼叫 opencli_list）

{OPENCLI_COMMANDS}

## 工具選擇規則（必須遵守）

【爬取網站資料】
- 直接從上方清單選擇對應的 run_opencli 命令，不需先呼叫 opencli_list
- OpenCLI 直接複用使用者已登入的 Chrome，幾乎不會被反爬蟲擋住
- 只有當上方清單中沒有該網站時，才改用 scrape_page 或 search_web
- 禁止對 Twitter、Bilibili、知乎、小紅書、Reddit 等社群網站使用 scrape_page

【其他規則】
1. 優先使用工具取得真實資料，不要憑空捏造
2. 如果一個工具失敗，嘗試其他方式
3. 取得足夠資料後，直接輸出結果不要再呼叫工具
4. 回覆使用繁體中文

你的目標是高效完成任務，最多執行 10 次工具呼叫。"""

    def agent_call_node(state: AgentState) -> dict:
        messages = state.get("messages", [])
        task = state.get("task", "")

        # 確保系統提示在第一條
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=AGENT_SYSTEM)] + list(messages)

        # 若 messages 中還沒有任務描述，加入
        if len(messages) == 1:
            from langchain_core.messages import HumanMessage
            messages.append(HumanMessage(content=task))

        response = llm.invoke(messages)
        return {"messages": [response]}

    # ── Routing：有工具呼叫 → tool_executor；否則 → reporter ──
    def should_continue(state: AgentState) -> Literal["tools", "reporter"]:
        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "reporter"

    # ── Tool Result Collector ───────────────────────────────
    def collect_results(state: AgentState) -> dict:
        """把最新的工具回傳結果收進 tool_results"""
        messages = state.get("messages", [])
        tool_results = list(state.get("tool_results", []))

        # 找最後一批 ToolMessage
        from langchain_core.messages import ToolMessage
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                tool_results.append({
                    "step": msg.name,
                    "output": msg.content,
                })
            else:
                break

        return {"tool_results": tool_results}

    # ── Save File Node ──────────────────────────────────────
    def save_file_node(state: AgentState) -> dict:
        save_path = state.get("save_path")
        final_output = state.get("final_output", "")
        if not save_path or not final_output:
            return {}

        from tools.file_manager import save_to_file_direct
        result = save_to_file_direct(final_output, save_path)
        return {"tool_results": state.get("tool_results", []) + [{"step": "save_file", "output": result}]}

    def should_save(state: AgentState) -> Literal["save", "end"]:
        return "save" if state.get("save_path") else "end"

    # ── Build Graph ─────────────────────────────────────────
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("agent", agent_call_node)
    graph.add_node("tools", tool_node)
    graph.add_node("collect", collect_results)
    graph.add_node("reporter", reporter_node)
    graph.add_node("save_file", save_file_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "reporter": "reporter",
    })
    graph.add_edge("tools", "collect")
    graph.add_edge("collect", "agent")
    graph.add_conditional_edges("reporter", should_save, {
        "save": "save_file",
        "end": END,
    })
    graph.add_edge("save_file", END)

    return graph.compile()


# ── 單例：延遲載入（等工具模組都準備好後再 import）─────────────
_compiled_graph = None


def get_graph():
    """回傳已編譯的圖（懶載入）"""
    global _compiled_graph
    if _compiled_graph is None:
        # ── 主要工具（OpenCLI：複用 Chrome session）───────────
        from tools.opencli import run_opencli, opencli_list, opencli_explore, opencli_status

        # ── 補充工具（OpenCLI 沒有 adapter 時的後備）─────────
        from tools.scraper import scrape_page          # 純 HTTP 爬蟲 + Groq 萃取
        from tools.search import search_web            # DuckDuckGo 搜尋

        # ── 檔案工具 ──────────────────────────────────────────
        from tools.file_manager import save_to_file, read_from_file

        # ── 媒體下載 ──────────────────────────────────────────
        from tools.media import download_media

        # ── 瀏覽器客製操作（CDP，需 Chrome 開啟除錯 port）────
        from tools.browser_actions import (
            navigate_to, click_element, type_text,
            take_screenshot, scroll_page, fill_form,
        )
        from tools.social_actions import (
            like_post, reply_to_post, create_post,
            follow_user, unfollow_user, repost, bookmark_post,
        )

        all_tools = [
            # OpenCLI（優先）
            run_opencli, opencli_list, opencli_explore, opencli_status,
            # 搜尋 / 爬蟲（後備）
            scrape_page, search_web,
            # 檔案
            save_to_file, read_from_file,
            # 媒體
            download_media,
            # 瀏覽器客製操作（CDP）
            navigate_to, click_element, type_text,
            take_screenshot, scroll_page, fill_form,
            like_post, reply_to_post, create_post,
            follow_user, unfollow_user, repost, bookmark_post,
        ]
        _compiled_graph = build_graph(all_tools)
    return _compiled_graph


async def run_task(task: str, output_format: str = "md", save_path: str = None) -> str:
    """
    執行一個任務並回傳最終輸出。

    Args:
        task: 自然語言任務描述
        output_format: 輸出格式 table/json/yaml/md/csv
        save_path: 儲存路徑（None = 不存檔）

    Returns:
        最終報告字串
    """
    graph = get_graph()

    initial_state: AgentState = {
        "messages": [],
        "task": task,
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "final_output": "",
        "output_format": output_format,
        "save_path": save_path,
        "error": None,
        "needs_browser": False,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state.get("final_output", "（無輸出）")
