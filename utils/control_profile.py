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

    def _is_context_alive(self) -> bool:
        ctx = self._context
        if ctx is None:
            return False
        try:
            # Accessing pages will throw if context is closed
            _ = ctx.pages
            return True
        except Exception:
            return False

    def _thread_main(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._async_init())
        except Exception as exc:
            self._init_error = exc
        finally:
            self._ready.set()
            if self._loop:
                self._loop.run_forever()

    async def _async_init(self):
        from playwright.async_api import async_playwright

        chrome_path = find_chrome()
        self._playwright = await async_playwright().start()

        launch_kwargs = {
            'user_data_dir': PROFILE_DIR,
            'headless': False,
            # Reduce automation fingerprinting (Cloudflare may block Playwright default flags)
            'ignore_default_args': ['--enable-automation'],
            'args': [
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
                '--password-store=basic',
                '--disable-blink-features=AutomationControlled',
            ],
        }
        if chrome_path:
            launch_kwargs['executable_path'] = chrome_path
        else:
            # Prefer system Chrome channel when available
            launch_kwargs['channel'] = 'chrome'

        try:
            self._browser = None
            self._context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as exc:
            msg = str(exc)
            # When Chrome is already running with the same --user-data-dir, Playwright may log:
            # "Opening in existing browser session." and then the target is closed.
            if 'Opening in existing browser session' in msg or 'Target page, context or browser has been closed' in msg:
                # Fallback: connect to the already-open Chrome session via CDP
                # This keeps login/Cloudflare state exactly as the user verified.
                try:
                    self._browser = await self._playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
                    self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
                except Exception as exc2:
                    raise RuntimeError(
                        f"Profile đang được một phiên Chrome khác sử dụng: {PROFILE_DIR}. "
                        "Nếu bạn muốn dùng luôn phiên Chrome đó, hãy mở Chrome bằng nút 'THIẾT LẬP TÀI KHOẢN' (có bật remote debugging port 9222) rồi thử lại. "
                        "Hoặc đóng toàn bộ Chrome đang dùng profile này và chạy lại. "
                        f"CDP error: {exc2}"
                    ) from exc
                
            else:
                raise
        self._sema = asyncio.Semaphore(5)

    def ensure_started(self):
        if self._thread and self._thread.is_alive() and self._ready.is_set() and not self._init_error and self._is_context_alive():
            return

        if self._thread and self._thread.is_alive() and self._ready.is_set() and self._init_error:
            raise self._init_error

        self._ready.clear()
        self._init_error = None
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
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
            await self._async_init()
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


def init_global_browser():
    _GLOBAL_BROWSER.ensure_started()
    return True


def run_global(coro, timeout=None):
    return _GLOBAL_BROWSER.run(coro, timeout=timeout)


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