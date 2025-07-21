import os
from datetime import datetime

import yt_dlp

DOWNLOAD_DIR = "downloads"


def get_available_formats(url):
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        video_options = []

        for f in formats:
            fmt_id = f.get("format_id")
            vres = f.get("height")
            acodec = f.get("acodec")
            vcodec = f.get("vcodec")

            if vcodec != "none" and acodec != "none" and vres:
                label = f"{fmt_id} - {vres}p"
                video_options.append((fmt_id, label))

        return video_options


def download_media(url: str, format_id: str, user_id: int) -> str | None:
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{format_id}_{timestamp}.%(ext)s")

    ydl_opts = {
        "format": format_id,
        "outtmpl": output_path,
        "quiet": True,
        "merge_output_format": "mp4",
        "retries": 1,
        "http_chunk_size": 1024 * 1024,
        "concurrent_fragment_downloads": 5,
        "noplaylist": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        return None

    base = f"{user_id}_{format_id}_{timestamp}"
    for ext in [".mp4", ".mkv", ".webm"]:
        file_path = os.path.join(DOWNLOAD_DIR, base + ext)
        if os.path.exists(file_path):
            return file_path

    return None
