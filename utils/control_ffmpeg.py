
import base64
import os
import subprocess
import tempfile
import uuid

from flask import jsonify, request, send_from_directory


TRANSCODE_DIR = os.path.join(tempfile.gettempdir(), "web_creat_video_transcoded")
os.makedirs(TRANSCODE_DIR, exist_ok=True)


def serve_transcoded_handler(filename: str):
    return send_from_directory(TRANSCODE_DIR, filename)


def transcode_video_handler():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Missing file"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Invalid file"}), 400

    job_id = uuid.uuid4().hex
    in_path = os.path.join(TRANSCODE_DIR, f"{job_id}__src")
    out_name = f"{job_id}.mp4"
    out_path = os.path.join(TRANSCODE_DIR, out_name)

    try:
        file.save(in_path)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        in_path,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        out_path,
    ]

    try:
        subprocess.run(cmd, cwd=TRANSCODE_DIR, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "ffmpeg not found"}), 500
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        return jsonify({"ok": False, "error": err}), 500
    finally:
        try:
            if os.path.exists(in_path):
                os.remove(in_path)
        except OSError:
            pass

    if not os.path.exists(out_path):
        return jsonify({"ok": False, "error": "Transcode failed"}), 500

    return jsonify({"ok": True, "url": f"/transcoded/{out_name}", "mime": "video/mp4"})


def extract_frame_handler():
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
