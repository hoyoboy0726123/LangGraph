import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Groq ────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_MAIN = "llama-3.3-70b-versatile"          # 主推理模型
GROQ_MODEL_FAST = "llama3-groq-8b-8192-tool-use-preview"  # 快速工具選擇

# ── Telegram ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",")
    if uid.strip().isdigit()
]

# ── Browser ─────────────────────────────────────────────────
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
BROWSER_BRIDGE_PORT = int(os.getenv("BROWSER_BRIDGE_PORT", "19825"))
CHROME_CDP_URL = f"http://localhost:{CHROME_DEBUG_PORT}"
BROWSER_BRIDGE_URL = f"http://localhost:{BROWSER_BRIDGE_PORT}"

# ── File System ─────────────────────────────────────────────
OUTPUT_BASE_PATH = Path(os.getenv("OUTPUT_BASE_PATH", "~/ai_output")).expanduser()
OUTPUT_BASE_PATH.mkdir(parents=True, exist_ok=True)

# 允許 AI 讀寫的資料夾白名單
ALLOWED_PATHS: list[Path] = [OUTPUT_BASE_PATH]
for extra in os.getenv("EXTRA_ALLOWED_PATHS", "").split(","):
    if extra.strip():
        p = Path(extra.strip()).expanduser()
        ALLOWED_PATHS.append(p)

# ── Scheduler ───────────────────────────────────────────────
TIMEZONE = os.getenv("TIMEZONE", "Asia/Taipei")
SCHEDULER_DB_PATH = OUTPUT_BASE_PATH / "scheduler.db"

# ── Validation ──────────────────────────────────────────────
def check_config() -> list[str]:
    """回傳尚未設定的必要項目清單"""
    missing = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        missing.append("GROQ_API_KEY")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        missing.append("TELEGRAM_BOT_TOKEN（Telegram 功能需要）")
    return missing
