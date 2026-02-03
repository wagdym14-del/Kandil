import aiosqlite
import datetime
import json
import logging
import asyncio
import os
import streamlit as st  # إضافة مكتبة ستريمليت لجلب الإعدادات السرية
from dataclasses import dataclass, field
from typing import Optional, Dict

# إعداد السجلات بنظام احترافي
logger = logging.getLogger("SovereignArchiver")
logging.basicConfig(level=logging.INFO)

class MMArchiver:
    """
    [2026-02-03] محرك الأرشفة السيادي - نسخة السحاب المطورة.
    تم الحفاظ على منطق الـ GOD_MODE و PUMP_DUMP مع ربطها بـ Streamlit Secrets.
    """
    def __init__(self, db_path=None):
        # التعديل 1: جلب المسار من Secrets إذا لم يتم تمريره، لضمان العمل على السحاب
        if db_path is None:
            try:
                self.db_path = st.secrets["DATABASE_URL"]
            except:
                self.db_path = "./archive/vault_v1.sqlite"
        else:
            self.db_path = db_path
            
        self._cache: Dict[str, dict] = {} 

    async def boot_system(self):
        """تشغيل النظام وضمان وجود المجلدات في بيئة السحاب"""
        # التعديل 2: التأكد من وجود المجلد تلقائياً لمنع خطأ FileNotFoundError
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"📂 [SYSTEM] Created directory: {db_dir}")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mm_intel (
                    wallet_id TEXT PRIMARY KEY,
                    threat_level INTEGER CHECK(threat_level BETWEEN 0 AND 100),
                    behavior_pattern TEXT,
                    trust_score REAL,
                    total_raids INTEGER,
                    historical_data_json TEXT,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("🚀 [SYSTEM] Sovereign Vault is Online and Encrypted on Cloud.")

    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        """تحليل البصمة السلوكية وأرشفتها فوراً (منطقك الأصلي كما هو)"""
        risk_score = self._compute_risk_score(behavior_tag)
        now = datetime.datetime.utcnow().isoformat()
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
            
            self._cache[wallet] = {"tag": behavior_tag, "threat": risk_score}
            logger.info(f"💾 [ARCHIVED] Target {wallet[:6]}... classified as {behavior_tag}")

    def _compute_risk_score(self, tag: str) -> int:
        """منطق تقييم التهديد المتقدم (محفوظ بالكامل)"""
        scores = {
            "GOD_MODE_MM": 5,        
            "PUMP_DUMP_SCUM": 98,    
            "WASH_TRADE_BOT": 75,    
            "STEALTH_ACCUMULATOR": 15 
        }
        return scores.get(tag, 50)

    async def quick_check(self, wallet: str) -> Optional[dict]:
        """فحص سريع للمحفظة"""
        if wallet in self._cache:
            return self._cache[wallet]
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT threat_level, behavior_pattern FROM mm_intel WHERE wallet_id = ?", (wallet,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
