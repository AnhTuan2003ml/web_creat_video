from flask import Flask, jsonify, send_from_directory, request
import asyncio
import base64
import uuid
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
    generate_script_handler,
    list_tasks_handler,
    clear_tasks_handler,
    save_config_handler,
    cleanup_temp_handler,
    upload_temp_video_handler,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "config", "Music")
THEME_IMG_DIR = os.path.join(BASE_DIR, "templaces", "img")
GENERATED_DIR = os.path.join(BASE_DIR, "generated")

app = Flask(__name__, static_folder=".", static_url_path="")


def _safe_folder_name(name: str) -> str:
    name = (name or '').strip()
    if not name:
        return 'default'
    # keep it simple and filesystem-safe
    allowed = []
    for ch in name:
        if ch.isalnum() or ch in ('-', '_'):
            allowed.append(ch)
        elif ch.isspace():
            allowed.append('-')
    out = ''.join(allowed).strip('-')
    return out or 'default'


def _write_data_url_to_file(data_url: str, out_path: str) -> None:
    if not data_url or not data_url.startswith('data:image'):
        raise ValueError('Only data:image/* base64 is supported')
    try:
        header, b64 = data_url.split(',', 1)
        content = base64.b64decode(b64)
    except Exception as exc:
        raise ValueError('Invalid base64 image') from exc

    with open(out_path, 'wb') as f:
        f.write(content)


@app.route("/")
def index():
    # Phục vụ giao diện chính
    return send_from_directory("templaces/html", "index.html")


@app.route('/generated/<path:filename>')
def serve_generated(filename: str):
    return send_from_directory(GENERATED_DIR, filename)


@app.route('/debug_browser', methods=['GET'])
def debug_browser():
    try:
        from utils.grok.profile import PROFILE_DIR
        from utils.control_profile import _GLOBAL_BROWSER, init_global_browser

        init_global_browser()

        def _safe_int(x):
            try:
                return int(x)
            except Exception:
                return 0

        async def _info():
            ctx = await _GLOBAL_BROWSER.get_context_async()
            pages = 0
            try:
                pages = len(ctx.pages) if ctx else 0
            except Exception:
                pages = 0
            return {
                'profile_dir': PROFILE_DIR,
                'has_context': ctx is not None,
                'pages': pages,
                'cdp_connected': _GLOBAL_BROWSER._browser is not None,
            }

        info = _GLOBAL_BROWSER.run(_info(), timeout=10)
        return jsonify({'ok': True, 'info': info})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/reset_browser_profile', methods=['POST'])
def reset_browser_profile():
    try:
        from utils.control_profile import _GLOBAL_BROWSER
        # Chỉ đóng trình duyệt và khởi động lại context, không xóa file vật lý
        _GLOBAL_BROWSER.run(_GLOBAL_BROWSER.reset_async(), timeout=60)
        return jsonify({'ok': True, 'message': 'Trình duyệt đã được khởi động lại (Dữ liệu profile vẫn giữ nguyên).'})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/open_grok_login', methods=['POST'])
def open_grok_login():
    try:
        from utils.control_profile import _GLOBAL_BROWSER, init_global_browser, run_global

        async def _open():
            init_global_browser()
            ctx = await _GLOBAL_BROWSER.get_context_async()
            if ctx is None:
                raise RuntimeError('Global browser context is not initialized')
            page = await ctx.new_page()
            await page.goto('https://grok.com/', timeout=60000)
            return True

        run_global(_open(), timeout=60)
        return jsonify({'ok': True})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


@app.route('/pick_result_folder', methods=['POST'])
def pick_result_folder():
    try:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            return jsonify({'ok': False, 'error': f'tkinter not available: {exc}'}), 500

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        path = filedialog.askdirectory()

        try:
            root.destroy()
        except Exception:
            pass

        if not path:
            return jsonify({'ok': False, 'error': 'No folder selected'}), 200

        return jsonify({'ok': True, 'path': os.path.abspath(path)})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


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


@app.route("/upload_temp_video", methods=["POST"])
def upload_temp_video():
    return upload_temp_video_handler()


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


@app.route("/generate_script", methods=["POST"])
def generate_script():
    return generate_script_handler()


@app.route("/list_tasks")
def list_tasks():
    return list_tasks_handler()


@app.route("/clear_tasks", methods=["POST"])
def clear_tasks():
    return clear_tasks_handler()


@app.route("/save_config", methods=["POST"])
def save_config():
    return save_config_handler()


@app.route("/cleanup_temp", methods=["POST"])
def cleanup_temp():
    return cleanup_temp_handler()


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


@app.route('/setup_profile', methods=['POST'])
def setup_profile():
    try:
        data = request.get_json()
        if not data or 'model' not in data:
            return jsonify({'success': False, 'error': 'Missing model parameter'})
        
        model = data['model']
        
        # Import and run control_profile.py
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
        
        from control_profile import setting_grok_profile
        
        # Map model names to functions
        model_functions = {
            'Grok (X-AI)': setting_grok_profile,
            'Veo3 (Google)': lambda: print("Veo3 profile setup not implemented yet"),
            'Kling AI': lambda: print("Kling AI profile setup not implemented yet")
        }
        
        if model in model_functions:
            result = model_functions[model]()
            return jsonify({'success': True, 'message': f'Profile setup completed for {model}'})
        else:
            return jsonify({'success': False, 'error': f'Unknown model: {model}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/create_images_batch', methods=['POST'])
def create_images_batch():
    try:
        payload = request.get_json(silent=True) or {}
        provider = str(payload.get('provider') or '').strip()
        out_dir_label = str(payload.get('out_dir_label') or '').strip()
        max_tabs = payload.get('max_tabs', 5)
        ratio = str(payload.get('ratio') or '9:16').strip()
        tasks = payload.get('tasks')

        if not isinstance(tasks, list) or len(tasks) == 0:
            return jsonify({'ok': False, 'error': 'No tasks provided'}), 400

        # Ưu tiên dùng đường dẫn tuyệt đối từ label nếu nó là một thư mục hợp lệ
        # Nếu không thì mới dùng thư mục generated mặc định
        if os.path.isabs(out_dir_label) and os.path.isdir(out_dir_label):
            out_folder_abs = out_dir_label
            # Với thư mục ngoài, ta không có URL /generated/ tiện lợi,
            # nên ta sẽ phục vụ nó qua một route tạm hoặc trả về path tuyệt đối (tùy frontend xử lý)
            is_custom_dir = True
        else:
            folder = _safe_folder_name(out_dir_label)
            batch_id = uuid.uuid4().hex[:8]
            out_folder_rel = os.path.join(folder, batch_id)
            out_folder_abs = os.path.join(GENERATED_DIR, out_folder_rel)
            os.makedirs(out_folder_abs, exist_ok=True)
            is_custom_dir = False

        runner_tasks = []
        results = []

        for t in tasks:
            form_id = str((t or {}).get('form_id') or '').strip()
            img1 = str((t or {}).get('image1') or '')
            img2 = str((t or {}).get('image2') or '')
            prompt = str((t or {}).get('prompt') or '')

            if not form_id:
                continue

            if not img1 or not img2 or not prompt:
                results.append({'form_id': form_id, 'url': None, 'error': 'Thiếu ảnh hoặc prompt'})
                continue

            out_name = f'{form_id}_{uuid.uuid4().hex[:4]}.png'
            out_abs = os.path.join(out_folder_abs, out_name)

            runner_tasks.append({
                'form_id': form_id,
                'image1_data': img1, # Truyền data url trực tiếp
                'image2_data': img2,
                'prompt': prompt,
                'out': out_abs,
                'ratio': ratio,
                'is_custom_dir': is_custom_dir,
                'out_name': out_name,
                'out_folder_rel': out_folder_rel if not is_custom_dir else None
            })

        if len(runner_tasks) == 0:
            return jsonify({'ok': True, 'results': results})

        from utils.control_creat_image import run_tasks
        from utils.control_profile import init_global_browser, run_global

        async def _run_on_global_ctx():
            from utils.control_profile import _GLOBAL_BROWSER
            init_global_browser(provider=provider)
            ctx = await _GLOBAL_BROWSER.get_context_async()
            if ctx is None:
                raise RuntimeError('Global browser context is not initialized')
            await run_tasks(context=ctx, provider=provider, tasks=runner_tasks, max_tabs=max_tabs, aspect_ratio=ratio)

        try:
            run_global(_run_on_global_ctx(), timeout=3600, provider=provider)
        except Exception as exc:
            return jsonify({'ok': False, 'error': str(exc)}), 500

        # Gom kết quả
        for t in runner_tasks:
            form_id = t.get('form_id')
            out_abs = t.get('out')
            if os.path.exists(out_abs):
                if t['is_custom_dir']:
                    # Nếu là thư mục ngoài, trả về file:// hoặc data url để hiển thị (tạm thời trả về data url cho an toàn hiển thị)
                    with open(out_abs, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode('utf-8')
                        url = f"data:image/png;base64,{b64_data}"
                else:
                    url = f"/generated/{t['out_folder_rel']}/{t['out_name']}"
                results.append({'form_id': form_id, 'url': url, 'error': None})
            else:
                results.append({'form_id': form_id, 'url': None, 'error': 'Không tạo được ảnh'})

        return jsonify({'ok': True, 'results': results})

    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


if __name__ == "__main__":
    # Chạy local: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)

