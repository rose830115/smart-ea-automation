from __future__ import annotations

import base64
import time
from pathlib import Path

BASE_URL = "https://mrc.ycmproducts.com"


def playwright_login(account: str, password: str, base_url: str = BASE_URL) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{base_url}/login", wait_until="networkidle", timeout=40000)

            # Screenshot 1: what the page looks like on load
            shot1 = page.screenshot()

            # Try to find and fill the form
            try:
                page.wait_for_selector("input", timeout=10000)
            except Exception:
                raise RuntimeError(
                    f"找不到登入表單（頁面 URL: {page.url}）",
                    base64.b64encode(shot1).decode(),
                )

            inputs = page.locator("input").all()
            input_info = [
                f"type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')}"
                for inp in inputs
            ]

            account_input = page.locator("input").first
            password_input = page.locator("input[type='password']").first

            account_input.fill(account)
            password_input.fill(password)

            # Screenshot 2: after filling
            shot2 = page.screenshot()

            page.get_by_role("button", name="登入").click()

            deadline = time.time() + 20
            while "/login" in page.url and time.time() < deadline:
                time.sleep(0.3)

            shot3 = page.screenshot()

            if "/login" in page.url:
                raise RuntimeError(
                    f"登入後仍停留在登入頁（inputs: {input_info}）",
                    base64.b64encode(shot2).decode(),
                    base64.b64encode(shot3).decode(),
                )

            token = page.evaluate("localStorage.getItem('lab_admins_token')")
            if not token:
                raise RuntimeError("登入成功但找不到 token，請聯絡管理員")

            return token
        finally:
            browser.close()


def login_with_debug(account: str, password: str) -> tuple[str | None, list[str], str | None]:
    """Returns (token, screenshots_b64_list, error_message)"""
    try:
        token = playwright_login(account, password)
        return token, [], None
    except RuntimeError as e:
        args = e.args
        msg = args[0]
        shots = list(args[1:])
        return None, shots, msg
    except Exception as e:
        return None, [], str(e)
