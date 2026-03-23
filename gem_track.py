import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 網頁基礎設定
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("資料來源：poe.ninja | 翻譯與顏色同步：PoEDB (Skill_Gems)")

# --- 1. 從 PoEDB 抓取精確的顏色與中文對照表 ---
@st.cache_data(ttl=86400)
def get_poedb_mapping():
    # 這裡使用中文版頁面，確保能抓到中文名稱與 data-en (英文原名) 的對應
    url = "https://poedb.tw/tw/Skill_Gems"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    gem_map = {}
    # PoEDB 頁面中，紅色、綠色、藍色寶石分別在不同的 ID 區塊下
    color_sections = {
        "SkillGemsRed": "🔴",
        "SkillGemsGreen": "🟢",
        "SkillGemsBlue": "🔵"
    }
    
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for section_id, icon in color_sections.items():
            section = soup.find(id=section_id)
            if section:
                # 抓取該區塊內所有具備 data-en 屬性的 <a> 標籤
                links = section.find_all('a', attrs={'data-en': True})
                for link in links:
                    en_name = link.get('data-en')      # 英文原名 (Key)
                    zh_name = link.get_text().strip()  # 中文翻譯 (Value)
                    gem_map[en_name] = (zh_name, icon)
        
        return gem_map
    except Exception as e:
        st.error(f"PoEDB 對照表讀取失敗: {e}")
        return {}

# --- 2. 抓取 poe.ninja 價格並進行欄位對照 ---
@st.cache_data(ttl=1800)
def fetch_ninja_data(mapping):
    # 設定賽季為 Mirage
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選：只要「轉換寶石(名稱含 of)」且「非瓦爾(corrupted 為 NaN)」
        df = df[df['name'].str.contains(' of ', na=False) & df['corrupted'].isna()]
        
        # 執行 Mapping：將 Ninja 的英文名丟進 PoEDB 對照表
        def do_mapping(en_name):
            # 查找中文名與顏色圖示，若找不到則回傳原名與白色
            return mapping.get(en_name, (en_name, "⚪"))
            
        df['中文名稱'], df['顏色'] = zip(*df['name'].map(do_mapping))
        
        # 重新排列與命名欄位，符合您的需求
        # 排序：顏色 -> 中文名稱 -> 英文名稱 -> 等級 -> C價 -> D價
        res = df[['顏色', '中文名稱', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['屬性', '中文名稱', '英文名稱', '等級', '價格 (C)', '價格 (D)']
        
        return res.sort_values('價格 (C)', ascending=False)
    except Exception as e:
        st.error(f"Ninja 資料抓取失敗: {e}")
        return pd.DataFrame()

# --- 3. Streamlit UI 介面 ---
with st.spinner('同步 PoEDB 翻譯數據中...'):
    mapping_table = get_poedb_mapping()
    final_df = fetch_ninja_data(mapping_table)

if not final_df.empty:
    # 側邊欄過濾功能
    st.sidebar.header("🔍 篩選與搜尋")
    search_query = st.sidebar.text_input("搜尋 (支援中/英文)", "")
    
    color_options = ["全部", "🔴 紅色寶石 (力量)", "🟢 綠色寶石 (敏捷)", "🔵 藍色寶石 (智慧)"]
    selected_color = st.sidebar.selectbox("依屬性篩選", color_options)
    
    # 執行過濾邏輯
    output_df = final_df.copy()
    
    if search_query:
        mask = output_df['中文名稱'].str.contains(search_query, case=False) | \
               output_df['英文名稱'].str.contains(search_query, case=False)
        output_df = output_df[mask]
        
    if selected_color != "全部":
        target_icon = selected_color.split(" ")[0]
        output_df = output_df[output_df['屬性'] == target_icon]

    # 主要表格展示
    st.markdown(f"### 目前顯示 **{len(output_df)}** 筆轉換寶石數據")
    st.dataframe(
        output_df,
        use_container_width=True,
        height=750,
        column_config={
            "價格 (C)": st.column_config.NumberColumn(format="%d C"),
            "價格 (D)": st.column_config.NumberColumn(format="%.2f D"),
            "等級": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    # 側邊欄下載 CSV 功能
    csv = output_df.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button("📥 下載目前的資料表", csv, "poe_gem_prices.csv", "text/csv")

else:
    st.warning("無法取得資料，請重新整理頁面或檢查網路。")
