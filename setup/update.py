# update.py
# - Get GitHub latest release
# - Download latest zip asset
# - Extract to temp
# - Copy overwrite into APP_DIR
# - Update _internal/config.json field "VERSION" (tolerant, even if JSON is broken)

import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
import urllib.request

OWNER = "AnhTuan2003ml"
REPO = "creat_video"
API_LATEST = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
ASSET_PREFIX = "creat_video"
UA = "CreatVideoUpdater"

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

SKIP_NAMES = {"update.py", "update.exe"}

# ---------------- Version helpers ----------------

def normalize_tag(tag: str) -> str:
    if not tag:
        return "0.0.0"
    t = str(tag).strip()
    if len(t) >= 2 and (t[0] in ("v", "V")) and t[1].isdigit():
        t = t[1:]
    return t

# ---------------- GitHub ----------------

def get_latest_release():
    req = urllib.request.Request(
        API_LATEST,
        headers={"User-Agent": UA, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))

def pick_zip_asset(release_json):
    assets = release_json.get("assets", []) or []

    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(".zip") and name.startswith(ASSET_PREFIX.lower()):
            return a.get("browser_download_url")

    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(".zip"):
            return a.get("browser_download_url")

    return None

# ---------------- Download ----------------

def download_file(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as resp:
        total = resp.getheader("Content-Length")
        with open(dest, "wb") as f:
            if not total:
                shutil.copyfileobj(resp, f)
                print("Downloaded (no size info).")
                return

            total = int(total)
            downloaded = 0
            chunk_size = 1024 * 64
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                pct = (downloaded * 100) // total
                print(f"\rDownloading... {pct}%", end="")
    print("\nDownload complete.")

# ---------------- Extract ----------------

def safe_extract(zip_path: Path, extract_to: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)

def find_payload_root(extract_dir: Path) -> Path:
    items = [p for p in extract_dir.iterdir() if p.name not in (".DS_Store", "__MACOSX")]
    if len(items) == 1 and items[0].is_dir():
        return items[0]
    return extract_dir

# ---------------- Copy overwrite ----------------

def copy_overwrite(src_root: Path, dst_root: Path):
    for src in src_root.rglob("*"):
        rel = src.relative_to(src_root)
        dst = dst_root / rel

        if src.is_file() and src.name.lower() in SKIP_NAMES:
            continue

        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            try:
                os.chmod(dst, 0o666)
            except:
                pass

        shutil.copy2(src, dst)

# ---------------- Config VERSION update (tolerant) ----------------

def read_text_utf8sig(path: Path) -> str:
    # remove BOM if any
    return path.read_text(encoding="utf-8-sig", errors="replace")

def write_text_utf8(path: Path, text: str):
    path.write_text(text, encoding="utf-8")

def try_parse_json(text: str):
    # remove trailing commas like: "x":1,
    # (best-effort only; still may fail)
    try:
        return json.loads(text)
    except:
        return None

def update_config_version(app_dir: Path, new_version: str):
    cfg = app_dir / "_internal" / "config.json"
    if not cfg.exists():
        print("config.json not found:", cfg)
        return False

    new_version = normalize_tag(new_version)
    raw = read_text_utf8sig(cfg)

    # 1) Try parse + write pretty JSON if valid
    obj = try_parse_json(raw)
    if isinstance(obj, dict):
        obj["VERSION"] = new_version
        write_text_utf8(cfg, json.dumps(obj, ensure_ascii=False, indent=2))
        print("Updated VERSION (json ok) ->", new_version)
        return True

    # 2) JSON broken -> fallback regex replace
    print("⚠ config.json is invalid JSON -> fallback regex patch VERSION...")

    # Fix common wrong pattern: "VERSION":"VERSION": "1.0.0",
    raw = re.sub(r'"VERSION"\s*:\s*"VERSION"\s*:\s*', '"VERSION": ', raw)

    # Replace existing VERSION
    if re.search(r'"VERSION"\s*:\s*".*?"', raw, flags=re.IGNORECASE):
        patched = re.sub(
            r'("VERSION"\s*:\s*")([^"]*)(")',
            r'\g<1>' + new_version + r'\3',
            raw,
            flags=re.IGNORECASE,
            count=1
        )
        write_text_utf8(cfg, patched)
        print("Updated VERSION (regex replace) ->", new_version)
        return True

    # Insert VERSION after "API": ...
    m = re.search(r'("API"\s*:\s*".*?")\s*(,?)', raw, flags=re.IGNORECASE | re.DOTALL)
    if m:
        insert_pos = m.end()
        comma = ","  # always add comma after API line
        patched = raw[:insert_pos] + f'{comma}\n  "VERSION": "{new_version}"' + raw[insert_pos:]
        write_text_utf8(cfg, patched)
        print("Inserted VERSION (regex insert) ->", new_version)
        return True

    # If cannot locate API, just prepend VERSION at top-level (best-effort)
    patched = '{\n  "VERSION": "' + new_version + '",\n' + raw.lstrip()
    write_text_utf8(cfg, patched)
    print("Prepended VERSION (best-effort) ->", new_version)
    return True

# ---------------- Main ----------------

def main():
    print("APP_DIR:", APP_DIR)

    release = get_latest_release()
    tag = release.get("tag_name", "")
    latest_version = normalize_tag(tag)
    print("Latest release:", tag)

    zip_url = pick_zip_asset(release)
    if not zip_url:
        print("No zip asset found.")
        return 1

    work_dir = Path(tempfile.gettempdir()) / "creat_video_update"
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    zip_path = work_dir / "update.zip"
    extract_dir = work_dir / "extract"

    print("Downloading...")
    download_file(zip_url, zip_path)

    print("Extracting...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    safe_extract(zip_path, extract_dir)

    payload_root = find_payload_root(extract_dir)
    print("Payload root:", payload_root)

    print("Copy overwrite into APP_DIR...")
    copy_overwrite(payload_root, APP_DIR)

    print("Updating _internal/config.json VERSION...")
    update_config_version(APP_DIR, latest_version)

    print("Update done.")
    shutil.rmtree(work_dir, ignore_errors=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
