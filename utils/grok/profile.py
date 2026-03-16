import os
import subprocess
import shutil

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROFILE_DIR = os.path.join(_PROJECT_ROOT, "profile")


def find_chrome():
    paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
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