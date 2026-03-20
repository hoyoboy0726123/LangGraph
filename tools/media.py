"""
Media Download Tool：使用 yt-dlp 下載影片、音訊、圖片。
"""
import subprocess
from pathlib import Path
from langchain_core.tools import tool

from config import OUTPUT_BASE_PATH, ALLOWED_PATHS
from tools.file_manager import _is_allowed, _resolve_path


@tool
def download_media(url: str, filename: str = "") -> str:
    """
    下載網頁上的影片、音訊或圖片（支援 YouTube、Twitter、Bilibili 等）。

    Args:
        url: 媒體頁面網址
        filename: 儲存檔案名稱（不含副檔名，留空則自動命名）

    Returns:
        下載結果訊息
    """
    download_dir = OUTPUT_BASE_PATH / "media"
    download_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(download_dir / (filename if filename else "%(title)s.%(ext)s"))

    cmd = [
        "yt-dlp",
        "--output", output_template,
        "--no-playlist",
        "--restrict-filenames",
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return f"下載完成！已存到：{download_dir}"
        else:
            return f"下載失敗：{result.stderr[:500]}"
    except FileNotFoundError:
        return "yt-dlp 未安裝，請執行：pip install yt-dlp"
    except subprocess.TimeoutExpired:
        return "下載超時（超過 5 分鐘）"
    except Exception as e:
        return f"下載失敗：{e}"
