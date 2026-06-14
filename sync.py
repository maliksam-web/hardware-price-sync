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
            # 1. Login
            page.goto(PORTAL_URL, timeout=90000)
            page.wait_for_selector(USER_BOX, timeout=20000)
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            print("🔒 Logged in successfully.")

            # 2. Open products page
            print("⏳ Navigating to products dashboard...")
            page.goto(ITEMS_TABLE_URL, timeout=180000)
            page.wait_for_selector("table", timeout=60000)
            page.wait_for_timeout(2000)

            # 3. Use DataTables JS API to show ALL rows on one page
            print("⚙️ Attempting to set table page length to show all rows via DataTables API...")
            try:
                result = page.evaluate("""
                    () => {
                        if (typeof $ === 'undefined' || !$.fn || !$.fn.dataTable) {
                            return 'no-jquery-datatables';
                        }
                        var tables = $.fn.dataTable.tables({visible: true, api: true});
                        if (tables.length === 0) {
                            return 'no-tables-found';
                        }
                        tables.page.len(5000).draw(false);
                        return 'success';
                    }
                """)
                print(f"⚙️ DataTables API result: {result}")
            except Exception as e:
                print(f"⚠️ DataTables API approach failed: {e}")
                result = "error"

            # Give the table time to render all rows, with scrolling to force rendering
            page.wait_for_timeout(3000)
            for _ in range(10):
                page.mouse.wheel(0, 3000)
                time.sleep(0.5)
            page.wait_for_timeout(3000)

            # 4. Read pagination info text to verify how many rows are showing
            try:
                info_text = page.locator("text=/Showing.*entries/i").first.inner_text()
                print(f"ℹ️ Pagination info text: {info_text}")
            except Exception as e:
                print(f"⚠️ Could not read pagination info text: {e}")

            # 5. Scrape the table
            all_rows = []
            table_html = page.locator("table").first.inner_html()
            df_list = pd.read_html(f"<table>{table_html}</table>")
            raw_df = df_list[0]
            if "Name" in raw_df.columns:
                raw_df = raw_df[raw_df["Name"] != "Name"]
                raw_df = raw_df.dropna(subset=["Name"])
            all_rows.append(raw_df)
            print(f"📋 Rows collected in single-page read: {len(raw_df)}")

            # 6. Fallback: if DataTables API didn't work, loop through pagination pages
            if len(raw_df) < 500:
                print("⚠️ Row count too low, falling back to pagination click loop...")
                all_rows = []
                page_num = 1
                previous_first_name = None

                while True:
                    print(f"📜 Scraping page {page_num}...")
                    page.wait_for_timeout(2000)

                    table_html = page.locator("table").first.inner_html()
                    df_list = pd.read_html(f"<table>{table_html}</table>")
                    raw_df = df_list[0]
                    if "Name" in raw_df.columns:
                        raw_df = raw_df[raw_df["Name"] != "Name"]
                        raw_df = raw_df.dropna(subset=["Name"])

                    current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                    if page_num > 1 and current_first_name == previous_first_name:
                        print("   ⏳ Table not yet updated, waiting longer...")
                        page.wait_for_timeout(4000)
                        table_html = page.locator("table").first.inner_html()
                        df_list = pd.read_html(f"<table>{table_html}</table>")
                        raw_df = df_list[0]
                        if "Name" in raw_df.columns:
                            raw_df = raw_df[raw_df["Name"] != "Name"]
                            raw_df = raw_df.dropna(subset=["Name"])
                        current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                    all_rows.append(raw_df)
                    previous_first_name = current_first_name
                    print(f"   -> {len(raw_df)} rows collected on this page (first item: {current_first_name}).")

                    next_button = None
                    candidates = [
                        "a[rel='next']",
                        "li.paginate_button.next a",
                        "a[aria-label='Next']",
                        "a:has-text('Next')",
                        "a:has-text('»')",
                        "a:has-text('›')",
                    ]

                    for sel in candidates:
                        loc = page.locator(sel).last
                        if loc.count() > 0:
                            try:
                                if loc.is_visible() and loc.is_enabled():
                                    next_button = loc
                                    break
                            except Exception:
                                continue

                    if next_button is None:
                        print("⚠️ No next button found. Ending pagination.")
                        break

                    try:
                        parent_class = next_button.locator("xpath=..").get_attribute("class") or ""
                        if "disabled" in parent_class:
                            print("✅ Reached the last page.")
                            break
                    except Exception:
                        pass

                    next_button.click()
                    page_num += 1

                    if page_num > 250:
                        print("⚠️ Safety cap reached, stopping pagination loop.")
                        break

            # 7. Combine, dedupe, and save
            full_df = pd.concat(all_rows, ignore_index=True)
            print(f"📋 Total rows collected across all pages (before dedupe): {len(full_df)}")

            salesman_view = full_df[["Name", "Quantity", "Purchase Price", "Sale Price"]].copy()
            salesman_view.columns = ["Item Name", "Stock Quantity", "Purchase Price", "Retail Price"]
            salesman_view = salesman_view.dropna(subset=["Item Name"])
            salesman_view = salesman_view.drop_duplicates(subset=["Item Name"], keep="first")

            salesman_view.to_excel("salesman_prices.xlsx", index=False)
            print(f"✅ 'salesman_prices.xlsx' fully populated with {len(salesman_view)} hardware rates!")

        except Exception as error_log:
            print(f"❌ Processing interruption: {error_log}")
            if not os.path.exists("salesman_prices.xlsx"):
                df_err = pd.DataFrame([{
                    "Item Name": "System updating, please check back shortly.",
                    "Stock Quantity": 0,
                    "Purchase Price": 0,
                    "Retail Price": 0
                }])
                df_err.to_excel("salesman_prices.xlsx", index=False)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
