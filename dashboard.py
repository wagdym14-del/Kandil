# ==========================================
# 🧠 INTELLIGENCE DATA CORE (تعديل الجودة النهائي)
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
            
            processed_rows = []
            for _, row in df.iterrows():
                try:
                    meta = json.loads(row['historical_data_json'])
                    api_data = meta.get('api', {}) or {}
                except:
                    api_data = {}
                
                # [تصحيح الجودة]: استخراج الرابط بشكل مرن كما فعلنا في الخزنة
                row['token_icon'] = api_data.get('image_url') or api_data.get('image_uri') or api_data.get('logo')
                row['token_name'] = api_data.get('name', 'Scanning...')
                row['token_symbol'] = api_data.get('symbol', '-')
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
    # استدعاء البيانات المعالجة
    df_raw = SovereignVault.fetch_live_registry()
    
    if not df_raw.empty:
        # التأكد من ترتيب الأعمدة ووجودها
        df = df_raw
    else:
        st.warning("📡 Radar is scanning the blockchain...")
        return

    # ... (بقية منطق الـ Sidebar والـ Metrics تظل كما هي في كودك) ...

    st.markdown("---")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("🧬 Behavioral Ledger (Enriched)")
        st.dataframe(
            df,
            column_config={
                "token_icon": st.column_config.ImageColumn("Icon"), # عرض الصورة
                "token_name": "Token Name",
                "wallet_id": st.column_config.TextColumn("Identity", width="medium"),
                "trust_score": st.column_config.ProgressColumn("Trust Level", min_value=0, max_value=100, format="%d%%"),
                "behavior_pattern": "Pattern",
                "last_seen_at": "Last Seen"
            },
            # ترتيب عرض الأعمدة في الجدول
            column_order=("token_icon", "token_name", "wallet_id", "trust_score", "behavior_pattern", "last_seen_at"),
            hide_index=True,
            use_container_width=True
        )

    # ... (بقية كود الـ Plotly تظل كما هي) ...
