from flask import Flask, render_template, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
from pathlib import Path
import uuid
import re

app = Flask(__name__)

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

YOUTUBE_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be"
}

def is_youtube_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname
        return bool(host and host.lower() in YOUTUBE_HOSTS)
    except Exception:
        return False

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/convert")
def convert():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url or not is_youtube_url(url):
        return jsonify({"error": "YouTubeのURLを入力してください。"}), 400

    job_id = uuid.uuid4().hex
    outtmpl = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")

    ydl_opts = {
        # Prefer MP4 video + M4A audio and merge them into MP4 when needed.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # yt-dlp may use a different extension if merging is unavailable.
        candidates = list(DOWNLOAD_DIR.glob(f"{job_id}.*"))
        if not candidates:
            raise RuntimeError("動画ファイルを作成できませんでした。")

        mp4 = next((p for p in candidates if p.suffix.lower() == ".mp4"), candidates[0])

        return jsonify({
            "title": info.get("title", "YouTube動画"),
            "url": f"/media/{mp4.name}",
            "filename": mp4.name
        })
    except Exception as e:
        return jsonify({
            "error": "動画を取得できませんでした。",
            "detail": str(e)
        }), 500

@app.get("/media/<path:filename>")
def media(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=False)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
