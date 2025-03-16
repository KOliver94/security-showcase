import os
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(os.environ.get('APPLICATION_URL', "http://localhost:5000"))

    print("Starting login...")
    page.fill("input[name='username']", "charlie")
    page.fill("input[name='password']", "+An~vt2gPP=XViV%qjP%")
    page.get_by_role("button", name="Sign in").click()
    print("Login complete ✓")

    try:
        while True:
            print(f"Next page loading will be at {datetime.now() + timedelta(minutes = 1)}...")
            time.sleep(60)
            page.reload()
            print("Refresh complete ✓")
    except KeyboardInterrupt:
        print("Stopping script.")
        browser.close()
