"""
LEO Browser State Sandbox

Rule:
- Never launch Chrome/Edge.
- Use only an already-running browser.
- If no compatible browser is running, return a clear failure.
"""

import asyncio
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class ExistingBrowserController:
    def __init__(self, browser_type: str = "chrome"):
        browser_type = browser_type.lower().strip()

        if browser_type not in {"chrome", "edge"}:
            raise ValueError("browser_type must be 'chrome' or 'edge'")

        self.browser_type = browser_type
        self._playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def connect(self) -> BrowserContext:
        """
        Attach to an already-running Chromium browser.

        IMPORTANT:
        This function NEVER launches Chrome or Edge.
        """

        self._playwright = await async_playwright().start()

        executable = "chrome" if self.browser_type == "chrome" else "msedge"

        # Connect through the browser's CDP endpoint.
        # The browser must already be running with remote debugging enabled.
        port = 9222 if self.browser_type == "chrome" else 9223

        try:
            self.browser = await self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}"
            )
        except Exception as exc:
            await self.close()
            raise RuntimeError(
                f"Existing {executable} was not available on CDP port {port}. "
                f"Leo will NOT launch a new browser. Error: {exc}"
            )

        contexts = self.browser.contexts

        if not contexts:
            await self.close()
            raise RuntimeError(
                f"Existing {executable} connected, but no browser context was found."
            )

        self.context = contexts[0]
        return self.context

    async def get_existing_page(self) -> Page:
        """Return the currently available page from the existing browser."""

        if self.context is None:
            await self.connect()

        pages = self.context.pages

        if not pages:
            raise RuntimeError(
                f"No existing tab found in {self.browser_type}. "
                "Leo will not create a new browser."
            )

        return pages[-1]

    async def open_url(self, url: str) -> Page:
        """
        Navigate an existing tab.

        No new browser is created.
        No new tab is created.
        """

        page = await self.get_existing_page()
        await page.goto(url, wait_until="domcontentloaded")
        return page

    async def close(self):
        """
        Disconnect only.

        Do NOT close the user's actual Chrome/Edge process.
        """

        self.browser = None
        self.context = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass

            self._playwright = None


async def test_browser(browser_type: str, url: str):
    controller = ExistingBrowserController(browser_type)

    try:
        page = await controller.open_url(url)

        print("=" * 50)
        print(f"BROWSER: {browser_type.upper()}")
        print(f"MODE: EXISTING BROWSER ONLY")
        print(f"PAGE: {page.url}")
        print(f"TITLE: {await page.title()}")
        print("=" * 50)

    except Exception as exc:
        print(f"[FAILED] {browser_type}: {exc}")

    finally:
        await controller.close()


async def main():
    # Test Chrome first.
    await test_browser("chrome", "https://www.youtube.com")

    # Then Edge.
    await test_browser("edge", "https://www.youtube.com")


if __name__ == "__main__":
    asyncio.run(main())