import asyncio
import websockets
import json
import logging
import time
import streamlit as st
from typing import Optional, List, Dict
from dataclasses import dataclass

# نظام تسجيل جنائي فائق الدقة
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignSniffer.Ultra")

@dataclass
class MarketEvent:
    signature: str
    timestamp: float
    event_type: str
    risk_level: int
    raw_logs: List[str]

class PumpSniffer:
    """
    [2026-02-03] المحرك السيادي - نسخة الاستقرار المطلق (v3).
    تم تحسينها لتتبع الأرشفة وتجنب انهيار الذاكرة.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str = None, archiver=None, workers: int = 1):
        # [تعديل استراتيجي]: عامل واحد (1 Worker) هو الضمان الوحيد لمنع الـ Restart Loop في السحاب
        try:
            self.wss_url = st.secrets.get("WSS_URL_PRIMARY") or wss_url
        except Exception:
            self.wss_url = wss_url
            
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=1000) # تقليل حجم الطابور لتوفير الذاكرة
        self.is_running = False

    async def _subscribe(self, ws):
        """بروتوكول الاشتراك في تدفق بيانات سولانا"""
        subscribe_msg = {
            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
            "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
        }
        await ws.send(json.dumps(subscribe_msg))
        logger.info(f"📡 [CONNECTED] Monitoring Strategy Active...")

    async def start_sniffing(self):
        """إطلاق الرادار بنظام العامل الواحد لضمان الاستقرار"""
        if self.wss_url:
            self.wss_url = self.wss_url.strip()

        if not self.wss_url:
            logger.error("❌ [CRITICAL] WSS URL Missing!")
            return

        self.is_running = True
        
        # تشغيل العامل في الخلفية
        asyncio.create_task(self._worker_logic(0))

        while self.is_running:
            try:
                # حذفنا ping_interval و ping_timeout لترك السيرفر يدير الاتصال بأخف حمل ممكن
                async with websockets.connect(self.wss_url) as ws:
                    await self._subscribe(ws)
                    while self.is_running:
                        raw_msg = await ws.recv()
                        if not self._queue.full():
                            await self._queue.put((raw_msg, time.time()))
                        else:
                            # إذا امتلأ الطابور، نمسح أقدم رسالة لإفساح المجال للجديد
                            self._queue.get_nowait()
                            await self._queue.put((raw_msg, time.time()))

            except Exception as e:
                # وقت راحة كافٍ (5 ثوانٍ) لإعطاء فرصة للسحاب لتنظيف الذاكرة
                logger.warning(f"🔄 System Cooling Down... Reconnecting in 5s: {str(e)[:50]}")
                await asyncio.sleep(5)

    async def _worker_logic(self, worker_id: int):
        """منطق المعالجة والأرشفة الفورية"""
        while self.is_running:
            try:
                raw_msg, arrival_time = await self._queue.get()
                data = json.loads(raw_msg)
                
                if "params" in data:
                    result = data["params"]["result"]["value"]
                    event = self._deep_parse(result)
                    
                    if event and self.archiver:
                        # [تعليمات الأرشفة]: تسجيل البصمة للمستقبل
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature,
                            raw_data={"logs": event.raw_logs, "latency": time.time() - arrival_time},
                            behavior_tag=event.event_type
                        )
                
                self._queue.task_done()
                # إضافة استراحة قصيرة جداً للعامل لمنع استهلاك المعالج 100%
                await asyncio.sleep(0.01)
            except Exception:
                pass

    def _deep_parse(self, result: dict) -> Optional[MarketEvent]:
        """المحلل الهيكلي لبصمات البوتات والعملات الجديدة"""
        logs = result.get("logs", [])
        sig = result.get("signature")
        logs_str = "|".join(logs)

        # 1. رصد إطلاق البانيدل (أهم بصمة لمطور العملة)
        if "mintTo" in logs_str and "InitializeMint" in logs_str:
            return MarketEvent(sig, time.time(), "INSTANT_BUNDLE_LAUNCH", 95, logs)

        # 2. رصد النشاط الكثيف (بوتات صناع السوق) - معيار 5 تداولات
        if logs_str.count("Trade") > 5:
            return MarketEvent(sig, time.time(), "BOT_HFT_DETECTED", 70, logs)

        return None
