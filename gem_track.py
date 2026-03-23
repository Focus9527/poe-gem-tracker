import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 網頁配置
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("同步源：poe.ninja | 翻譯與顏色：PoEDB (Skill_Gems)")

# --- 1. 手動保底 Mapping (避免爬蟲失效時全英文) ---
STATIC_MAP = {
    "Kinetic Blast of Clustering": ("爆靈術：聚能", "🔵"),
    "Molten Strike of the Zenith": ("熔岩打擊：巔峰", "🔴"),
    "Viper Strike of the Mamba": ("毒蛇打擊：曼巴", "🟢"),
    "Animate Guardian of Smiting": ("喚醒守衛：重擊", "🔵"),
    "Ethereal Knives of the Massacre": ("飛刃風暴：屠殺", "🟢"),
    "Cyclone of Tumult": ("旋風斬：騷亂", "🟢"),
    "Double Strike of Momentum": ("雙重打擊：動量", "🔴"),
    "Ice Nova of Frostbolts": ("冰霜新星：冰霜彈", "🔵"),
}

# --- 2. 強化版 PoEDB 爬蟲 ---
@st.cache_data(ttl=86400)
def get_poedb_mapping():
    url = "https://poedb.tw/tw/Skill_Gems"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    gem_map = STATIC_MAP.copy()
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 定義分區
        sections = {"SkillGemsRed": "🔴", "SkillGemsGreen": "🟢", "SkillGemsBlue": "🔵"}
        
        for s_id, icon in sections.items():
            container = soup.find(id=s_id)
            if not container:
                # 備案：如果找不到 ID，找包含該名稱的 Table
                container = soup.find('h1', text=lambda t: t and s_id[9:] in t)
                if container: container = container.find_next('table')

            if container:
                links = container.find_all('a', attrs={'data-en': True})
                for link in links:
                    en_name = link.get('data-en')
                    zh_name = link.get_text().strip()
                    if en_name and zh_name:
                        gem_map[en_name] = (zh_name, icon)
        
        return gem_map
    except Exception as e:
        return gem_map # 失敗時回傳保底資料

# --- 3. 抓取價格 ---
@st.cache_data(ttl=1800)
def fetch_ninja_data(mapping):
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選
        df = df[df['name'].str.contains(' of ', na=False) & df['corrupted'].isna()]
        
        # 執行對照
        def apply_mapping(en_name):
            return mapping.get(en_name, (en_name, "⚪"))
            
        df['中文'], df['色'] = zip(*df['name'].map(apply_mapping))
        
        # 重新整理顯示欄位 (修正您反應的名稱問題)
        res = df[['色', '中文', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['屬性', '中文名稱', '英文名稱', '等級', '價格 (C)', '價格 (D)']
        return res.sort_values('價格 (C)', ascending=False)
    except:
        return pd.DataFrame()

# --- 4. UI 介面 ---
mapping_table = get_poedb_mapping()
df = fetch_ninja_data(mapping_table)

if not df.empty:
    search = st.sidebar.text_input("🔍 搜尋名稱", "")
    final_df = df[df['中文名稱'].str.contains(search, case=False) | df['英文名稱'].str.contains(search, case=False)]
    
    st.dataframe(
        final_df,
        use_container_width=True,
        height=800,
        column_config={
            "價格 (C)": st.column_config.NumberColumn(format="%d C"),
            "價格 (D)": st.column_config.NumberColumn(format="%.2f D")
        },
        hide_index=True
    )
    
    if st.sidebar.button("強制重新整理資料"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error("資料讀取失敗，請檢查網路。")
