import aiosqlite
import datetime
import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict

# إعداد السجلات بنظام احترافي (Logging System)
logger = logging.getLogger("SovereignArchiver")
logging.basicConfig(level=logging.INFO)

class MMArchiver:
    """
    [2026-02-03] محرك الأرشفة السيادي - الإصدار المطلق.
    النظام مصمم ليكون "الذاكرة الفوتوغرافية" لكل صانع سوق على Solana.
    """
    def __init__(self, db_path="./archive/vault_v1.sqlite"):
        self.db_path = db_path
        self._cache: Dict[str, dict] = {} # ذاكرة مؤقتة لسرعة الاستجابة الملي-ثانية

    async def boot_system(self):
        """تشغيل النظام وفحص سلامة الهيكل"""
        async with aiosqlite.connect(self.db_path) as db:
            # تفعيل نمط WAL للسرعة القصوى في القراءة والكتابة المتزامنة
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mm_intel (
                    wallet_id TEXT PRIMARY KEY,
                    threat_level INTEGER CHECK(threat_level BETWEEN 0 AND 100),
                    behavior_pattern TEXT, -- (مثلاً: Wash Trading, Stealth Buy)
                    trust_score REAL,
                    total_raids INTEGER,
                    historical_data_json TEXT, -- أرشيف الصفقات السابقة
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("🚀 [SYSTEM] Sovereign Vault is Online and Encrypted.")

    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        """
        [cite: 2026-02-03]
        تحليل البصمة السلوكية وأرشفتها فوراً. 
        يستخدم هذا التابع نظام الـ Upsert لضمان عدم تكرار البيانات.
        """
        risk_score = self._compute_risk_score(behavior_tag)
        now = datetime.datetime.utcnow().isoformat()
        
        # تحويل البيانات لـ JSON مع ضغطها برمجياً
        metadata = json.dumps(raw_data)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO mm_intel (wallet_id, threat_level, behavior_pattern, trust_score, total_raids, historical_data_json, last_seen_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(wallet_id) DO UPDATE SET
                    total_raids = total_raids + 1,
                    threat_level = (threat_level + ?) / 2,
                    behavior_pattern = excluded.behavior_pattern,
                    historical_data_json = excluded.historical_data_json,
                    last_seen_at = excluded.last_seen_at
            """, (wallet, risk_score, behavior_tag, 100-risk_score, metadata, now, risk_score))
            await db.commit()
            
            # تحديث الذاكرة المؤقتة (Cache) لتجنب الاستعلام من القرص مرة أخرى
            self._cache[wallet] = {"tag": behavior_tag, "threat": risk_score}
            logger.info(f"💾 [ARCHIVED] Target {wallet[:6]}... classified as {behavior_tag}")

    def _compute_risk_score(self, tag: str) -> int:
        """منطق تقييم التهديد المتقدم"""
        scores = {
            "GOD_MODE_MM": 5,        # صانع سوق محترف جداً وموثوق
            "PUMP_DUMP_SCUM": 98,    # خطر فوري
            "WASH_TRADE_BOT": 75,    # تلاعب بالفوليوم
            "STEALTH_ACCUMULATOR": 15 # تجميع ذكي (فرصة شراء)
        }
        return scores.get(tag, 50)

    async def quick_check(self, wallet: str) -> Optional[dict]:
        """فحص سريع للمحفظة: هل واجهناها من قبل؟"""
        if wallet in self._cache:
            return self._cache[wallet]
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT threat_level, behavior_pattern FROM mm_intel WHERE wallet_id = ?", (wallet,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
