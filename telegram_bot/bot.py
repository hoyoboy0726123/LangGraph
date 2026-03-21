"""
Telegram Bot：讓使用者透過 Telegram 發派任務給 LangGraph agent。

功能：
  /run <任務>                  - 執行一次性任務
  /schedule <任務>             - 互動式設定定時任務
  /tasks                       - 列出所有定時任務
  /deltask <id>                - 刪除定時任務
  /status                      - 查看 Bot 狀態
  /help                        - 說明

  Pipeline 功能：
  /pipeline run <yaml路徑>     - 立即執行 pipeline
  /pipeline runs               - 列出最近 pipeline 執行紀錄
  /pipeline status <run_id>    - 查看特定 run 狀態
  /pipeline log <run_id>       - 顯示最近 50 行 log
  /pipeline schedule <yaml路徑> <cron表達式> - 排程定期執行 pipeline

  Inline keyboard（系統自動送出）：
  🔄 重試此步驟 / ⏩ 跳過此步驟 / 🛑 中止
"""
import asyncio
import html
from pathlib import Path
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS

# 對話狀態（ConversationHandler 用）
AWAIT_SCHEDULE_TASK, AWAIT_SCHEDULE_TIME = range(2)


def _check_auth(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return uid in TELEGRAM_ALLOWED_USER_IDS


async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 無授權存取。")
        return
    await update.message.reply_text(
        "👋 你好！我是你的 AI Agent Bot。\n\n"
        "發送 /help 查看指令說明。"
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return
    text = (
        "📖 <b>指令說明</b>\n\n"
        "/run &lt;任務描述&gt; — 立即執行任務\n"
        "例：/run 爬取台股大盤行情\n\n"
        "/schedule — 設定定時任務\n"
        "/tasks — 查看定時任務清單\n"
        "/deltask &lt;id&gt; — 刪除定時任務\n\n"
        "/status — 查看系統狀態\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔁 <b>Pipeline 指令</b>\n\n"
        "/pipeline run &lt;yaml路徑&gt; — 立即執行 pipeline\n"
        "/pipeline runs — 最近執行紀錄\n"
        "/pipeline status &lt;run_id&gt; — 查看狀態\n"
        "/pipeline log &lt;run_id&gt; — 查看 log\n"
        "/pipeline schedule &lt;yaml&gt; &lt;cron&gt; — 排程執行\n\n"
        "/help — 顯示此說明"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def run_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        await update.message.reply_text("⛔ 無授權存取。")
        return

    task = " ".join(ctx.args) if ctx.args else ""
    if not task:
        await update.message.reply_text("請提供任務描述，例：\n/run 爬取台股加權指數")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await update.message.reply_text(f"⚙️ 執行中：{task[:50]}...")

    try:
        from agent.graph import run_task
        result = await run_task(task, output_format="md")

        # Telegram 訊息長度限制 4096 字元
        if len(result) > 4000:
            chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
            await msg.edit_text(f"✅ 完成（共 {len(chunks)} 則訊息）")
            for chunk in chunks:
                await update.message.reply_text(
                    f"```\n{chunk}\n```",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
        else:
            await msg.edit_text(
                f"✅ <b>任務完成</b>\n\n{html.escape(result)}",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        await msg.edit_text(f"❌ 執行失敗：{html.escape(str(e))}", parse_mode=ParseMode.HTML)


async def tasks_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return

    from scheduler.manager import list_tasks
    tasks = list_tasks()

    if not tasks:
        await update.message.reply_text("目前沒有定時任務。\n使用 /schedule 新增。")
        return

    lines = ["📋 <b>定時任務清單</b>\n"]
    for t in tasks:
        lines.append(
            f"🆔 <code>{t['id']}</code> <b>{html.escape(t['name'])}</b>\n"
            f"   📌 {html.escape(t['task_prompt'][:50])}\n"
            f"   ⏰ {t['schedule_type']}: {html.escape(t['schedule_expr'])}\n"
            f"   ▶️ 下次：{t.get('next_run', 'N/A')[:16]}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def deltask_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return
    if not ctx.args:
        await update.message.reply_text("請提供任務 ID，例：/deltask abc12345")
        return

    from scheduler.manager import remove_task
    task_id = ctx.args[0]
    if remove_task(task_id):
        await update.message.reply_text(f"✅ 已刪除任務 {task_id}")
    else:
        await update.message.reply_text(f"❌ 找不到任務 {task_id}")


async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return
    from scheduler.manager import list_tasks
    task_count = len(list_tasks())
    await update.message.reply_text(
        f"✅ <b>系統狀態</b>\n\n"
        f"🤖 Agent：運行中\n"
        f"📅 定時任務：{task_count} 個\n",
        parse_mode=ParseMode.HTML,
    )


async def pipeline_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /pipeline <subcommand> [args]
    Subcommands: run | runs | status | log | schedule
    """
    if not _check_auth(update):
        await update.message.reply_text("⛔ 無授權存取。")
        return

    args = ctx.args or []
    if not args:
        await update.message.reply_text(
            "📖 <b>Pipeline 指令說明</b>\n\n"
            "/pipeline run &lt;yaml路徑&gt; — 立即執行\n"
            "/pipeline runs — 最近 10 筆執行紀錄\n"
            "/pipeline status &lt;run_id&gt; — 執行狀態\n"
            "/pipeline log &lt;run_id&gt; — 最近 50 行 log\n"
            "/pipeline schedule &lt;yaml路徑&gt; &lt;cron&gt; — 排程執行",
            parse_mode=ParseMode.HTML,
        )
        return

    sub = args[0].lower()

    # ── /pipeline run <yaml_path> ─────────────────────────────
    if sub == "run":
        if len(args) < 2:
            await update.message.reply_text("請提供 YAML 路徑，例：/pipeline run /data/pipelines/daily.yaml")
            return

        yaml_path = args[1]
        if not Path(yaml_path).exists():
            await update.message.reply_text(f"❌ 找不到檔案：{yaml_path}")
            return

        try:
            from pipeline.models import PipelineConfig
            config = PipelineConfig.from_yaml(yaml_path)
        except Exception as e:
            await update.message.reply_text(f"❌ YAML 格式錯誤：{html.escape(str(e))}", parse_mode=ParseMode.HTML)
            return

        msg = await update.message.reply_text(
            f"⚙️ 啟動 Pipeline：<b>{html.escape(config.name)}</b>\n"
            f"共 {len(config.steps)} 步驟，將在完成後通知你。",
            parse_mode=ParseMode.HTML,
        )

        chat_id = update.effective_chat.id
        asyncio.create_task(_run_pipeline_bg(config.model_dump(), chat_id, msg))

    # ── /pipeline runs ────────────────────────────────────────
    elif sub == "runs":
        from pipeline.store import get_store
        runs = get_store().list_recent(10)
        if not runs:
            await update.message.reply_text("尚無 pipeline 執行紀錄。")
            return

        status_icon = {
            "running": "🔄",
            "awaiting_human": "⏳",
            "completed": "✅",
            "failed": "❌",
            "aborted": "🛑",
        }
        lines = ["📋 <b>最近 Pipeline 執行紀錄</b>\n"]
        for r in runs:
            icon = status_icon.get(r.status, "❓")
            ts = r.started_at[:16]
            lines.append(
                f"{icon} <code>{r.run_id}</code> <b>{html.escape(r.pipeline_name)}</b>\n"
                f"   {ts}  步驟 {r.current_step}/{len(r.config_dict.get('steps', []))}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    # ── /pipeline status <run_id> ─────────────────────────────
    elif sub == "status":
        if len(args) < 2:
            await update.message.reply_text("請提供 run_id，例：/pipeline status abc123")
            return

        from pipeline.store import get_store
        run = get_store().load(args[1])
        if not run:
            await update.message.reply_text(f"❌ 找不到 run：{args[1]}")
            return

        from pipeline.models import PipelineConfig
        config = PipelineConfig.from_dict(run.config_dict)
        status_icon = {"running": "🔄", "awaiting_human": "⏳", "completed": "✅",
                       "failed": "❌", "aborted": "🛑"}
        icon = status_icon.get(run.status, "❓")

        lines = [
            f"{icon} <b>{html.escape(run.pipeline_name)}</b>",
            f"ID：<code>{run.run_id}</code>",
            f"狀態：{run.status}",
            f"開始：{run.started_at[:16]}",
            "",
            "<b>步驟：</b>",
        ]
        step_icon = {"ok": "✅", "warning": "⚠️", "failed": "❌"}
        for i, step in enumerate(config.steps):
            if i < len(run.step_results):
                r = run.step_results[i]
                si = step_icon.get(r.validation_status, "❓")
                lines.append(f"  {si} {step.name}  ({r.validation_reason[:50]})")
            elif i == run.current_step and run.status == "running":
                lines.append(f"  🔄 {step.name}  （執行中）")
            else:
                lines.append(f"  ⬜ {step.name}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    # ── /pipeline log <run_id> ────────────────────────────────
    elif sub == "log":
        if len(args) < 2:
            await update.message.reply_text("請提供 run_id，例：/pipeline log abc123")
            return

        from pipeline.store import get_store
        run = get_store().load(args[1])
        if not run:
            await update.message.reply_text(f"❌ 找不到 run：{args[1]}")
            return

        log_path = Path(run.log_path)
        if not log_path.exists():
            await update.message.reply_text(f"❌ Log 檔不存在：{run.log_path}")
            return

        # 取最後 50 行
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-50:])
        if len(tail) > 3800:
            tail = "...\n" + tail[-3800:]
        await update.message.reply_text(
            f"<b>Log（最後 50 行）：</b>\n<pre>{html.escape(tail)}</pre>",
            parse_mode=ParseMode.HTML,
        )

    # ── /pipeline schedule <yaml_path> <cron> ────────────────
    elif sub == "schedule":
        if len(args) < 3:
            await update.message.reply_text(
                "格式：/pipeline schedule &lt;yaml路徑&gt; &lt;cron&gt;\n"
                "例：/pipeline schedule /data/daily.yaml \"0 8 * * *\"",
                parse_mode=ParseMode.HTML,
            )
            return

        yaml_path = args[1]
        cron_expr = " ".join(args[2:])

        if not Path(yaml_path).exists():
            await update.message.reply_text(f"❌ 找不到檔案：{yaml_path}")
            return

        try:
            from pipeline.models import PipelineConfig
            config = PipelineConfig.from_yaml(yaml_path)
            from scheduler.manager import add_pipeline_task
            task = add_pipeline_task(
                name=config.name,
                yaml_path=yaml_path,
                chat_id=update.effective_chat.id,
                schedule_expr=cron_expr,
            )
            await update.message.reply_text(
                f"✅ 已排程 Pipeline：<b>{html.escape(config.name)}</b>\n"
                f"⏰ Cron：<code>{html.escape(cron_expr)}</code>\n"
                f"🆔 任務 ID：<code>{task.id}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ 排程失敗：{html.escape(str(e))}",
                parse_mode=ParseMode.HTML,
            )

    else:
        await update.message.reply_text(f"❓ 未知子命令：{sub}，請輸入 /pipeline 查看說明")


async def _run_pipeline_bg(config_dict: dict, chat_id: int, status_msg):
    """背景執行 pipeline，捕獲異常避免 crash"""
    try:
        from pipeline.runner import run_pipeline
        await run_pipeline(config_dict=config_dict, chat_id=chat_id)
    except Exception as e:
        try:
            await status_msg.edit_text(
                f"❌ Pipeline 啟動失敗：{html.escape(str(e))}",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def pipeline_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    處理 pipeline inline keyboard 的 callback。
    payload 格式：pipe_retry:<run_id> | pipe_skip:<run_id> | pipe_abort:<run_id>
    """
    query = update.callback_query
    await query.answer()

    if not _check_auth(update):
        await query.edit_message_text("⛔ 無授權存取。")
        return

    data = query.data or ""
    if not data.startswith("pipe_"):
        return

    action, run_id = data.split(":", 1)
    decision_map = {
        "pipe_retry": "retry",
        "pipe_skip":  "skip",
        "pipe_abort": "abort",
    }
    decision = decision_map.get(action)
    if not decision:
        return

    # 移除 inline keyboard，避免重複按
    await query.edit_message_reply_markup(reply_markup=None)

    from pipeline.runner import resume_pipeline
    result_msg = await resume_pipeline(run_id, decision)
    await query.message.reply_text(result_msg, parse_mode=ParseMode.HTML)


async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """處理一般訊息（視為任務描述直接執行）"""
    if not _check_auth(update):
        return
    task = update.message.text or ""
    if task:
        ctx.args = task.split()
        await run_cmd(update, ctx)


def create_application():
    """建立並設定 Bot Application"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        raise ValueError("TELEGRAM_BOT_TOKEN 未設定，請在 .env 中填入 Bot Token")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("run", run_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(CommandHandler("deltask", deltask_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("pipeline", pipeline_cmd))
    app.add_handler(CallbackQueryHandler(pipeline_callback, pattern=r"^pipe_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    return app


async def run_bot():
    """啟動 Telegram Bot（長輪詢模式）"""
    app = create_application()
    await app.initialize()
    await app.start()
    print("✅ Telegram Bot 已啟動，等待訊息中...")
    await app.updater.start_polling()
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
