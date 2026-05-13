from __future__ import annotations

import time

BASE_URL = "https://mrc.ycmproducts.com"


def playwright_login(account: str, password: str, base_url: str = BASE_URL) -> str:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{base_url}/login", wait_until="domcontentloaded", timeout=30000)

            page.get_by_placeholder("帳號").fill(account)
            page.get_by_placeholder("密碼").fill(password)
            page.get_by_role("button", name="登入").click()

            # Wait for redirect away from /login
            deadline = time.time() + 20
            while "/login" in page.url and time.time() < deadline:
                time.sleep(0.3)

            if "/login" in page.url:
                raise RuntimeError("登入後仍停留在登入頁，請確認帳號密碼是否正確")

            token = page.evaluate("localStorage.getItem('lab_admins_token')")
            if not token:
                raise RuntimeError("登入成功但找不到 token，請聯絡管理員")

            return token
        finally:
            browser.close()
