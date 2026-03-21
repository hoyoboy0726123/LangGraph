import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Groq ────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_MAIN = "llama-3.1-8b-instant"              # 主推理模型（TPD 500k）
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

# ── Pipeline ─────────────────────────────────────────────────
# 存放 pipeline YAML 定義檔的預設目錄
PIPELINE_DIR = Path(os.getenv("PIPELINE_DIR", "~/pipelines")).expanduser()
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

# ── OpenCLI 可用命令清單（opencli list 輸出，供 AI 直接參考）────
OPENCLI_COMMANDS = """
## OpenCLI 支援的網站與命令（244 個內建命令，44 個網站）

### 社群 / 內容平台
- twitter: timeline, search, post, reply, like, bookmark, bookmarks, follow, unfollow, block, unblock, thread, article, profile, trending, notifications, followers, following, download, reply-dm, accept, hide-reply, delete, unbookmark
- reddit: frontpage, hot, popular, search, subreddit, read, comment, upvote, save, saved, upvoted, user, user-posts, user-comments, subscribe
- xiaohongshu: search, feed, user, notifications, download, creator-notes, creator-note-detail, creator-notes-summary, creator-profile, creator-stats
- weibo: hot
- jike: feed, search, post, topic, user, like, comment, repost, notifications
- v2ex: hot, latest, topic, me, notifications, daily
- linux-do: hot, latest, categories, category, topic, search
- hackernews: top
- stackoverflow: hot, search, bounties, unanswered

### 影音 / 音樂
- youtube: search, video, transcript
- bilibili: hot, ranking, feed, dynamic, search, history, favorite, me, following, subtitle, user-videos, download
- neteasemusic: playing, playlist, search, play, next, prev, like, lyrics, volume, status
- xiaoyuzhou: podcast, episode, podcast-episodes

### 財經 / 股票
- xueqiu: hot, hot-stock, search, stock, feed, watchlist
- yahoo-finance: quote
- barchart: quote, options, greeks, flow
- sinafinance: news
- bloomberg: main, markets, tech, politics, economics, opinions, businessweek, industries, news, feeds

### 新聞 / 知識
- bbc: news
- reuters: search
- wikipedia: search, summary
- arxiv: search, paper
- hf: top
- zhihu: hot, search, question, download

### AI 工具
- chatgpt: ask, send, read, new, status
- grok: ask
- antigravity: send, read, ask, new, model, dump, extract-code, watch, status
- chatwise: ask, send, read, new, model, export, history, screenshot, status
- cursor: ask, send, read, new, composer, model, export, history, extract-code, dump, screenshot, status
- codex: ask, send, read, new, model, export, history, extract-diff, dump, screenshot, status

### 閱讀 / 筆記
- notion: search, read, write, new, favorites, sidebar, export, status
- weread: search, ranking, shelf, book, highlights, notes, notebooks
- jimeng: generate, history

### 職場 / 通訊
- boss: search, recommend, resume, detail, joblist, stats, greet, batchgreet, chatlist, chatmsg, send, invite, exchange, mark
- linkedin: search
- discord-app: read, send, search, channels, servers, members, status
- wechat: send, read, search, chats, contacts, status
- feishu: send, read, search, new, status

### 購物 / 旅遊
- coupang: search, add-to-cart
- smzdm: search
- steam: top-sellers
- ctrip: search
- apple-podcasts: search, top, episodes

### 學習
- chaoxing: assignments, exams

### External CLIs
- gh: GitHub CLI（repos, PRs, issues, releases）
- docker: Docker CLI
- gws: Google Workspace（Docs, Sheets, Drive, Gmail, Calendar）
- kubectl: Kubernetes CLI
- obsidian: Obsidian 筆記管理
- readwise: Readwise 閱讀清單

使用方式：run_opencli("site command [options]")
範例：run_opencli("twitter timeline --format json --limit 20")
     run_opencli("youtube search 'LangGraph tutorial' --limit 5")
     run_opencli("gh repo list --limit 10")
"""

# ── Validation ──────────────────────────────────────────────
def check_config() -> list[str]:
    """回傳尚未設定的必要項目清單"""
    missing = []
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        missing.append("GROQ_API_KEY")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        missing.append("TELEGRAM_BOT_TOKEN（Telegram 功能需要）")
    return missing
