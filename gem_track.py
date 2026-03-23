import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 頁面配置
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("自動同步 PoEDB 中文翻譯與顏色屬性")

# --- 1. 自動從 PoEDB 抓取對照表 (強化解析版) ---
@st.cache_data(ttl=86400)
def get_poedb_mapping():
    # 針對轉換寶石專用頁面抓取，結構最穩定
    url = "https://poedb.tw/tw/Transfigured_Gems"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    gem_map = {}
    try:
        resp = requests.get(url, headers=headers)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 尋找所有 <a> 標籤，這類連結通常包含中英文資訊
        # PoEDB 的結構中，data-en 屬性存放英文，text 存放中文
        for link in soup.find_all('a', {'data-en': True}):
            en_name = link.get('data-en')
            zh_name = link.get_text().strip()
            
            # 排除非轉換寶石的雜項
            if " of " in en_name:
                # 判定顏色：檢查該行 (tr) 或連結的 class
                # 根據 PoEDB 慣例，不同屬性寶石會有不同 CSS class 或鄰近文字
                parent_row = link.find_parent('tr')
                color_icon = "⚪"
                
                if parent_row:
                    row_text = parent_row.get_text()
                    # 依據標籤內容判定
                    if "力量" in row_text or "火" in row_text: color_icon = "🔴"
                    elif "敏捷" in row_text or "冰" in row_text: color_icon = "🟢"
                    elif "智慧" in row_text or "電" in row_text: color_icon = "🔵"
                
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
            # 如果 mapping 裡沒找到，回傳 (原始名稱, ⚪)
            return mapping.get(en_name, (en_name, "⚪"))
            
        df['中文'], df['色'] = zip(*df['name'].map(apply_info))
        
        # 整理輸出
        res = df[['色', '中文', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['⚪', '寶石名稱', '英文原名', '等級', 'C', 'D']
        return res.sort_values('C', ascending=False)
    except:
        return pd.DataFrame()

# --- 3. UI 主介面 ---
with st.spinner('正在同步 PoEDB 翻譯中...'):
    mapping = get_poedb_mapping()
    df = fetch_ninja_data(mapping)

if not df.empty:
    # 搜尋過濾
    search = st.text_input("🔍 搜尋名稱 (例如：冰霜新星 或 Ice Nova)", "")
    
    # 篩選邏輯
    mask = df['寶石名稱'].str.contains(search, case=False) | df['英文原名'].str.contains(search, case=False)
    final_df = df[mask]

    # 顯示表格
    st.dataframe(
        final_df,
        use_container_width=True,
        height=700,
        column_config={
            "C": st.column_config.NumberColumn("混沌石 (C)", format="%d"),
            "D": st.column_config.NumberColumn("神聖石 (D)", format="%.2f"),
        },
        hide_index=True
    )
else:
    st.warning("無法載入資料，請確認網路或 API 狀態。")
