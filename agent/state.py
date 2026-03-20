from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # 對話歷史（自動 append，不覆蓋）
    messages: Annotated[list, add_messages]
    # 原始任務描述
    task: str
    # 規劃拆分後的步驟清單
    plan: list[str]
    # 目前執行到第幾步
    current_step: int
    # 每個工具呼叫的結果
    tool_results: list[dict]
    # 最終整理好的輸出
    final_output: str
    # 輸出格式：table / json / yaml / md / csv
    output_format: str
    # 若需儲存到本地，指定相對路徑（None = 不存檔）
    save_path: Optional[str]
    # 任何執行錯誤訊息
    error: Optional[str]
    # 是否需要瀏覽器
    needs_browser: bool
