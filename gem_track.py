import streamlit as st
import pandas as pd
import requests

# 設定網頁標題
st.set_page_config(page_title="PoE Mirage 轉換寶石價格追蹤", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("資料來源：poe.ninja API | 自動過濾非瓦爾、等級 20 之轉換寶石")

# 1. 抓取資料的函式
@st.cache_data(ttl=3600)  # 快取 1 小時，避免頻繁請求 API
def fetch_data():
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選轉換寶石 (名稱含 of) 且非瓦爾 (corrupted 為空)
        df = df[df['name'].str.contains(' of ', na=False)]
        df = df[df['corrupted'].isna()]
        
        # 整理輸出欄位
        df = df[['name', 'gemLevel', 'chaosValue', 'divineValue', 'listingCount']]
        df.columns = ['寶石名稱', '等級', '混沌石(C)', '神聖石(D)', '掛單數']
        return df.sort_values('混沌石(C)', ascending=False)
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return pd.DataFrame()

# 2. 執行抓取
data = fetch_data()

if not data.empty:
    # 側邊欄過濾器
    search_query = st.sidebar.text_input("🔍 搜尋寶石名稱", "")
    min_price = st.sidebar.slider("💰 最低 C 價篩選", 0, 1000, 10)
    
    # 套用篩選
    display_df = data[data['寶石名稱'].str.contains(search_query, case=False)]
    display_df = display_df[display_df['混沌石(C)'] >= min_price]

    # 3. 顯示數據表格
    st.dataframe(display_df, use_container_width=True, height=600)

    # 4. 下載功能
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載目前的價格表 (CSV)", csv, "mirage_gems.csv", "text/csv")
else:
    st.warning("目前無法取得資料，請確認 API 網址是否正確。")