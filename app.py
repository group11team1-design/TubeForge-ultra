import os, tempfile
from urllib.parse import urlparse
import imageio_ffmpeg
import yt_dlp
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","), supports_credentials=False)
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def checked_url(value):
    value = (value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a valid http or https video URL.")
    return value

def friendly_error(message):
    lower = message.lower()
    if "sign in to confirm" in lower or "not a bot" in lower:
        return ("YouTube requires verification for this video. TubeForge does not use personal "
                "browser cookies or bypass access controls. Try a publicly accessible video.")
    return message[:1200]

def ydl_options(**overrides):
    options = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "socket_timeout": 15, "retries": 1, "ffmpeg_location": FFMPEG_EXE,
    }
    options.update(overrides)
    return options

@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.get("/config.js")
def config():
    return send_from_directory(BASE_DIR, "config.js")

@app.get("/api/health")
def health():
    return jsonify(status="ok", service="TubeForge API", ffmpeg=os.path.exists(FFMPEG_EXE))

@app.post("/api/info")
def info():
    try:
        data = request.get_json(silent=True) or {}
        url = checked_url(data.get("url"))
        with yt_dlp.YoutubeDL(ydl_options(skip_download=True)) as ydl:
            info_data = ydl.extract_info(url, download=False)
        heights = sorted({int(f["height"]) for f in info_data.get("formats", [])
                          if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
        return jsonify(
            title=info_data.get("title") or "Video",
            thumbnail=info_data.get("thumbnail"),
            duration=info_data.get("duration_string"),
            uploader=info_data.get("uploader"),
            qualities=[{"height": h, "label": f"{h}p"} for h in heights],
            note="FFmpeg merge is enabled. Vercel runtime, storage, and response limits may prevent larger downloads."
        )
    except Exception as exc:
        return jsonify(error=friendly_error(str(exc))), 422

@app.get("/api/download")
def download():
    workdir = tempfile.mkdtemp(prefix="tubeforge-")
    try:
        url = checked_url(request.args.get("url"))
        mode = request.args.get("format", "video").lower()
        height = request.args.get("height", "best")
        if mode not in ("video", "audio"):
            return jsonify(error="format must be video or audio"), 400

        if mode == "audio":
            fmt, ext = "bestaudio/best", "mp3"
            postprocessors = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        else:
            if height == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                try:
                    max_height = max(144, min(int(height), 4320))
                except ValueError:
                    return jsonify(error="Invalid video height."), 400
                fmt = f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"
            ext = "mp4"
            postprocessors = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]

        opts = ydl_options(
            format=fmt,
            outtmpl=os.path.join(workdir, "%(title).100B.%(ext)s"),
            merge_output_format="mp4" if mode == "video" else None,
            postprocessors=postprocessors,
            continuedl=False,
            noprogress=True,
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            info_data = ydl.extract_info(url, download=True)
            output = ydl.prepare_filename(info_data)

        root, _ = os.path.splitext(output)
        candidates = [root + "." + ext, output]
        output = next((p for p in candidates if os.path.isfile(p)), None)
        if not output:
            found = [os.path.join(workdir, n) for n in os.listdir(workdir)
                     if os.path.isfile(os.path.join(workdir, n))]
            output = found[0] if found else None
        if not output or not os.path.isfile(output):
            return jsonify(error="The merged output file was not created."), 500
        return send_file(output, as_attachment=True, download_name=os.path.basename(output), conditional=True)
    except Exception as exc:
        return jsonify(error=friendly_error(str(exc))), 422

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
