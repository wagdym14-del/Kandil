import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import json # ضروري لفك تشفير بيانات الـ API
import time
import os
import asyncio
import threading
from datetime import datetime
from core.archiver import MMArchiver
from core.sniffer import PumpSniffer

# ... (نفس الجزء العلوي الخاص بـ launch_radar_in_background و configuration دون تغيير) ...

# ==========================================
# 🧠 INTELLIGENCE DATA CORE (تعديل الجودة)
# ==========================================
class SovereignVault:
    @staticmethod
    def get_connection():
        db_path = st.secrets.get("DATABASE_URL", "./archive/sovereign_vault.sqlite")
        if not os.path.exists(db_path): return None
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    @classmethod
    @st.cache_data(ttl=1) 
    def fetch_live_registry(cls):
        conn = cls.get_connection()
        if not conn: return pd.DataFrame()
        try:
            query = "SELECT * FROM mm_intel ORDER BY last_seen_at DESC"
            df = pd.read_sql(query, conn)
            
            # --- [إضافة جودة] معالجة بيانات الـ API المدمجة ---
            processed_rows = []
            for _, row in df.iterrows():
                try:
                    # فك تشفير الـ JSON الذي حفظته الخزنة
                    meta = json.loads(row['historical_data_json'])
                    api_data = meta.get('api', {}) or {}
                except:
                    api_data = {}
                
                # إلحاق البيانات الجديدة بالصف
                row['token_name'] = api_data.get('name', 'Scanning...')
                row['token_symbol'] = api_data.get('symbol', '-')
                row['token_icon'] = api_data.get('image_url', '') # رابط الصورة من الـ API
                processed_rows.append(row)
            
            return pd.DataFrame(processed_rows)
        except Exception as e:
            return pd.DataFrame()
        finally:
            conn.close()

# ==========================================
# 🖥️ SOVEREIGN INTERFACE BUILDER (تحديث العرض)
# ==========================================
def render_dashboard():
    # ... (الجزء الخاص بالـ sidebar والـ metrics يظل كما هو) ...
    
    # [تعديل العرض] استدعاء البيانات المعالجة
    df_raw = SovereignVault.fetch_live_registry()
    
    # (تصفية البيانات حسب الشريط المنزلق كما في كودك)
    if not df_raw.empty:
        # تأكد من وجود الأعمدة حتى لو لم يتم الرصد بعد
        for col in ['threat_level', 'token_name', 'token_icon']:
            if col not in df_raw.columns: df_raw[col] = None
            
        trust_threshold = st.session_state.get('risk_slider', (0, 100)) # تأكد من مطابقة اسم الـ widget
        # ملاحظة: استبدل trust_threshold هنا بمتغير الـ slider الخاص بك
        df = df_raw # سنعرض الكل حالياً لغرض الفحص
    else:
        st.warning("📡 Radar is scanning the blockchain...")
        return

    # عرض الإحصائيات (Metrics) بنفس أسلوبك الجميل
    # ... (كود الـ Metrics الخاص بك) ...

    st.markdown("---")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🧬 Behavioral Ledger (Enriched with API)")
        st.dataframe(
            df,
            column_config={
                "token_icon": st.column_config.ImageColumn("Icon", help="Token Logo from Pump.fun"),
                "token_name": "Token Name",
                "token_symbol": "Symbol",
                "wallet_id": st.column_config.TextColumn("Identity", width="medium"),
                "trust_score": st.column_config.ProgressColumn("Trust Level", min_value=0, max_value=100, format="%d%%"),
                "behavior_pattern": "Pattern",
                "last_seen_at": "Last Seen"
            },
            # ترتيب الأعمدة لتظهر الصورة والاسم أولاً
            column_order=("token_icon", "token_name", "token_symbol", "wallet_id", "trust_score", "behavior_pattern", "last_seen_at"),
            hide_index=True,
            use_container_width=True
        )

    with c2:
        # (كود الـ Plotly الخاص بك يظل كما هو)
        st.subheader("📊 Strategy Profile")
        fig = px.pie(df, names='behavior_pattern', hole=0.6)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_dashboard()
    time.sleep(2)
    st.rerun()
