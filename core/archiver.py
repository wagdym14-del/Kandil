import asyncio
import aiosqlite
import json
import datetime
import logging

logger = logging.getLogger("SovereignArchiver")

class SovereignArchiver:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._cache = {}

    def _compute_risk_score(self, tag: str) -> int:
        # نظام تقييم مخاطر بسيط لضمان سير العمل
        return 85 if "Raid" in tag else 40

    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        """
        تحليل البصمة مع ضمان استخراج روابط الصور والأسماء بمرونة عالية.
        """
        risk_score = self._compute_risk_score(behavior_tag)
        now = datetime.datetime.utcnow().isoformat()
        
        # [خطوة الربط الذهبية]: نضمن وجود حقل 'api' داخل الـ JSON بالبيانات الصحيحة
        api_info = raw_data.get("api") or {}
        
        # استخراج البيانات بمرونة
        token_image = api_info.get("image_url") or api_info.get("image_uri") or api_info.get("logo")
        token_name = api_info.get("name", "Scanning...")
        token_symbol = api_info.get("symbol", "-")

        # تحديث raw_data لضمان أن الـ Dashboard سيقرأ الصور والأسماء
        raw_data["api"] = {
            "image_url": token_image,
            "name": token_name,
            "symbol": token_symbol
        }
        
        metadata_json = json.dumps(raw_data)

        # الحفاظ على الـ Cache الخاص بك
        self._cache[wallet] = {
            "tag": behavior_tag, 
            "threat": risk_score, 
            "coin_info": {
                "name": token_name,
                "symbol": token_symbol,
                "image": token_image
            }
        }

        try:
            # استخدام WAL mode لضمان عدم حدوث Database Lock بين البوت والواجهة
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL") 
                await db.execute("""
                    INSERT INTO mm_intel (wallet_id, threat_level, behavior_pattern, trust_score, total_raids, historical_data_json, last_seen_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(wallet_id) DO UPDATE SET
                        total_raids = total_raids + 1,
                        threat_level = (threat_level + ?) / 2,
                        behavior_pattern = excluded.behavior_pattern,
                        historical_data_json = excluded.historical_data_json,
                        last_seen_at = excluded.last_seen_at
                """, (wallet, risk_score, behavior_tag, 100-risk_score, metadata_json, now, risk_score))
                await db.commit()
                logger.info(f"💾 [SAVED] {behavior_tag} (with Intelligent Metadata) -> {wallet[:8]}")
        except Exception as e:
            logger.error(f"❌ Database Write Error: {e}")
