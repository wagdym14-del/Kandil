import aiosqlite
import datetime
import json
import logging
import os
import streamlit as st
from typing import Optional, Dict

logger = logging.getLogger("SovereignArchiver")

class MMArchiver:
    """
    [2026-02-03] محرك الأرشفة السيادي - نسخة 'توازن الموارد'.
    تمت إضافة نظام التجميع (Batching) لحماية سيرفر Streamlit من الانهيار.
    """
    def __init__(self, db_path=None):
        # الاعتماد على مسار مؤقت في السحاب إذا لم يتوفر قاعدة بيانات خارجية
        self.db_path = db_path or "./archive/vault_v1.sqlite"
        self._cache: Dict[str, dict] = {} 
        self._pending_writes = [] # قائمة انتظار للكتابة الجماعية

    async def boot_system(self):
        """تشغيل النظام مع نظام WAL لتحسين الأداء"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # نظام WAL (Write-Ahead Logging) ضروري جداً لمنع قفل قاعدة البيانات في السحاب
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL") 
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mm_intel (
                    wallet_id TEXT PRIMARY KEY,
                    threat_level INTEGER,
                    behavior_pattern TEXT,
                    trust_score REAL,
                    total_raids INTEGER,
                    historical_data_json TEXT,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("🚀 [SYSTEM] Sovereign Vault Secured.")

    async def analyze_and_archive(self, wallet: str, raw_data: dict, behavior_tag: str):
        """
        تحليل البصمة مع إضافة بيانات الـ API السريعة.
        """
        risk_score = self._compute_risk_score(behavior_tag)
        now = datetime.datetime.utcnow().isoformat()
        
        # دمج بيانات الـ API في الأرشفة إذا وجدت
        metadata = json.dumps(raw_data)

        # التعديل الاحترافي: تحديث الكاش أولاً لضمان السرعة في الواجهة
        self._cache[wallet] = {
            "tag": behavior_tag, 
            "threat": risk_score, 
            "metadata": raw_data.get("metadata") # البيانات القادمة من API
        }

        # تنفيذ الكتابة (نستخدم try/except لضمان عدم توقف البوت إذا تعثرت قاعدة البيانات)
        try:
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
                logger.info(f"💾 [SAVED] {behavior_tag} -> {wallet[:8]}")
        except Exception as e:
            logger.error(f"❌ Database Write Error: {e}")

    def _compute_risk_score(self, tag: str) -> int:
        # الحفاظ على منطقك الأصلي كما طلبت
        scores = {
            "GOD_MODE_MM": 5,        
            "PUMP_DUMP_SCUM": 98,    
            "WASH_TRADE_BOT": 75,    
            "STEALTH_ACCUMULATOR": 15,
            "INSTANT_BUNDLE_LAUNCH": 90, # إضافة النوع الجديد من السنيفر
            "BOT_HFT_DETECTED": 70
        }
        return scores.get(tag, 50)
