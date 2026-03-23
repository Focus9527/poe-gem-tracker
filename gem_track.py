import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# 頁面配置
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格 (PoEDB 自動對照版)")

# --- 1. 自動從 PoEDB 抓取對照表 ---
@st.cache_data(ttl=86400) # 每天抓一次對照表即可
def get_poedb_mapping():
    # 使用中文頁面來抓取「中文 vs 英文」的關係
    url_zh = "https://poedb.tw/tw/Skill_Gems"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    gem_map = {}
    try:
        resp = requests.get(url_zh, headers=headers)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 尋找所有寶石連結
        links = soup.select('a[href*="/tw/"]')
        
        for link in links:
            en_name = link.get('data-en') # 這是核心：PoEDB 標註的英文原名
            zh_name = link.text.strip()
            
            if en_name and " of " in en_name: # 確保是轉換寶石
                # 簡單判定顏色 (從父層抓取屬性或標籤)
                parent_text = link.find_parent('td').find_next_sibling('td').text if link.find_parent('td') and link.find_parent('td').find_next_sibling('td') else ""
                
                color = "⚪"
                if "力量" in parent_text: color = "🔴"
                elif "敏捷" in parent_text: color = "🟢"
                elif "智慧" in parent_text: color = "🔵"
                
                gem_map[en_name] = (zh_name, color)
        
        return gem_map
    except Exception as e:
        st.error(f"對照表抓取錯誤: {e}")
        return {}

# --- 2. 抓取 poe.ninja 價格 ---
@st.cache_data(ttl=1800)
def fetch_ninja_data(mapping):
    # 使用 Mirage 賽季 API
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選：轉換寶石(of) + 非瓦爾
        df = df[df['name'].str.contains(' of ', na=False) & df['corrupted'].isna()]
        
        # 匹配中文與顏色
        def apply_info(en_name):
            return mapping.get(en_name, (en_name, "⚪"))
            
        df['中文'], df['色'] = zip(*df['name'].map(apply_info))
        
        # 整理欄位
        res = df[['色', '中文', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['⚪', '寶石名稱', '英文原名', '等級', 'C', 'D']
        return res.sort_values('C', ascending=False)
    except:
        return pd.DataFrame()

# --- 3. UI 介面 ---
with st.spinner('正在同步 PoEDB 翻譯與 Ninja 價格...'):
    mapping = get_poedb_mapping()
    df = fetch_ninja_data(mapping)

if not df.empty:
    # 搜尋與工具欄
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 搜尋 (支援中英文)", placeholder="例如：Ice Nova 或 冰霜新星")
    with col2:
        color_filter = st.selectbox("顏色篩選", ["全部", "🔴 紅色", "🟢 綠色", "🔵 藍色"])

    # 執行篩選
    final_df = df[df['寶石名稱'].str.contains(search, case=False) | df['英文原名'].str.contains(search, case=False)]
    if color_filter != "全部":
        final_df = final_df[final_df['⚪'] == color_filter.split(" ")[0]]

    # 顯示主表格
    st.dataframe(
        final_df,
        use_container_width=True,
        height=700,
        column_config={
            "C": st.column_config.NumberColumn("價格 (C)", format="%d"),
            "D": st.column_config.NumberColumn("價格 (D)", format="%.2f"),
            "等級": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    st.caption(f"最後更新時間：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("無法載入資料，請確認網路連接或 API 狀態。")
