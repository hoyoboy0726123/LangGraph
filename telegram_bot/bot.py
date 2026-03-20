"""
Telegram Bot：讓使用者透過 Telegram 發派任務給 LangGraph agent。

功能：
  /run <任務>          - 執行一次性任務
  /schedule <任務>     - 互動式設定定時任務
  /tasks               - 列出所有定時任務
  /deltask <id>        - 刪除定時任務
  /status              - 查看 Bot 狀態
  /help                - 說明
"""
import asyncio
import html
from telegram import Update, BotCommand
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
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
        "/status — 查看系統狀態\n"
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
