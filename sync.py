import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd

PORTAL_URL = "https://hafizhardware.bahestech.com"
ITEMS_TABLE_URL = "https://hafizhardware.bahestech.com/admin/products"

USERNAME = os.environ.get('STORE_USER')
PASSWORD = os.environ.get('STORE_PASS')

USER_BOX = "input[placeholder='Enter E-mail']"
PASS_BOX = "input[placeholder='Enter Password']"
LOGIN_BTN = "button:has-text('Login'), input[type='submit']"

def run_scraper():
    print("🚀 Booting heavy-load background cloud browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        try:
            page.goto(PORTAL_URL, timeout=90000)
            page.wait_for_selector(USER_BOX, timeout=20000)
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            print("🔒 Logged in successfully.")

            print("⏳ Navigating to products dashboard (Allowing extra time for 2,000+ items)...")
            page.goto(ITEMS_TABLE_URL, timeout=180000)
            page.wait_for_selector("table", timeout=60000)

            print("📜 Scrolling data rows to ensure complete rendering...")
            for _ in range(5):
                page.mouse.wheel(0, 2000)
                time.sleep(1)

            page.wait_for_load_state("networkidle")

            table_html = page.locator("table").first.inner_html()
            df_list = pd.read_html(f"<table>{table_html}</table>")
            raw_df = df_list[0]

            print(f"📋 Data extracted successfully! Rows found: {len(raw_df)}")

            salesman_view = raw_df[["Name", "Sale Price"]].copy()
            salesman_view.columns = ["Item Name", "Retail Price"]

            salesman_view.to_excel("salesman_prices.xlsx", index=False)
            print("✅ 'salesman_prices.xlsx' fully populated with actual hardware rates!")

        except Exception as error_log:
            print(f"❌ Processing interruption: {error_log}")
            if not os.path.exists("salesman_prices.xlsx"):
                df_err = pd.DataFrame([{"Item Name": "System updating, please check back shortly.", "Retail Price": 0}])
                df_err.to_excel("salesman_prices.xlsx", index=False)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
