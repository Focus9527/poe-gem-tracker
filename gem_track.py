import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 頁面配置
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("同步自 PoEDB (Skill_Gems) 中文翻譯與屬性顏色")

# --- 1. 從 PoEDB Skill_Gems 總表抓取對照表 ---
@st.cache_data(ttl=86400)
def get_poedb_mapping():
    url = "https://poedb.tw/tw/Skill_Gems"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    gem_map = {}
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 在 Skill_Gems 頁面中，所有的寶石連結都有 data-en 屬性
        # 我們直接抓取所有具備 data-en 的 <a> 標籤
        for link in soup.find_all('a', attrs={'data-en': True}):
            en_name = link.get('data-en')
            zh_name = link.get_text().strip()
            
            # 只要是轉換寶石 (包含 " of ")
            if " of " in en_name:
                # 判定顏色：根據 PoEDB 的 CSS Class 或父層結構
                # 力量寶石通常在特定的 td 或有對應的文字
                parent_td = link.find_parent('td')
                color_icon = "⚪"
                
                if parent_td:
                    # 往後找標籤欄位 (Tags)
                    sibling_tds = parent_td.find_next_siblings('td')
                    if sibling_tds:
                        tags_text = sibling_tds[0].get_text()
                        if "力量" in tags_text: color_icon = "🔴"
                        elif "敏捷" in tags_text: color_icon = "🟢"
                        elif "智慧" in tags_text: color_icon = "🔵"
                
                gem_map[en_name] = (zh_name, color_icon)
        
        return gem_map
    except Exception as e:
        st.error(f"對照表抓取失敗: {e}")
        return {}

# --- 2. 抓取 poe.ninja 價格 ---
@st.cache_data(ttl=1800)
def fetch_ninja_data(mapping):
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選轉換寶石與非瓦爾
        df = df[df['name'].str.contains(' of ', na=False) & df['corrupted'].isna()]
        
        # 執行配對
        def apply_info(en_name):
            # 優先從 mapping 找，找不到則顯示原名
            return mapping.get(en_name, (en_name, "⚪"))
            
        df['中文'], df['色'] = zip(*df['name'].map(apply_info))
        
        # 整理輸出欄位
        res = df[['色', '中文', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['屬性', '寶石中文名稱', '英文原名', '等級', 'C', 'D']
        return res.sort_values('C', ascending=False)
    except:
        return pd.DataFrame()

# --- 3. UI 主介面 ---
with st.spinner('正在讀取 PoEDB 中文資料...'):
    mapping = get_poedb_mapping()
    df = fetch_ninja_data(mapping)

if not df.empty:
    # 側邊欄過濾
    st.sidebar.header("過濾選項")
    search = st.sidebar.text_input("🔍 搜尋 (中英文皆可)", "")
    min_c = st.sidebar.number_input("最低 C 價", value=0)
    
    # 套用過濾
    mask = (df['寶石中文名稱'].str.contains(search, case=False) | df['英文原名'].str.contains(search, case=False)) & (df['C'] >= min_c)
    final_df = df[mask]

    # 顯示表格
    st.dataframe(
        final_df,
        use_container_width=True,
        height=800,
        column_config={
            "C": st.column_config.NumberColumn("價格 (C)", format="%d"),
            "D": st.column_config.NumberColumn("價格 (D)", format="%.2f"),
        },
        hide_index=True
    )
    
    st.success(f"成功加載 {len(final_df)} 顆寶石資料")
else:
    st.warning("無法載入資料，請確認 API 狀態。")
