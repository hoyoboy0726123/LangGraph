"""
Reporter Node：整理所有工具執行結果，產出最終報告。
"""
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from config import GROQ_API_KEY, GROQ_MODEL_MAIN

_llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_MAIN, temperature=0)

_SYSTEM = """你是報告整理專家。根據工具執行結果，整理出清晰的最終報告。

格式要求：
- table：使用 Markdown 表格
- json：輸出合法 JSON
- yaml：輸出合法 YAML
- md：Markdown 格式報告（含標題、段落、清單）
- csv：CSV 格式（第一行為欄位名稱）

報告應包含：
1. 執行摘要
2. 詳細資料
3. 完成時間

只輸出報告內容，不要加「這是報告：」之類的說明。"""


def reporter_node(state: AgentState) -> dict:
    task = state.get("task", "")
    tool_results = state.get("tool_results", [])
    output_format = state.get("output_format", "md")

    results_text = "\n\n".join(
        f"步驟 {i+1}：{r.get('step', '')}\n結果：{r.get('output', '')}"
        for i, r in enumerate(tool_results)
    ) if tool_results else "（無執行結果）"

    prompt = (
        f"原始任務：{task}\n\n"
        f"執行結果：\n{results_text}\n\n"
        f"請以 {output_format} 格式整理報告。"
    )

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return {"final_output": response.content}
