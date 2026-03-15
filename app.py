from flask import Flask, jsonify, send_from_directory
import os
import sys
import subprocess

from utils.control_music import (
    list_music_handler,
    serve_music_handler,
    delete_music_handler,
    add_music_handler,
    upload_music_handler,
)

from utils.control_ffmpeg import (
    serve_transcoded_handler,
    transcode_video_handler,
    extract_frame_handler,
)

from utils.control_script import (
    list_scripts_handler,
    load_script_handler,
    save_script_handler,
    delete_script_handler,
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


@app.route("/transcoded/<path:filename>")
def serve_transcoded(filename: str):
    return serve_transcoded_handler(filename)


@app.route("/transcode_video", methods=["POST"])
def transcode_video():
    return transcode_video_handler()


@app.route("/extract_frame", methods=["POST"])
def extract_frame():
    return extract_frame_handler()


@app.route("/listscripts")
def list_scripts():
    return list_scripts_handler()


@app.route("/load_script")
def load_script():
    return load_script_handler()


@app.route("/save_script", methods=["POST"])
def save_script():
    return save_script_handler()


@app.route("/transcode_for_web", methods=["POST"])
def transcode_for_web():
    return transcode_video_handler()


@app.route("/delete_script", methods=["POST"])
def delete_script():
    return delete_script_handler()


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

