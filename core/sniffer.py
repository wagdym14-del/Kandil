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
    [2026-02-03] المحرك الفائق لرصد الثغرات السلوكية (Behavioral Gap Detector).
    نظام يعتمد على معالجة التدفق المتوازي (Parallel Stream Processing).
    تم تحسينه للأرشفة الذكية وتتبع بوتات صناع السوق.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str = None, archiver=None, workers: int = 5):
        # [نظام الاستدعاء الذكي]: الربط المباشر بخزنة الأسرار
        try:
            # الأولوية للرابط من Secrets لضمان الثبات السحابي
            self.wss_url = st.secrets.get("WSS_URL_PRIMARY") or wss_url
        except Exception:
            self.wss_url = wss_url
            
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=10000) 
        self.is_running = False
        self._performance_metrics = {"total_processed": 0, "dropped": 0}

    async def _subscribe(self, ws):
        """بروتوكول الاشتراك في تدفق بيانات سولانا"""
        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [self.PROGRAM_ID]},
                {"commitment": "processed"}
            ]
        }
        await ws.send(json.dumps(subscribe_msg))
        logger.info(f"📡 [SYSTEM] Connection Established. Monitoring: {self.PROGRAM_ID[:8]}...")

    async def start_sniffing(self):
        """إطلاق الرادار بنظام خوادم المعالجة المتعددة (Worker Pool)"""
        if self.wss_url:
            self.wss_url = self.wss_url.strip()

        if not self.wss_url:
            logger.error("❌ [CRITICAL] WSS URL is missing from Secrets!")
            return

        self.is_running = True
        logger.info(f"🚀 [ENGINE] Activating {self.workers_count} High-Frequency Workers...")

        # تشغيل العمال في الخلفية كمهام منفصلة لضمان التوازي الحقيقي
        workers = [asyncio.create_task(self._worker_logic(i)) for i in range(self.workers_count)]

        while self.is_running:
            try:
                # [التعديل الذهبي]: اتصال خام ونقي لتجنب أخطاء بروتوكول السحاب
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=30, 
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    await self._subscribe(ws)
                    
                    while self.is_running:
                        raw_msg = await ws.recv()
                        # إدارة الطابور لمنع تكدس البيانات
                        if self._queue.full():
                            self._performance_metrics["dropped"] += 1
                            self._queue.get_nowait() 
                        
                        await self._queue.put((raw_msg, time.time()))

            except Exception as e:
                # رصد الانقطاع وإعادة التشغيل التلقائي في أقل من ثانية
                logger.warning(f"🔄 [NETWORK] Auto-reconnecting... Context: {str(e)[:50]}")
                await asyncio.sleep(1)

    async def _worker_logic(self, worker_id: int):
        """منطق المعالجة الجنائية: تحليل البصمات والأرشفة الفورية"""
        while self.is_running:
            try:
                raw_msg, arrival_time = await self._queue.get()
                data = json.loads(raw_msg)
                
                if "params" in data:
                    result = data["params"]["result"]["value"]
                    event = self._deep_parse(result)
                    
                    if event:
                        # حساب زمن الاستجابة الفعلي بالملي ثانية
                        latency = (time.time() - arrival_time) * 1000
                        
                        # [الأرشفة]: إرسال البصمة لمحرك الأرشفة للتسجيل المستقبلي
                        if self.archiver:
                            await self.archiver.analyze_and_archive(
                                wallet=event.signature,
                                raw_data={
                                    "logs": event.raw_logs, 
                                    "latency_ms": round(latency, 2),
                                    "worker_id": worker_id
                                },
                                behavior_tag=event.event_type
                            )
                        self._performance_metrics["total_processed"] += 1
                
                self._queue.task_done()
            except Exception as e:
                logger.error(f"Worker-{worker_id} Error: {e}")

    def _deep_parse(self, result: dict) -> Optional[MarketEvent]:
        """المحلل الهيكلي: فك تشفير بصمات صناع السوق (Market Makers)"""
        logs = result.get("logs", [])
        sig = result.get("signature")
        logs_str = "|".join(logs)

        # 1. رصد إطلاق البانيدل (Instant Bundle)
        if "mintTo" in logs_str and "InitializeMint" in logs_str:
            return MarketEvent(sig, time.time(), "INSTANT_BUNDLE_LAUNCH", 95, logs)
        
        # 2. رصد البوتات عالية التردد (HFT Bots)
        if logs_str.count("Trade") > 12:
            return MarketEvent(sig, time.time(), "BOT_HFT_ACCUMULATION", 70, logs)
            
        # 3. رصد تحركات المطور المشبوهة
        if "SetAuthority" in logs_str and "Trade" in logs_str:
            return MarketEvent(sig, time.time(), "DEV_AUTHORITY_RELIQUISH", 40, logs)

        return None
