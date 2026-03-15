from flask import Flask, jsonify, send_from_directory, request
import os
import sys
import subprocess
import base64
import tempfile

from utils.control_music import (
    list_music_handler,
    serve_music_handler,
    delete_music_handler,
    add_music_handler,
    upload_music_handler,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "config", "Music")
THEME_IMG_DIR = os.path.join(BASE_DIR, "templaces", "img")

app = Flask(__name__, static_folder=".", static_url_path="")


@app.route("/")
def index():
    # Phục vụ giao diện chính
    return send_from_directory("templaces/html", "index.html")


@app.route("/listmusic")
def list_music():
    return list_music_handler()


@app.route("/music/<path:filename>")
def serve_music(filename: str):
    return serve_music_handler(filename)


@app.route("/deletemusic", methods=["POST"])
def delete_music():
    return delete_music_handler()


@app.route("/addmusic", methods=["POST"])
def add_music():
    return add_music_handler()


@app.route("/uploadmusic", methods=["POST"])
def upload_music():
    return upload_music_handler()


@app.route("/uninstall", methods=["POST"])
def uninstall():
    base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR
    exe_path = os.path.join(base_dir, "uninstall.exe")

    if not os.path.exists(exe_path):
        return jsonify({"ok": False, "error": "uninstall.exe not found"}), 404

    try:
        subprocess.Popen([exe_path], cwd=base_dir)
    except OSError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True})


@app.route("/extract_frame", methods=["POST"])
def extract_frame():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Missing file"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Invalid file"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, file.filename)
        out_path = os.path.join(tmpdir, "thumb.jpg")
        file.save(in_path)

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            in_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            out_path,
        ]

        try:
            subprocess.run(cmd, cwd=tmpdir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            return jsonify({"ok": False, "error": "ffmpeg not found"}), 500
        except subprocess.CalledProcessError as exc:
            err = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            return jsonify({"ok": False, "error": err}), 500

        if not os.path.exists(out_path):
            return jsonify({"ok": False, "error": "Failed to extract frame"}), 500

        with open(out_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({"ok": True, "data_url": f"data:image/jpeg;base64,{b64}"})


@app.route("/open_video", methods=["POST"])
def open_video():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Missing file"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Invalid file"}), 400

    # Lưu tạm ra disk rồi gọi app mặc định của hệ điều hành để mở
    tmp_root = os.path.join(tempfile.gettempdir(), "web_creat_video_previews")
    os.makedirs(tmp_root, exist_ok=True)

    safe_name = os.path.basename(file.filename)
    out_path = os.path.join(tmp_root, safe_name)
    file.save(out_path)

    try:
        if sys.platform.startswith("win"):
            os.startfile(out_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", out_path])
        else:
            subprocess.Popen(["xdg-open", out_path])
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True})


@app.route("/listthemes")
def list_themes():
    """
    Trả về danh sách file ảnh theme trong templaces/img
    dạng:
    [
      {"name": "Default", "file": "Default.png", "url": "/templaces/img/Default.png"},
      ...
    ]
    """
    items = []

    if os.path.isdir(THEME_IMG_DIR):
        files = [f for f in os.listdir(THEME_IMG_DIR)
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

        # Chỉ giữ lại 4 theme: Default, Hacker, Tech, Princess (nếu tồn tại), theo đúng thứ tự này
        ordered_basenames = ["default", "hacker", "tech", "princess"]

        for base in ordered_basenames:
            # tìm file khớp basename (không phân biệt hoa thường)
            match = next(
                (
                    name for name in files
                    if os.path.splitext(name)[0].lower() == base
                ),
                None,
            )
            if not match:
                continue

            title = os.path.splitext(match)[0]

            # map basename -> class CSS
            if base == "default":
                theme_class = "theme-default"
            elif base == "hacker":
                theme_class = "theme-hacker"
            elif base == "tech":
                theme_class = "theme-tech"
            elif base == "princess":
                theme_class = "theme-princess"
            else:
                theme_class = "theme-default"

            items.append(
                {
                    "name": title,
                    "file": match,
                    "url": f"/templaces/img/{match}",
                    "theme": theme_class,
                }
            )

    return jsonify(items)


if __name__ == "__main__":
    # Chạy local: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)

