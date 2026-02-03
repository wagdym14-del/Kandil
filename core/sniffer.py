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
    [2026-02-03] المحرك السيادي - نسخة الاستقرار المطلق.
    تم تقليل العمال لضمان عدم انهيار الذاكرة في السحاب.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    # [تعديل استراتيجي]: 2 عمال فقط لضمان استقرار التطبيق ومنع الـ Boot Loop
    def __init__(self, wss_url: str = None, archiver=None, workers: int = 2):
        try:
            self.wss_url = st.secrets.get("WSS_URL_PRIMARY") or wss_url
        except Exception:
            self.wss_url = wss_url
            
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=5000) 
        self.is_running = False
        self._performance_metrics = {"total_processed": 0, "dropped": 0}

    async def _subscribe(self, ws):
        subscribe_msg = {
            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
            "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
        }
        await ws.send(json.dumps(subscribe_msg))
        logger.info(f"📡 [CONNECTED] Monitoring Pump.fun Strategy...")

    async def start_sniffing(self):
        if self.wss_url:
            self.wss_url = self.wss_url.strip()

        if not self.wss_url:
            logger.error("❌ WSS URL Missing!")
            return

        self.is_running = True
        
        # إطلاق العمال (Workers)
        for i in range(self.workers_count):
            asyncio.create_task(self._worker_logic(i))

        while self.is_running:
            try:
                # اتصال نقي لتجنب خطأ extra_headers
                async with websockets.connect(self.wss_url, ping_interval=20, ping_timeout=20) as ws:
                    await self._subscribe(ws)
                    while self.is_running:
                        raw_msg = await ws.recv()
                        if not self._queue.full():
                            await self._queue.put((raw_msg, time.time()))
            except Exception as e:
                logger.warning(f"🔄 Reconnecting: {str(e)[:50]}")
                await asyncio.sleep(2)

    async def _worker_logic(self, worker_id: int):
        while self.is_running:
            try:
                raw_msg, arrival_time = await self._queue.get()
                data = json.loads(raw_msg)
                if "params" in data:
                    result = data["params"]["result"]["value"]
                    event = self._deep_parse(result)
                    
                    if event and self.archiver:
                        # أرشفة البيانات فوراً لتتبع المحفظة مستقبلاً
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature,
                            raw_data={"logs": event.raw_logs, "latency": time.time()-arrival_time},
                            behavior_tag=event.event_type
                        )
                        self._performance_metrics["total_processed"] += 1
                self._queue.task_done()
            except Exception as e: pass

    def _deep_parse(self, result: dict) -> Optional[MarketEvent]:
        logs = result.get("logs", [])
        sig = result.get("signature")
        logs_str = "|".join(logs)

        # [تعديل الحساسية]: خفضنا الرقم لـ 3 لرصد أي عملة جديدة تظهر فيها حركة بوتات
        if logs_str.count("Trade") > 3:
            return MarketEvent(sig, time.time(), "NEW_TOKEN_ACTIVITY", 60, logs)

        if "mintTo" in logs_str and "InitializeMint" in logs_str:
            return MarketEvent(sig, time.time(), "INSTANT_BUNDLE_LAUNCH", 95, logs)

        return None
