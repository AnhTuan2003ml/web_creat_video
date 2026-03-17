import asyncio
import threading

from utils.grok.profile import PROFILE_DIR, find_chrome, setting_grok_profile


def open_profile(provider: str):

    if not provider:
        return

    p = provider.strip().lower()

    if p in ["grok", "grok (x-ai)", "x-ai", "xai"]:
        # Only open profile + navigate to Grok (no CDP). CDP is managed by _GlobalBrowser.
        setting_grok_profile()
        return

    print(f"Provider not supported: {provider}")


class _GlobalBrowser:
    def __init__(self):
        self._loop = None
        self._thread = None
        self._ready = threading.Event()
        self._init_error = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._sema = None
        self._provider = "grok"
        self._download_dir = None
        self._lifecycle_lock = threading.Lock()
        self._spawned_pid = None

    def _thread_main(self, provider="grok", download_dir=None):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._provider = provider or "grok"
            self._download_dir = download_dir
            self._loop.run_until_complete(self._async_init(provider=provider, download_dir=download_dir))
        except Exception as exc:
            self._init_error = exc
        finally:
            self._ready.set()
            if self._loop:
                self._loop.run_forever()

    def _is_context_alive(self) -> bool:
        if self._context is None:
            return False
        try:
            # Check if we can still access pages. This will throw if context is closed.
            _ = self._context.pages
            # If we connected via CDP, also check if browser is still connected
            if self._browser:
                # Playwright's browser.is_connected() is the authoritative check for CDP
                if not self._browser.is_connected():
                    return False
            return True
        except Exception:
            # Any error here means the context/browser is no longer usable
            return False

    def _submit(self, coro, timeout=None):
        if self._loop is None:
            raise RuntimeError("Global browser loop is not initialized")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    async def _async_init(self, provider="grok", download_dir=None):
        from playwright.async_api import async_playwright
        import subprocess
        import time
        import os

        def _port_open(host: str, port: int) -> bool:
            try:
                import socket
                with socket.create_connection((host, port), timeout=0.3):
                    return True
            except Exception:
                return False

        async def _wait_cdp_ready(timeout_s: float = 8.0) -> bool:
            deadline = time.time() + float(timeout_s)
            while time.time() < deadline:
                if _port_open("127.0.0.1", 9222):
                    return True
                await asyncio.sleep(0.25)
            return False

        def _start_chrome_profile_with_cdp() -> None:
            chrome = find_chrome()
            if not chrome:
                raise RuntimeError("Chrome not found")
            try:
                os.makedirs(PROFILE_DIR, exist_ok=True)
            except Exception:
                pass

            url = "https://grok.com/"
            proc = subprocess.Popen(
                [
                    chrome,
                    f"--user-data-dir={PROFILE_DIR}",
                    "--remote-debugging-port=9222",
                    "--remote-debugging-address=127.0.0.1",
                    "--new-window",
                    url,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                self._spawned_pid = int(getattr(proc, 'pid', None) or 0) or None
            except Exception:
                self._spawned_pid = None

        # Stop existing playwright if any
        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass

        self._playwright = await async_playwright().start()

        # Normalize download dir
        download_dir = str(download_dir or "").strip() or None
        if download_dir:
            try:
                download_dir = os.path.abspath(download_dir)
                os.makedirs(download_dir, exist_ok=True)
            except Exception:
                download_dir = None

        # Ensure Chrome profile is running WITH CDP enabled, then connect via CDP.
        # control_profile.py is responsible for enabling 9222.
        if not await _wait_cdp_ready(timeout_s=1.0):
            try:
                _start_chrome_profile_with_cdp()
            except Exception:
                pass

        if not await _wait_cdp_ready(timeout_s=12.0):
            raise RuntimeError("CDP port 9222 is not available")

        print("DEBUG: Connecting to Chrome via CDP (port 9222)...")
        self._browser = await self._playwright.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=15000)
        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 720}, position={'x': -50, 'y': -50})

        # Try to force download directory via CDP if requested (best-effort)
        if download_dir:
            try:
                print(f"DEBUG: Set download_dir={download_dir}")
            except Exception:
                pass
            # 1) Browser-level (preferred)
            try:
                await self._browser.new_browser_cdp_session().send(
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": download_dir},
                )
            except Exception:
                pass

            # 2) Fallback: Page-level download behavior via a temporary page CDP session
            try:
                tmp = await self._context.new_page()
                try:
                    cdp = await self._context.new_cdp_session(tmp)
                    try:
                        await cdp.send(
                            "Browser.setDownloadBehavior",
                            {"behavior": "allow", "downloadPath": download_dir},
                        )
                    except Exception:
                        await cdp.send(
                            "Page.setDownloadBehavior",
                            {"behavior": "allow", "downloadPath": download_dir},
                        )
                finally:
                    try:
                        await tmp.close()
                    except Exception:
                        pass
            except Exception:
                pass

        self._sema = asyncio.Semaphore(5)
        return

    def ensure_started(self, provider="grok", download_dir=None):
        download_dir = str(download_dir or "").strip() or None
        with self._lifecycle_lock:
            # If thread is up and healthy, reuse it.
            if self._thread and self._thread.is_alive() and self._ready.is_set() and not self._init_error:
                # Only re-init when context is dead/disconnected.
                # Do NOT re-init just because download_dir changed, as that would kill
                # in-flight tabs from other concurrent jobs (image/video).
                if self._is_context_alive():
                    self._provider = provider or self._provider
                    self._download_dir = download_dir
                    return

                self._provider = provider or self._provider
                self._download_dir = download_dir
                self._submit(self._async_init(provider=self._provider, download_dir=self._download_dir), timeout=60)
                return

            if self._thread and self._thread.is_alive() and self._ready.is_set() and self._init_error:
                raise self._init_error

            self._ready.clear()
            self._init_error = None
            self._thread = threading.Thread(target=self._thread_main, args=(provider, download_dir), daemon=True)
            self._thread.start()
            self._ready.wait(timeout=60)
            if self._init_error:
                raise self._init_error

    def run(self, coro, timeout=None):
        self.ensure_started()
        return self._submit(coro, timeout=timeout)

    async def get_context_async(self):
        if not self._is_context_alive():
            print("DEBUG: Context is dead or browser disconnected. Re-initializing...")
            await self._async_init(provider=self._provider, download_dir=self._download_dir)
        return self._context

    async def run_with_tab_slot(self, coro):
        if self._sema is None:
            self._sema = asyncio.Semaphore(5)
        await self._sema.acquire()
        try:
            return await coro
        finally:
            self._sema.release()

    async def reset_async(self):
        await self.close_async()
        await self._async_init(provider=self._provider, download_dir=self._download_dir)

    async def close_async(self):
        # Close everything but do not re-init
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                # For CDP-connected browsers, browser.close() may only disconnect.
                # To really close Chrome, send the CDP Browser.close command.
                try:
                    sess = await self._browser.new_browser_cdp_session()
                    await sess.send("Browser.close")
                except Exception:
                    pass
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        # Force-kill Chrome process tree if we spawned it (best-effort)
        pid = self._spawned_pid
        self._spawned_pid = None
        if pid:
            try:
                import os
                import subprocess
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        # Fallback: if Flask reloader restarted, we may have lost the PID/browser handle.
        # In that case, try to kill any Chrome process running our profile with CDP enabled.
        try:
            import os
            import subprocess
            if os.name == 'nt':
                prof = str(PROFILE_DIR).replace('\\', '\\\\')
                ps = (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*--remote-debugging-port=9222*' -and $_.CommandLine -like '*--user-data-dir="
                    + prof
                    + "*' } | Select-Object -ExpandProperty ProcessId"
                )
                out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps], stderr=subprocess.DEVNULL)
                pids = []
                try:
                    for line in out.decode(errors='ignore').splitlines():
                        s = str(line).strip()
                        if s.isdigit():
                            pids.append(int(s))
                except Exception:
                    pids = []
                for p in pids:
                    try:
                        subprocess.run(["taskkill", "/PID", str(p), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
        except Exception:
            pass

    def close_global_browser(self):
        async def _do():
            await self.close_async()

        with self._lifecycle_lock:
            # 1) Try clean async close
            if self._loop is not None:
                try:
                    self._submit(_do(), timeout=20)
                except Exception:
                    pass
            
            # 2) MANDATORY HARD KILL (fallback for all cases: crash, restart, hang)
            try:
                import os
                import subprocess
                from utils.grok.profile import PROFILE_DIR
                if os.name == 'nt':
                    prof_path = os.path.abspath(PROFILE_DIR)
                    # Convert to double backslash for WMI/PowerShell matching
                    prof_match = prof_path.replace('\\', '\\\\')
                    
                    # Kill by port 9222 OR by profile directory in command line
                    ps_cmd = (
                        "Get-CimInstance Win32_Process | "
                        "Where-Object { "
                        "($_.Name -eq 'chrome.exe') -and "
                        "($_.CommandLine -like '*--remote-debugging-port=9222*' -or $_.CommandLine -like '*--user-data-dir=" + prof_match + "*') "
                        "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    # Unix fallback
                    subprocess.run(["pkill", "-9", "-f", "remote-debugging-port=9222"], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            # Reset state
            self._spawned_pid = None
            
        return True


_GLOBAL_BROWSERS = {
    'default': _GlobalBrowser(),
    'image': _GlobalBrowser(),
    'video': _GlobalBrowser(),
}

# Backward-compatible alias
_GLOBAL_BROWSER = _GLOBAL_BROWSERS['default']


def get_global_browser(kind: str = 'default') -> _GlobalBrowser:
    k = str(kind or 'default').strip().lower()
    if k not in _GLOBAL_BROWSERS:
        k = 'default'
    return _GLOBAL_BROWSERS[k]


def init_global_browser(provider="grok", download_dir=None, kind: str = 'default'):
    get_global_browser(kind).ensure_started(provider=provider, download_dir=download_dir)
    return True


def close_global_browser(kind: str = 'default'):
    return get_global_browser(kind).close_global_browser()


def run_global(coro, timeout=None, provider="grok", kind: str = 'default'):
    """
    Run a coroutine on the global browser's event loop from a different thread.
    This is non-blocking for the Flask main thread.
    """
    gb = get_global_browser(kind)
    gb.ensure_started(provider=provider)
    
    # Sử dụng asyncio.run_coroutine_threadsafe để không block Flask
    future = asyncio.run_coroutine_threadsafe(coro, gb._loop)
    return future.result(timeout=timeout)


def get_global_context(kind: str = 'default'):
    async def _get():
        return await get_global_browser(kind).get_context_async()

    return get_global_browser(kind).run(_get(), timeout=60)


def reset_global_browser(kind: str = 'default'):
    async def _do():
        await get_global_browser(kind).reset_async()

    return get_global_browser(kind).run(_do(), timeout=120)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python control_profile.py <provider>")
    else:
        open_profile(sys.argv[1])