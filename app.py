import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(
    page_title="Hafiz Hardware | Price Desk",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- CUSTOM STYLING ----------
st.markdown("""
    <style>
        .main-header {
            text-align: center;
            padding: 1rem 0 0.5rem 0;
        }
        .main-header h1 {
            color: #1B3A5C;
            font-size: 2.2rem;
            margin-bottom: 0;
        }
        .main-header p {
            color: #4F7FA3;
            font-size: 1rem;
            margin-top: 0;
            font-weight: 500;
        }
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 1.5px solid #1B3A5C;
            padding: 0.6rem;
            font-size: 1rem;
        }
        .footer-note {
            text-align: center;
            color: #999;
            font-size: 0.8rem;
            margin-top: 2rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.3rem;
            color: #1B3A5C;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
    <div class="main-header">
        <h1>🔧 Hafiz Hardware</h1>
        <p>LIVE SALESMAN PRICE DESK</p>
    </div>
""", unsafe_allow_html=True)

st.divider()

# ---------- LOAD DATA ----------
@st.cache_data(ttl=600)
def load_synced_data():
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, "salesman_prices.xlsx")
        df = pd.read_excel(file_path)
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        return df, last_modified
    except Exception:
        return pd.DataFrame(), None

df, last_synced = load_synced_data()

# ---------- MAIN CONTENT ----------
if df.empty:
    st.error("⚠️ Pricing database synchronization in progress. Please try again in a minute.")
else:
    # Summary metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Products", f"{len(df):,}")
    with col2:
        in_stock_count = (df["Stock Quantity"] > 0).sum() if "Stock Quantity" in df.columns else 0
        st.metric("In Stock Items", f"{in_stock_count:,}")
    with col3:
        if last_synced:
            st.metric("Last Synced", last_synced.strftime("%I:%M %p"))
        else:
            st.metric("Last Synced", "—")

    st.write("")

    # Search box
    search_keyword = st.text_input(
        "🔍 Search Product",
        placeholder="e.g., pipe, watti, bolt, handle...",
        autocomplete="off",
        label_visibility="visible"
    )

    st.write("")

    if search_keyword:
        results = df[df["Item Name"].str.contains(search_keyword, case=False, na=False)]

        if not results.empty:
            st.success(f"✅ Found {len(results)} matching item(s)")

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Item Name": st.column_config.TextColumn("Product", width="large"),
                    "Stock Quantity": st.column_config.NumberColumn("In Stock", format="%d"),
                    "Purchase Price": st.column_config.NumberColumn("Cost Price (Bargain Floor)", format="Rs. %d"),
                    "Retail Price": st.column_config.NumberColumn("Selling Price", format="Rs. %d")
                }
            )
        else:
            st.warning("❌ No matching inventory found. Try a different keyword.")
    else:
        st.info("💡 Start typing a product name above to view live stock and pricing.")

    # ---------- FOOTER ----------
    st.markdown("""
        <div class="footer-note">
            Hafiz Hardware Internal Tool · Prices auto-sync hourly · For salesman use only
        </div>
    """, unsafe_allow_html=True)
