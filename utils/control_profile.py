import asyncio
import threading

from utils.grok.profile import setting_grok_profile, PROFILE_DIR, find_chrome


def open_profile(provider: str):

    if not provider:
        return

    p = provider.strip().lower()

    if p in ["grok", "grok (x-ai)", "x-ai", "xai"]:
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

    def _thread_main(self, provider="grok"):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._provider = provider or "grok"
            self._loop.run_until_complete(self._async_init(provider=provider))
        except Exception as exc:
            self._init_error = exc
        finally:
            self._ready.set()
            if self._loop:
                self._loop.run_forever()

    async def _async_init(self, provider="grok"):
        from playwright.async_api import async_playwright
        import subprocess
        import time

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

        def _kill_profile_chrome_best_effort() -> None:
            # Chỉ dùng khi thật sự cần (tránh làm mất session user đang mở)
            try:
                cmd = f"fuser -k {PROFILE_DIR} 2>/dev/null"
                subprocess.run(cmd, shell=True)
            except Exception:
                pass
            try:
                subprocess.run(
                    "pkill -f 'google-chrome.*--user-data-dir=" + PROFILE_DIR + "'",
                    shell=True,
                )
            except Exception:
                pass

        # NOTE: KHÔNG kill chrome ở đây. Ưu tiên bám vào session/profile đang mở qua CDP.

        chrome_path = find_chrome()
        
        # Stop existing playwright if any
        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass

        self._playwright = await async_playwright().start()

        # Thử kết nối CDP trước nếu Chrome đang mở (để dùng đúng session user vừa login)
        try:
            print("DEBUG: Attempting to connect to existing Chrome via CDP (port 9222)...")
            # Set a short timeout for CDP connection to avoid hanging
            self._browser = await self._playwright.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=5000)
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            print("DEBUG: Successfully connected to existing Chrome session.")
            self._sema = asyncio.Semaphore(5)
            return
        except Exception as e:
            print(f"DEBUG: CDP connection failed (normal if Chrome is closed): {e}")
            self._browser = None
            self._context = None

        # Nếu CDP chưa chạy: tự mở Chrome bằng chính profile dự án (bật 9222) rồi connect lại
        try:
            print(f"DEBUG: CDP not available. Auto-opening Chrome profile for provider={provider}...")
            if provider.lower() in ["grok", "grok (x-ai)"]:
                setting_grok_profile()

            await _wait_cdp_ready(timeout_s=10.0)

            print("DEBUG: Retrying CDP connect after opening Chrome...")
            self._browser = await self._playwright.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=15000)
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            print("DEBUG: Successfully connected to Chrome via CDP after auto-open.")
            self._sema = asyncio.Semaphore(5)
            return
        except Exception as e:
            print(f"DEBUG: Auto-open + CDP connect still failed: {e}")
            self._browser = None
            self._context = None

        # Nếu vẫn fail CDP: fallback cuối cùng = launch_persistent_context.
        # Lúc này mới kill chrome đang giữ profile để tránh 'Opening in existing browser session'.
        print("DEBUG: Falling back to launch_persistent_context (last resort)...")
        _kill_profile_chrome_best_effort()

        # launch persistent context dùng đúng profile dự án
        launch_kwargs = {
            'user_data_dir': PROFILE_DIR,
            'headless': False,
            'ignore_default_args': ['--enable-automation'],
            'args': [
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
                '--password-store=basic',
                '--disable-blink-features=AutomationControlled',
                '--window-position=-5,-5',
                '--window-size=1,1',
            ],
        }
        if chrome_path:
            launch_kwargs['executable_path'] = chrome_path
        else:
            launch_kwargs['channel'] = 'chrome'

        try:
            print(f"DEBUG: Launching persistent context with Chrome: {chrome_path or 'default channel'}")
            self._context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            print("DEBUG: Successfully launched persistent context at (0,-5).")
        except Exception as exc:
            print(f"DEBUG: Failed to launch persistent context: {exc}")
            raise exc
        self._sema = asyncio.Semaphore(5)

    def ensure_started(self, provider="grok"):
        if self._thread and self._thread.is_alive() and self._ready.is_set() and not self._init_error and self._is_context_alive():
            return

        if self._thread and self._thread.is_alive() and self._ready.is_set() and self._init_error:
            raise self._init_error

        self._ready.clear()
        self._init_error = None
        self._thread = threading.Thread(target=self._thread_main, args=(provider,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=60)
        if self._init_error:
            raise self._init_error

    def run(self, coro, timeout=None):
        self.ensure_started()
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    async def get_context_async(self):
        if not self._is_context_alive():
            print("DEBUG: Context is dead or browser disconnected. Re-initializing...")
            await self._async_init(provider=self._provider)
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
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser is not None:
            try:
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
        await self._async_init()


_GLOBAL_BROWSER = _GlobalBrowser()


def init_global_browser(provider="grok"):
    _GLOBAL_BROWSER.ensure_started(provider=provider)
    return True


def run_global(coro, timeout=None, provider="grok"):
    """
    Run a coroutine on the global browser's event loop from a different thread.
    This is non-blocking for the Flask main thread.
    """
    from utils.control_profile import _GLOBAL_BROWSER
    _GLOBAL_BROWSER.ensure_started(provider=provider)
    
    # Sử dụng asyncio.run_coroutine_threadsafe để không block Flask
    future = asyncio.run_coroutine_threadsafe(coro, _GLOBAL_BROWSER._loop)
    return future.result(timeout=timeout)


def get_global_context():
    async def _get():
        return await _GLOBAL_BROWSER.get_context_async()

    return _GLOBAL_BROWSER.run(_get(), timeout=60)


def reset_global_browser():
    async def _do():
        await _GLOBAL_BROWSER.reset_async()

    return _GLOBAL_BROWSER.run(_do(), timeout=120)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python control_profile.py <provider>")
    else:
        open_profile(sys.argv[1])