import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 網頁基礎設定
st.set_page_config(page_title="PoE Mirage 轉換寶石工具", page_icon="💎", layout="wide")

st.title("💎 PoE Mirage 賽季：轉換寶石即時價格")
st.caption("資料來源：poe.ninja | 翻譯與顏色：PoEDB (Skill_Gems)")

# --- 1. 從 PoEDB 抓取精確的顏色與中文對照表 ---
@st.cache_data(ttl=86400)
def get_poedb_mapping():
    url = "https://poedb.tw/tw/Skill_Gems"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    gem_map = {}
    # 定義 PoEDB 頁面中的顏色區塊 ID
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
            # 找到對應顏色的區塊 (可能是 div 或 table)
            section = soup.find(id=section_id)
            if section:
                # 抓取該區塊內所有具備 data-en 的連結
                links = section.find_all('a', attrs={'data-en': True})
                for link in links:
                    en_name = link.get('data-en')
                    zh_name = link.get_text().strip()
                    # 存入對照表：英文名稱為 Key，值為 (中文, 顏色圖示)
                    gem_map[en_name] = (zh_name, icon)
        
        return gem_map
    except Exception as e:
        st.error(f"PoEDB 對照表抓取失敗: {e}")
        return {}

# --- 2. 抓取 poe.ninja 價格並進行 Mapping ---
@st.cache_data(ttl=1800)
def fetch_ninja_data(mapping):
    # 目前賽季設定為 Mirage
    url = "https://poe.ninja/api/data/itemoverview?league=Mirage&type=SkillGem&language=en"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['lines'])
        
        # 篩選：轉換寶石(名稱含 of) 且 非瓦爾(corrupted 為 NaN)
        df = df[df['name'].str.contains(' of ', na=False) & df['corrupted'].isna()]
        
        # 核心 Mapping 邏輯
        def do_mapping(en_name):
            # 從 PoEDB 的對照表中查找
            return mapping.get(en_name, (en_name, "⚪")) # 找不到則保底顯示英文+白色
            
        df['中文名稱'], df['顏色'] = zip(*df['name'].map(do_mapping))
        
        # 整理輸出格式
        res = df[['顏色', '中文名稱', 'name', 'gemLevel', 'chaosValue', 'divineValue']]
        res.columns = ['屬性', '寶石中文名稱', '英文原名', '等級', 'C', 'D']
        return res.sort_values('C', ascending=False)
    except Exception as e:
        st.error(f"Ninja 價格抓取失敗: {e}")
        return pd.DataFrame()

# --- 3. Streamlit UI 介面 ---
# 啟動時先跑一次 Mapping 抓取
with st.spinner('正在同步 PoEDB 翻譯與顏色分區...'):
    mapping_table = get_poedb_mapping()
    final_df = fetch_ninja_data(mapping_table)

if not final_df.empty:
    # 側邊欄：搜尋與過濾
    st.sidebar.header("🔍 篩選與搜尋")
    search_query = st.sidebar.text_input("搜尋名稱 (中/英文)", "")
    
    color_options = ["全部", "🔴 紅色寶石", "🟢 綠色寶石", "🔵 藍色寶石"]
    selected_color = st.sidebar.selectbox("依顏色篩選", color_options)
    
    min_c = st.sidebar.number_input("最低 C 價", min_value=0, value=0)

    # 執行篩選
    mask = (final_df['寶石中文名稱'].str.contains(search_query, case=False) | 
            final_df['英文原名'].str.contains(search_query, case=False)) & \
           (final_df['C'] >= min_c)
    
    output_df = final_df[mask]
    
    if selected_color != "全部":
        target_icon = selected_color.split(" ")[0]
        output_df = output_df[output_df['屬性'] == target_icon]

    # 主要表格顯示
    st.markdown(f"### 找到 **{len(output_df)}** 個轉換寶石")
    st.dataframe(
        output_df,
        use_container_width=True,
        height=800,
        column_config={
            "C": st.column_config.NumberColumn("價格 (Chaos)", format="%d C"),
            "D": st.column_config.NumberColumn("價格 (Divine)", format="%.2f D"),
            "等級": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    # 下載按鈕
    csv = output_df.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button("📥 下載目前的 Excel (CSV)", csv, "poe_gem_prices.csv", "text/csv")

else:
    st.warning("暫時無法取得資料，請確認網路或 API 狀態。")
