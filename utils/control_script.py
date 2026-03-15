import os
import json
from flask import jsonify, request
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(BASE_DIR, "config", "KichBan")
os.makedirs(SCRIPT_DIR, exist_ok=True)


def list_scripts_handler():
    """
    Flask view: trả về danh sách tên file .txt trong config/KichBan (bao gồm cả .txt để phân biệt)
    """
    files = []
    if os.path.isdir(SCRIPT_DIR):
        for name in os.listdir(SCRIPT_DIR):
            if name.lower().endswith(".txt"):
                files.append(name)  # giữ nguyên tên có .txt
    return jsonify(files)


def load_script_handler():
    """
    Flask view: đọc nội dung file .txt và parse JSON scenes.
    Query param: ?name=<filename_with_ext>
    """
    name = request.args.get("name")
    if not name:
        return jsonify({"ok": False, "error": "Missing name"}), 400

    # Giữ nguyên tên gốc (có thể chứa .txt)
    path = os.path.join(SCRIPT_DIR, name)

    # Đảm bảo file nằm trong SCRIPT_DIR (ngăn path traversal)
    if not os.path.abspath(path).startswith(os.path.abspath(SCRIPT_DIR)):
        return jsonify({"ok": False, "error": "Invalid name"}), 400

    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "File not found"}), 404

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return jsonify({"ok": True, "scenes": data})
    except json.JSONDecodeError as e:
        return jsonify({"ok": False, "error": f"Invalid JSON: {e}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def save_script_handler():
    """
    Flask view: lưu danh sách scenes vào file .txt.
    Body JSON: { "name": "...", "scenes": [...] }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    scenes = data.get("scenes")

    if not name or not isinstance(scenes, list):
        return jsonify({"ok": False, "error": "Invalid request"}), 400

    # Nếu tên chưa có .txt thì thêm vào
    if not name.lower().endswith(".txt"):
        filename = name + ".txt"
    else:
        filename = name
    path = os.path.join(SCRIPT_DIR, filename)

    # Đảm bảo file nằm trong SCRIPT_DIR (ngăn path traversal)
    if not os.path.abspath(path).startswith(os.path.abspath(SCRIPT_DIR)):
        return jsonify({"ok": False, "error": "Invalid name"}), 400

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


def delete_script_handler():
    """
    Flask view: xóa file script
    Body JSON: {"name": "filename.txt"}
    """
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return jsonify({"ok": False, "error": "Missing name"}), 400
    
    # Đảm bảo tên file có .txt
    if not name.lower().endswith(".txt"):
        name += ".txt"
    
    file_path = os.path.join(SCRIPT_DIR, name)
    
    if not os.path.exists(file_path):
        return jsonify({"ok": False, "error": "File not found"}), 404
    
    try:
        os.remove(file_path)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
