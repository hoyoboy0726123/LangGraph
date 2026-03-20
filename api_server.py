"""
FastAPI 後端：提供 REST + SSE API 給 Next.js 前端使用。

啟動方式：
  uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import OUTPUT_BASE_PATH, ALLOWED_PATHS, check_config
from scheduler.manager import start as sched_start, shutdown as sched_shutdown

app = FastAPI(
    title="LangGraph Agent API",
    description="AI Agent with LangGraph + Groq",
    version="1.0.0",
)

# CORS：允許本地 Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Lifespan ────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await sched_start()
    print("✅ Scheduler 已啟動")


@app.on_event("shutdown")
async def shutdown():
    await sched_shutdown()


# ── Models ──────────────────────────────────────────────────
class RunTaskRequest(BaseModel):
    task: str
    output_format: str = "md"
    save_path: Optional[str] = None
    stream: bool = True


class ScheduleTaskRequest(BaseModel):
    name: str
    task_prompt: str
    output_format: str = "md"
    save_path: Optional[str] = None
    schedule_type: str = "cron"     # cron | interval | once
    schedule_expr: str = "0 9 * * *"


# ── Chat / Run ───────────────────────────────────────────────
async def _stream_task(task: str, output_format: str, save_path: Optional[str]) -> AsyncGenerator[str, None]:
    """串流執行任務，回傳 SSE 事件"""

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield sse("status", {"message": "分析任務中...", "step": "planner"})
    await asyncio.sleep(0.1)

    try:
        # 攔截 LangGraph 的中間步驟
        from agent.graph import get_graph, AgentState
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

        final_output = ""
        async for chunk in graph.astream(initial_state, stream_mode="updates"):
            for node_name, state_update in chunk.items():
                if node_name == "planner":
                    plan = state_update.get("plan", [])
                    yield sse("plan", {"plan": plan, "step": "planner"})

                elif node_name == "agent":
                    messages = state_update.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "content") and msg.content:
                            yield sse("thinking", {
                                "message": str(msg.content)[:200],
                                "step": "agent",
                            })
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                yield sse("tool_call", {
                                    "tool": tc.get("name", ""),
                                    "args": str(tc.get("args", {}))[:100],
                                    "step": "tool",
                                })

                elif node_name == "tools":
                    yield sse("status", {"message": "工具執行中...", "step": "tool"})

                elif node_name == "reporter":
                    output = state_update.get("final_output", "")
                    if output:
                        final_output = output
                        yield sse("result", {"output": output, "format": output_format})

                elif node_name == "save_file":
                    yield sse("status", {"message": "儲存檔案中...", "step": "save"})

        yield sse("done", {"output": final_output, "format": output_format})

    except Exception as e:
        yield sse("error", {"message": str(e)})


@app.post("/run")
async def run_task(req: RunTaskRequest):
    """執行任務，支援 SSE 串流回應"""
    if req.stream:
        return StreamingResponse(
            _stream_task(req.task, req.output_format, req.save_path),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        from agent.graph import run_task as _run
        result = await _run(req.task, req.output_format, req.save_path)
        return {"output": result, "format": req.output_format}


# ── Scheduled Tasks ──────────────────────────────────────────
@app.get("/tasks")
async def get_tasks():
    from scheduler.manager import list_tasks
    return {"tasks": list_tasks()}


@app.post("/tasks")
async def create_task(req: ScheduleTaskRequest):
    from scheduler.manager import add_task
    try:
        task = add_task(
            name=req.name,
            task_prompt=req.task_prompt,
            output_format=req.output_format,
            save_path=req.save_path,
            schedule_type=req.schedule_type,
            schedule_expr=req.schedule_expr,
        )
        from dataclasses import asdict
        return {"task": asdict(task)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    from scheduler.manager import remove_task
    if remove_task(task_id):
        return {"message": f"任務 {task_id} 已刪除"}
    raise HTTPException(status_code=404, detail=f"找不到任務 {task_id}")


# ── Files ────────────────────────────────────────────────────
@app.get("/files")
async def list_files(path: str = ""):
    """列出輸出目錄中的檔案"""
    base = OUTPUT_BASE_PATH / path if path else OUTPUT_BASE_PATH
    if not base.exists():
        return {"files": [], "path": str(path)}

    files = []
    for item in sorted(base.iterdir()):
        stat = item.stat()
        files.append({
            "name": item.name,
            "path": str(item.relative_to(OUTPUT_BASE_PATH)),
            "is_dir": item.is_dir(),
            "size": stat.st_size if item.is_file() else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return {"files": files, "path": str(path)}


@app.get("/files/content")
async def read_file(path: str):
    """讀取檔案內容"""
    file_path = (OUTPUT_BASE_PATH / path).resolve()

    # 安全檢查
    allowed = any(
        str(file_path).startswith(str(p.resolve()))
        for p in ALLOWED_PATHS
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="拒絕存取：路徑不在允許清單中")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="檔案不存在")

    try:
        content = file_path.read_text(encoding="utf-8")
        return {"content": content, "path": path, "name": file_path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    missing = check_config()
    return {
        "status": "ok",
        "warnings": [f"{k} 未設定" for k in missing],
        "version": "1.0.0",
    }
