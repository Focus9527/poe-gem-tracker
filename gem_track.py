import streamlit as st
import pandas as pd
import requests

# 設定網頁標題與圖示
st.set_page_config(page_title="PoE Mirage 轉換寶石價格追蹤", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("資料來源：poe.ninja API | 自動過濾非瓦爾、等級 20 之轉換寶石")

# 1. 定義中英文對照與顏色資料庫 (這部分需要手動維護，我已加入常見寶石)
# 格式: "英文名稱": ("中文名稱", "顏色代碼")
# 顏色代碼說明: 🔴=力量(紅), 🟢=敏捷(綠), 🔵=智慧(藍), ⚪=白色
GEM_DATA_MAP = {
    # 藍色 (智慧)
    "Ice Nova of Frostbolts": ("冰霜新星：冰霜彈", "🔵"),
    "Raise Zombie of Falling": ("喚醒幽靈：墜落", "🔵"),
    "Detonate Dead of Scavenging": ("屍體爆破：尋食", "🔵"),
    "Firestorm of Pelting": ("烈炎風暴：猛攻", "🔵"),
    "Ball Lightning of Static": ("電球：靜態", "🔵"),
    "Arc of Oscillating": ("連鎖閃電：震盪", "🔵"),
    "Blade Vortex of Reaping": ("刀鋒漩渦：收割", "🔵"),
    "Summon Raging Spirit of Enormity": ("召喚憤怒狂靈：巨大", "🔵"),
    # 綠色 (敏捷)
    "Tornado Shot of Cloudburst": ("龍卷射擊：雲爆", "🟢"),
    "Blade Blast of Unloading": ("刀鋒爆破：卸載", "🟢"),
    "Caustic Arrow of Poison": ("腐蝕箭矢：毒素", "🟢"),
    "Scourge Arrow of Menace": ("災厄箭矢：威脅", "🟢"),
    "Ethereal Knives of Lingering": ("飛刃風暴：滯留", "🟢"),
    # 紅色 (力量)
    "Cremation of Exhumation": ("火葬：發掘", "🔴"),
    "Earthshatter of Prominence": ("地裂斬：傑出", "🔴"),
    "Sunder of Earthbreaking": ("裂地擊：破土", "🔴"),
    "Consecrated Path of Endurance": ("奉獻之路：耐力", "🔴"),
    # 可根據需要在此繼續新增...
}

# 2. 抓取資料的函式
@st.cache_data(ttl=1800)  # 快取 30 分鐘，兼顧即時性與降低 API 負擔
def fetch_data():
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        response.raise_for_status() # 檢查請求是否成功
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選轉換寶石 (名稱含 of) 且非瓦爾 (corrupted 為空)
        df = df[df['name'].str.contains(' of ', na=False)]
        df = df[df['corrupted'].isna()]
        
        # 3. 整合中文名稱與顏色
        def get_gem_info(en_name):
            # 在地圖中尋找，找不到就顯示 N/A 和白色
            info = GEM_DATA_MAP.get(en_name, (en_name, "⚪")) 
            return info[0], info[1]

        # 應用對照表
        df['中文名稱'], df['顏色'] = zip(*df['name'].map(get_gem_info))
        
        # 整理輸出欄位
        df = df[['顏色', '中文名稱', 'name', 'gemLevel', 'chaosValue', 'divineValue', 'listingCount']]
        df.columns = ['⚪', '寶石中文名稱', '英文名稱', '等級', '混沌石(C)', '神聖石(D)', '掛單數']
        
        # 預設依 C 價排序
        return df.sort_values('混沌石(C)', ascending=False)
    except Exception as e:
        st.error(f"資料抓取或處理失敗: {e}")
        return pd.DataFrame()

# 4. 執行抓取
with st.spinner('正在從 poe.ninja 獲取最新 Mirage 價格...'):
    data = fetch_data()
