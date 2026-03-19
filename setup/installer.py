import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import requests
except ImportError:
    requests = None


# =======================
# CONFIG
# =======================
DOWNLOAD_URL = "https://github.com/AnhTuan2003ml/creat_video/releases/latest/download/creat_video_start.zip"

EXE_NAME = "Creat_Video.exe"
APP_FOLDER_NAME = "Creat_Video"
SHORTCUT_NAME = "Creat_Video"
ICON_FILE = "bg_menu.ico"
# =======================


def is_windows() -> bool:
    return os.name == "nt"


def default_install_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_FOLDER_NAME)


def ensure_requests():
    if requests is None:
        raise RuntimeError("Thiếu thư viện requests. Cài bằng: pip install requests")


def download_file(url: str, out_path: str, progress_cb=None, cancel_event: threading.Event | None = None):
    ensure_requests()
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        got = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError("Đã huỷ cài đặt.")
                if not chunk:
                    continue
                f.write(chunk)
                got += len(chunk)
                if progress_cb:
                    progress_cb(got, total)


def extract_zip(zip_path: str, dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)


def find_exe_path(install_dir: str) -> str:
    p = os.path.join(install_dir, EXE_NAME)
    if os.path.isfile(p):
        return p
    for root, _, files in os.walk(install_dir):
        if EXE_NAME in files:
            return os.path.join(root, EXE_NAME)
    raise FileNotFoundError(f"Không tìm thấy {EXE_NAME} trong: {install_dir}")


def find_file_under(root_dir: str, filename: str) -> str | None:
    direct = os.path.join(root_dir, filename)
    if os.path.isfile(direct):
        return direct
    for r, _, files in os.walk(root_dir):
        if filename in files:
            return os.path.join(r, filename)
    return None


def safe_delete_children(folder: str):
    if not os.path.isdir(folder):
        return
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except:
            pass


def create_desktop_shortcut(shortcut_name: str, target_path: str, working_dir: str, icon_path: str = None):
    """Tạo shortcut Desktop (.lnk) bằng PowerShell."""
    if not is_windows():
        return

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    lnk_path = os.path.join(desktop, f"{shortcut_name}.lnk")

    def ps_escape(s: str) -> str:
        return s.replace("`", "``").replace('"', '`"')

    ps = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{ps_escape(lnk_path)}")
$Shortcut.TargetPath = "{ps_escape(target_path)}"
$Shortcut.WorkingDirectory = "{ps_escape(working_dir)}"
'''
    if icon_path:
        ps += f'$Shortcut.IconLocation = "{ps_escape(icon_path)}"\n'
    ps += '$Shortcut.Save()'

    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
        **_win_subprocess_kwargs(),
    )


def get_base_dir_for_assets() -> str:
    # Hỗ trợ PyInstaller --onefile
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def _win_subprocess_kwargs():
    if os.name != 'nt':
        return {}
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
    except Exception:
        si = None
    kw = {}
    try:
        kw['creationflags'] = subprocess.CREATE_NO_WINDOW
    except Exception:
        pass
    if si is not None:
        kw['startupinfo'] = si
    return kw


class InstallerUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Creat_Video Installer")

        # ===== ICON (bg_menu.ico) =====
        try:
            base_dir = get_base_dir_for_assets()
            icon_path = os.path.join(base_dir, ICON_FILE)
            if os.path.isfile(icon_path):
                self.iconbitmap(icon_path)
        except:
            pass

        # ===== NVIDIA-like sizing =====
        self.minsize(820, 460)
        self.geometry("980x540")
        self.resizable(True, True)

        # State
        self.install_dir = tk.StringVar(value=default_install_dir())
        self.create_shortcut = tk.BooleanVar(value=True)
        self.run_after_install = tk.BooleanVar(value=True)

        self._q: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()

        self._apply_theme()
        self._build()
        self.after(80, self._poll_queue)

    # =======================
    # THEME (dark + green accent)
    # =======================
    def _apply_theme(self):
        self.configure(bg="#0f1114")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass

        # Base colors
        self.C_BG = "#0f1114"
        self.C_PANEL = "#14171c"
        self.C_PANEL2 = "#101216"
        self.C_TEXT = "#e6e8ea"
        self.C_MUTED = "#a9b0b6"
        self.C_ACCENT = "#76b900"  # green-ish accent (NVIDIA vibe)
        self.C_BORDER = "#232831"

        style.configure("Root.TFrame", background=self.C_BG)
        style.configure("Panel.TFrame", background=self.C_PANEL)
        style.configure("Panel2.TFrame", background=self.C_PANEL2)

        style.configure("Title.TLabel", background=self.C_PANEL, foreground=self.C_TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=self.C_PANEL, foreground=self.C_MUTED, font=("Segoe UI", 10))
        style.configure("Text.TLabel", background=self.C_PANEL2, foreground=self.C_TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.C_PANEL2, foreground=self.C_MUTED, font=("Segoe UI", 9))

        style.configure("Step.TLabel", background=self.C_PANEL, foreground=self.C_MUTED, font=("Segoe UI", 10))
        style.configure("StepOn.TLabel", background=self.C_PANEL, foreground=self.C_TEXT, font=("Segoe UI", 10, "bold"))

        style.configure("TCheckbutton", background=self.C_PANEL2, foreground=self.C_TEXT)
        style.map("TCheckbutton", background=[("active", self.C_PANEL2)])

        # Entry
        style.configure("TEntry", fieldbackground="#0c0e12", foreground=self.C_TEXT, bordercolor=self.C_BORDER)

        # Buttons
        style.configure(
            "Primary.TButton",
            background=self.C_ACCENT,
            foreground="#0b0c0d",
            bordercolor=self.C_ACCENT,
            focusthickness=0,
            padding=(14, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#8ed10a"), ("disabled", "#3a3f48")],
            foreground=[("disabled", "#9aa1a9")],
        )

        style.configure(
            "Ghost.TButton",
            background=self.C_PANEL2,
            foreground=self.C_TEXT,
            bordercolor=self.C_BORDER,
            focusthickness=0,
            padding=(12, 8),
            font=("Segoe UI", 10),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#1a1f27"), ("disabled", "#12151a")],
            foreground=[("disabled", "#7a828c")],
        )

        # Progressbar
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#0c0e12",
            background=self.C_ACCENT,
            bordercolor=self.C_BORDER,
            lightcolor=self.C_ACCENT,
            darkcolor=self.C_ACCENT,
        )

    # =======================
    # UI LAYOUT (NVIDIA-like)
    # =======================
    def _build(self):
        root = ttk.Frame(self, style="Root.TFrame")
        root.pack(fill="both", expand=True)

        root.columnconfigure(0, weight=0)  # left
        root.columnconfigure(1, weight=1)  # right
        root.rowconfigure(0, weight=1)

        # ---------- LEFT BRAND PANEL ----------
        left = ttk.Frame(root, width=280, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsw")
        left.grid_propagate(False)

        # header (fake accent line)
        header = tk.Canvas(left, height=6, bg=self.C_ACCENT, highlightthickness=0)
        header.pack(fill="x", side="top")

        pad = 18
        inner = ttk.Frame(left, style="Panel.TFrame", padding=(pad, 16))
        inner.pack(fill="both", expand=True)

        ttk.Label(inner, text="CREAT_VIDEO", style="Title.TLabel").pack(anchor="w")
        ttk.Label(inner, text="Trình cài đặt", style="Sub.TLabel").pack(anchor="w", pady=(4, 16))

        self._step_vars = {
            "download": tk.StringVar(value="• Tải gói cài đặt"),
            "extract": tk.StringVar(value="• Giải nén & cập nhật"),
            "shortcut": tk.StringVar(value="• Tạo shortcut"),
            "playwright": tk.StringVar(value="• Cài Playwright"),
            "done": tk.StringVar(value="• Hoàn tất"),
        }

        self._step_labels = {}
        for k, v in self._step_vars.items():
            lbl = ttk.Label(inner, textvariable=v, style="Step.TLabel")
            lbl.pack(anchor="w", pady=4)
            self._step_labels[k] = lbl

        ttk.Label(inner, text="", style="Sub.TLabel").pack(anchor="w", pady=(14, 0))
        ttk.Label(
            inner,
            text="Gợi ý: Nếu Windows hỏi quyền, hãy bấm Yes/Allow.",
            style="Sub.TLabel",
            wraplength=240,
            justify="left",
        ).pack(anchor="w")

        # ---------- RIGHT CONTENT PANEL ----------
        right = ttk.Frame(root, style="Panel2.TFrame", padding=(22, 18))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        # top title
        ttk.Label(right, text="Cài đặt Creat_Video", style="Text.TLabel", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            right,
            text="Chọn thư mục cài đặt và bấm Cài đặt để bắt đầu.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        # install dir box
        box = ttk.Frame(right, style="Panel2.TFrame")
        box.grid(row=2, column=0, sticky="ew")
        box.columnconfigure(0, weight=1)

        ttk.Label(box, text="Thư mục cài đặt", style="Muted.TLabel").grid(row=0, column=0, sticky="w")

        dir_row = ttk.Frame(box, style="Panel2.TFrame")
        dir_row.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        dir_row.columnconfigure(0, weight=1)

        self.txtDir = ttk.Entry(dir_row, textvariable=self.install_dir)
        self.txtDir.grid(row=0, column=0, sticky="ew")

        self.btnBrowse = ttk.Button(dir_row, text="Chọn...", style="Ghost.TButton", command=self._browse)
        self.btnBrowse.grid(row=0, column=1, padx=(10, 0))

        # options
        opt = ttk.Frame(right, style="Panel2.TFrame")
        opt.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Checkbutton(opt, text="Tạo shortcut ngoài Desktop", variable=self.create_shortcut).pack(anchor="w", pady=3)
        ttk.Checkbutton(opt, text="Mở ứng dụng sau khi cài xong", variable=self.run_after_install).pack(anchor="w", pady=3)

        # progress / status
        prog = ttk.Frame(right, style="Panel2.TFrame")
        prog.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        prog.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(prog, style="Green.Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew")

        self.status = ttk.Label(right, text="Sẵn sàng cài đặt.", style="Muted.TLabel")
        self.status.grid(row=5, column=0, sticky="w", pady=(10, 0))

        # buttons
        btns = ttk.Frame(right, style="Panel2.TFrame")
        btns.grid(row=6, column=0, sticky="e", pady=(22, 0))

        self.btnExit = ttk.Button(btns, text="Thoát", style="Ghost.TButton", command=self._on_exit)
        self.btnExit.grid(row=0, column=0, padx=(0, 10))

        self.btnInstall = ttk.Button(btns, text="Cài đặt", style="Primary.TButton", command=self._install_async)
        self.btnInstall.grid(row=0, column=1)

        self.btnCancel = ttk.Button(btns, text="Huỷ", style="Ghost.TButton", command=self._cancel_install, state="disabled")
        self.btnCancel.grid(row=0, column=2, padx=(10, 0))

    # =======================
    # helpers
    # =======================
    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.install_dir.get() or default_install_dir())
        if d:
            self.install_dir.set(d)

    def _ui_lock(self, installing: bool):
        state = "disabled" if installing else "normal"
        self.btnInstall.config(state=state)
        self.btnBrowse.config(state=state)
        self.txtDir.config(state=state)
        self.btnCancel.config(state="normal" if installing else "disabled")

    def _set_status(self, txt: str):
        self.status.config(text=txt)

    def _post(self, kind: str, payload=None):
        self._q.put((kind, payload))

    def _set_step(self, active_key: str):
        # highlight active step (left)
        for k, lbl in self._step_labels.items():
            lbl.configure(style="StepOn.TLabel" if k == active_key else "Step.TLabel")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._q.get_nowait()

                if kind == "status":
                    self._set_status(str(payload))

                elif kind == "progress":
                    try:
                        self.progress["value"] = int(payload)
                    except:
                        pass

                elif kind == "step":
                    self._set_step(str(payload))

                elif kind == "done":
                    self._ui_lock(False)
                    self.progress["value"] = 100
                    self._set_status("Hoàn tất!")
                    self._set_step("done")

                    info = payload or {}
                    install_dir = info.get("install_dir", "")
                    exe_path = info.get("exe_path", "")

                    messagebox.showinfo("Thành công", f"Cài đặt thành công!\n\n{install_dir}")

                    if self.run_after_install.get() and exe_path and os.path.isfile(exe_path):
                        try:
                            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
                        except Exception as e:
                            messagebox.showwarning("Cảnh báo", f"Cài xong nhưng không mở được app:\n{e}")

                    self.destroy()

                elif kind == "error":
                    self._ui_lock(False)
                    self._set_status("Có lỗi.")
                    messagebox.showerror("Lỗi", str(payload))

                elif kind == "cancelled":
                    self._ui_lock(False)
                    self._set_status("Đã huỷ.")
        except queue.Empty:
            pass

        self.after(80, self._poll_queue)

    def _cancel_install(self):
        if self._worker and self._worker.is_alive():
            self._cancel.set()
            self._post("status", "Đang huỷ...")

    def _on_exit(self):
        if self._worker and self._worker.is_alive():
            self._cancel.set()
            self._post("status", "Đang huỷ... (đợi chút)")
            return
        self.destroy()

    def _install_async(self):
        if self._worker and self._worker.is_alive():
            return

        self._cancel.clear()
        self.progress["value"] = 0

        self._ui_lock(True)
        self._post("step", "download")
        self._set_status("Bắt đầu...")

        self._worker = threading.Thread(target=self._install_worker, daemon=True)
        self._worker.start()

    # =======================
    # worker
    # =======================
    def _install_worker(self):
        tmp = None
        try:
            install_dir = (self.install_dir.get() or "").strip()
            if not install_dir:
                raise RuntimeError("Bạn chưa chọn thư mục cài đặt.")

            if os.path.basename(install_dir).lower() != APP_FOLDER_NAME.lower():
                install_dir = os.path.join(install_dir, APP_FOLDER_NAME)

            os.makedirs(install_dir, exist_ok=True)

            tmp = tempfile.mkdtemp(prefix="creat_video_setup_")
            zip_path = os.path.join(tmp, "update.zip")

            # STEP: download
            self._post("step", "download")
            self._post("status", "Đang tải gói cài đặt...")

            def on_progress(got, total):
                if total > 0:
                    pct = int(got * 100 / total)
                    self._post("progress", pct)
                    self._post("status", f"Đang tải... {pct}%")
                else:
                    self._post("status", f"Đang tải... {got/1024/1024:.1f} MB")

            download_file(DOWNLOAD_URL, zip_path, on_progress, cancel_event=self._cancel)
            if self._cancel.is_set():
                self._post("cancelled", None)
                return

            # STEP: extract
            self._post("step", "extract")
            self._post("status", "Đang cập nhật file...")
            safe_delete_children(install_dir)

            if self._cancel.is_set():
                self._post("cancelled", None)
                return

            self._post("status", "Đang giải nén...")
            extract_zip(zip_path, install_dir)

            if self._cancel.is_set():
                self._post("cancelled", None)
                return

            exe_path = find_exe_path(install_dir)

            # STEP: shortcut
            self._post("step", "shortcut")
            self._post("status", "Đang tạo shortcut...")
            if self.create_shortcut.get():
                create_desktop_shortcut(
                    SHORTCUT_NAME,
                    exe_path,
                    os.path.dirname(exe_path),
                    icon_path=exe_path,
                )

            # STEP: playwright
            self._post("step", "playwright")
            self._post("status", "Đang cài Playwright...")
            ps1 = find_file_under(install_dir, "playwright.ps1")

            if ps1 is None:
                self._post("status", "Không thấy playwright.ps1 (bỏ qua Playwright).")
            else:
                ps_dir = os.path.dirname(ps1)
                cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, "install"]
                proc = subprocess.Popen(
                    cmd,
                    cwd=ps_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    **_win_subprocess_kwargs(),
                )

                # đọc output để tránh đầy buffer, nhưng KHÔNG hiển thị
                while True:
                    if self._cancel.is_set():
                        try:
                            proc.terminate()
                        except:
                            pass
                        self._post("cancelled", None)
                        return

                    line = proc.stdout.readline() if proc.stdout else ""
                    if not line and proc.poll() is not None:
                        break

                rc = proc.wait()
                if rc != 0:
                    raise RuntimeError(f"playwright.ps1 install lỗi (exit code={rc}).")
                self._post("status", "Playwright install xong.")

            # cleanup tmp
            try:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
            except:
                pass

            self._post("done", {"install_dir": install_dir, "exe_path": exe_path})

        except Exception as e:
            try:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
            except:
                pass
            self._post("error", str(e))


def main():
    if not is_windows():
        return
    app = InstallerUI()
    app.mainloop()


if __name__ == "__main__":
    main()