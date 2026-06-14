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
            page.wait_for_selector("table#dataTable", timeout=60000)
            page.wait_for_timeout(2000)

            # 3. Use DataTables 2.x jQuery API on #dataTable to show ALL rows
            print("⚙️ Attempting DataTables API on #dataTable...")
            try:
                result = page.evaluate("""
                    () => {
                        try {
                            if (typeof $ !== 'undefined' && $.fn && $.fn.dataTable &&
                                $.fn.dataTable.isDataTable('#dataTable')) {
                                const table = $('#dataTable').DataTable();
                                const total = table.page.info().recordsTotal;
                                table.page.len(total > 0 ? total : 3000).draw('page');
                                return 'success:' + total;
                            }
                            return 'not-a-datatable';
                        } catch (e) {
                            return 'error:' + e.message;
                        }
                    }
                """)
                print(f"⚙️ DataTables API result: {result}")
            except Exception as e:
                print(f"⚠️ DataTables API approach failed: {e}")
                result = "error"

            # Give the table time to redraw all rows, scroll to force rendering
            page.wait_for_timeout(3000)
            for _ in range(15):
                page.mouse.wheel(0, 3000)
                time.sleep(0.4)
            page.wait_for_timeout(3000)

            # 4. Read pagination info text to verify count
            try:
                info_text = page.locator("text=/Showing.*entries/i").first.inner_text()
                print(f"ℹ️ Pagination info text: {info_text}")
            except Exception as e:
                print(f"⚠️ Could not read pagination info text: {e}")

            # 5. Scrape the table
            all_rows = []
            table_html = page.locator("table#dataTable").first.inner_html()
            df_list = pd.read_html(f"<table>{table_html}</table>")
            raw_df = df_list[0]
            if "Name" in raw_df.columns:
                raw_df = raw_df[raw_df["Name"] != "Name"]
                raw_df = raw_df.dropna(subset=["Name"])
            all_rows.append(raw_df)
            print(f"📋 Rows collected in single-page read: {len(raw_df)}")

            # 6. Fallback: pagination button loop (DataTables 2.x markup)
            if len(raw_df) < 500:
                print("⚠️ Row count too low, falling back to pagination click loop...")
                all_rows = []
                page_num = 1
                previous_first_name = None

                while True:
                    print(f"📜 Scraping page {page_num}...")
                    page.wait_for_timeout(1500)

                    table_html = page.locator("table#dataTable").first.inner_html()
                    df_list = pd.read_html(f"<table>{table_html}</table>")
                    raw_df = df_list[0]
                    if "Name" in raw_df.columns:
                        raw_df = raw_df[raw_df["Name"] != "Name"]
                        raw_df = raw_df.dropna(subset=["Name"])

                    current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                    if page_num > 1 and current_first_name == previous_first_name:
                        print("   ⏳ Table not yet updated, waiting longer...")
                        page.wait_for_timeout(3000)
                        table_html = page.locator("table#dataTable").first.inner_html()
                        df_list = pd.read_html(f"<table>{table_html}</table>")
                        raw_df = df_list[0]
                        if "Name" in raw_df.columns:
                            raw_df = raw_df[raw_df["Name"] != "Name"]
                            raw_df = raw_df.dropna(subset=["Name"])
                        current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                    all_rows.append(raw_df)
                    previous_first_name = current_first_name
                    print(f"   -> {len(raw_df)} rows collected on this page (first item: {current_first_name}).")

                    # DataTables 2.x "Next" button
                    next_btn = page.locator("button.dt-paging-button[data-dt-idx='next']").first

                    if next_btn.count() == 0:
                        print("⚠️ No next button found. Ending pagination.")
                        break

                    is_disabled = next_btn.get_attribute("disabled")
                    aria_disabled = next_btn.get_attribute("aria-disabled")
                    if is_disabled is not None or aria_disabled == "true":
                        print("✅ Reached the last page.")
                        break

                    next_btn.click()
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
