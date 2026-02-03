import asyncio
import aiosqlite
import json
import datetime
import logging
import httpx

logger = logging.getLogger("SovereignArchiver")

class SovereignArchiver:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._cache = {}
        # [تحديث] رفع الحد الأدنى للقيمة السوقية إلى 11,000 دولار
        self.MIN_MARKET_CAP_USD = 11000 
        # [تحديث] إضافة شرط عدد الهولدرز
        self.MIN_HOLDERS = 70

    async def _check_viability(self, mint: str) -> bool:
        """فحص دقيق للقيمة السوقية وعدد الهولدرز لاصطياد كبار المحترفين"""
        if mint == "Scanning..." or not mint: return False
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                url = f"https://frontend-api.pump.fun/coins/{mint}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    market_cap = data.get("usd_market_cap", 0)
                    # ملاحظة: في Pump.fun، يتم تتبع عدد المتداولين/الملاك
                    # سنستخدم "reply_count" أو بيانات الـ holders إذا توفرت في الـ API
                    # غالباً الـ API يوفر معلومات عن مدى اكتمال المنحنى (Bonding Curve)
                    holders_count = data.get("holder_count", 0) 
                    
                    # التحقق من الشرطين معاً
                    is_viable = market_cap >= self.MIN_MARKET_CAP_USD and holders_count > self.MIN_HOLDERS
                    
                    if is_viable:
                        logger.info(f"✅ [MATCH] Cap: ${market_cap:,.0f} | Holders: {holders_count}")
                    return is_viable
        except Exception as e:
            logger.debug(f"Viability Check Error: {e}")
            return False # في حال الخطأ، نفضل عدم التخزين لتوفير الموارد
        return False

    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        mint = raw_data.get("mint")
        
        # 1. تطبيق الفلتر الجديد (11k Cap + 70 Holders)
        if not await self._check_viability(mint):
            return 

        now = datetime.datetime.utcnow().isoformat()
        # محاولة جلب البيانات مباشرة من الـ API بدلاً من الانتظار
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://frontend-api.pump.fun/coins/{mint}")
            api_info = resp.json() if resp.status_code == 200 else {}

        token_image = api_info.get("image_url") or api_info.get("logo")
        token_name = api_info.get("name", "Active Token")
        token_symbol = api_info.get("symbol", "-")

        # تنظيف وحفظ
        clean_raw_data = {
            "sig": raw_data.get("sig"),
            "mint": mint,
            "api": {"image_url": token_image, "name": token_name, "symbol": token_symbol},
            "stats": {"cap": api_info.get("usd_market_cap"), "holders": api_info.get("holder_count")}
        }
        
        metadata_json = json.dumps(clean_raw_data)

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("""
                    INSERT INTO mm_intel (wallet_id, threat_level, behavior_pattern, trust_score, total_raids, historical_data_json, last_seen_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(wallet_id) DO UPDATE SET
                        total_raids = total_raids + 1,
                        historical_data_json = excluded.historical_data_json,
                        last_seen_at = excluded.last_seen_at
                """, (wallet, 50, behavior_tag, 50, metadata_json, now))
                await db.commit()
                logger.info(f"💾 [ELITE_TARGET_SAVED] {token_name} (Cap: ${api_info.get('usd_market_cap',0):,.0f})")
        except Exception as e:
            logger.error(f"❌ DB Error: {e}")
