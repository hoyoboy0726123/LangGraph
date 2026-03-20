#!/usr/bin/env python3
"""
LangGraph Agent CLI 入口點。

模式：
  python main.py             → 互動式 CLI（Rich REPL）
  python main.py --api       → 啟動 FastAPI 後端（供 Next.js 使用）
  python main.py --telegram  → 啟動 Telegram Bot
  python main.py --all       → 同時啟動 API + Telegram Bot

快速任務：
  python main.py "爬取台積電股價"
  python main.py "搜尋 LangGraph 教學" --format table
  python main.py "爬取 HN 熱門" --format json --save reports/hn.json
"""
import asyncio
import sys
import argparse
import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live
from rich import print as rprint

console = Console()


# ── 啟動訊息 ────────────────────────────────────────────────
def print_banner():
    banner = Panel(
        "[bold cyan]LangGraph Agent[/bold cyan]\n"
        "[dim]Powered by Groq + LangGraph[/dim]\n\n"
        "輸入任務描述，Agent 會自動規劃並執行。\n"
        "[dim]輸入 /help 查看指令 | Ctrl+C 退出[/dim]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(banner)


# ── CLI REPL ─────────────────────────────────────────────────
async def run_cli():
    """互動式 CLI 模式"""
    from config import check_config
    from agent.graph import run_task

    missing = check_config()
    if missing:
        console.print(f"[yellow]⚠ 以下設定未填寫：{', '.join(missing)}[/yellow]")
        console.print("[dim]請複製 .env.example 為 .env 並填入設定[/dim]\n")

    print_banner()

    output_format = "md"
    save_path = None

    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]你[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再見！[/dim]")
            break

        if not user_input.strip():
            continue

        # ── 內部指令 ────────────────────────────────────────
        if user_input.startswith("/"):
            parts = user_input.split()
            cmd = parts[0].lower()

            if cmd == "/help":
                console.print(Panel(
                    "/format md|table|json|yaml|csv  — 設定輸出格式\n"
                    "/save <路徑>                     — 自動存檔路徑\n"
                    "/nosave                          — 取消自動存檔\n"
                    "/status                          — 查看系統狀態\n"
                    "/clear                           — 清除畫面\n"
                    "/exit                            — 退出",
                    title="指令說明", border_style="dim"
                ))

            elif cmd == "/format" and len(parts) > 1:
                output_format = parts[1]
                console.print(f"[green]輸出格式已設為：{output_format}[/green]")

            elif cmd == "/save" and len(parts) > 1:
                save_path = parts[1]
                console.print(f"[green]自動存檔路徑：{save_path}[/green]")

            elif cmd == "/nosave":
                save_path = None
                console.print("[green]已取消自動存檔[/green]")

            elif cmd == "/status":
                from scheduler.manager import list_tasks
                tasks = list_tasks()
                console.print(f"[cyan]定時任務：{len(tasks)} 個[/cyan]")

            elif cmd == "/clear":
                console.clear()

            elif cmd in ("/exit", "/quit", "/q"):
                console.print("[dim]再見！[/dim]")
                break

            else:
                console.print(f"[red]未知指令：{cmd}，輸入 /help 查看說明[/red]")

            continue

        # ── 執行任務 ─────────────────────────────────────────
        console.print()
        with Live(Spinner("dots", text=" Agent 思考中..."), console=console, transient=True):
            result = await run_task(user_input, output_format, save_path)

        console.print(Panel(
            Markdown(result) if output_format == "md" else result,
            title="[bold green]Agent[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))


# ── Single Task Mode ─────────────────────────────────────────
async def run_single_task(task: str, fmt: str, save: str | None):
    from agent.graph import run_task
    with Live(Spinner("dots", text=" 執行中..."), console=console, transient=True):
        result = await run_task(task, fmt, save)

    if fmt == "md":
        console.print(Markdown(result))
    else:
        console.print(result)


# ── API Server ───────────────────────────────────────────────
def run_api(host="0.0.0.0", port=8000):
    import uvicorn
    console.print(f"[green]✅ FastAPI 後端啟動中 → http://{host}:{port}[/green]")
    uvicorn.run("api_server:app", host=host, port=port, reload=True)


# ── Telegram Bot ─────────────────────────────────────────────
async def run_telegram():
    from telegram_bot.bot import run_bot
    console.print("[green]✅ Telegram Bot 啟動中...[/green]")
    await run_bot()


# ── All-in-one ───────────────────────────────────────────────
async def run_all():
    import uvicorn
    config = uvicorn.Config("api_server:app", host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        run_telegram(),
    )


# ── Entry Point ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LangGraph Agent")
    parser.add_argument("task", nargs="?", help="直接執行單一任務")
    parser.add_argument("--format", "-f", default="md",
                        choices=["md", "table", "json", "yaml", "csv"],
                        help="輸出格式（預設：md）")
    parser.add_argument("--save", "-s", help="存檔路徑")
    parser.add_argument("--api", action="store_true", help="啟動 FastAPI 後端")
    parser.add_argument("--telegram", action="store_true", help="啟動 Telegram Bot")
    parser.add_argument("--all", action="store_true", help="啟動 API + Telegram")

    args = parser.parse_args()

    if args.api:
        run_api()
    elif args.telegram:
        asyncio.run(run_telegram())
    elif getattr(args, "all"):
        asyncio.run(run_all())
    elif args.task:
        asyncio.run(run_single_task(args.task, args.format, args.save))
    else:
        asyncio.run(run_cli())


if __name__ == "__main__":
    main()
