import os
import subprocess
import shutil

# Lấy đường dẫn tuyệt đối đến thư mục gốc của project (thư mục chứa app.py)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, "..", ".."))
PROFILE_DIR = os.path.join(_PROJECT_ROOT, "profile")

print(f"DEBUG: Profile directory set to: {PROFILE_DIR}")


def find_chrome():
    paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",

        os.path.expandvars(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p

    return shutil.which("google-chrome") or shutil.which("chromium")


def setting_grok_profile():
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR, exist_ok=True)

    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome not found")

    url = "https://grok.com/"

    subprocess.Popen(
        [
            chrome,
            f"--user-data-dir={PROFILE_DIR}",
            "--remote-debugging-port=9222",
            "--remote-debugging-address=127.0.0.1",
            "--new-window",
            url
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )


if __name__ == "__main__":
    setting_grok_profile()