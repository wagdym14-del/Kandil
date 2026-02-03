import asyncio
import websockets
import json
import logging
import time
import streamlit as st  # المحرك السحابي (لا يؤثر على السرعة)
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
    تم الحفاظ على كامل القدرات الأصلية مع ميزة الربط السحابي التلقائي.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str = None, archiver=None, workers: int = 5):
        # التعديل: يسحب الرابط من الخزنة إذا لم يتم تمريره، مما يضمن العمل سحابياً ومحلياً
        self.wss_url = wss_url or st.secrets.get("WSS_URL_PRIMARY")
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=10000) # طابور ضخم للحماية من الانفجار البياني
        self.is_running = False
        self._performance_metrics = {"total_processed": 0, "dropped": 0}

    async def _subscribe(self, ws):
        """وظيفة الاشتراك الأصلية للحفاظ على الاتصال"""
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
        logger.info(f"📡 [CONNECTED] Monitoring: {self.PROGRAM_ID[:8]}...")

    async def start_sniffing(self):
        """إطلاق الرادار بنظام خوادم المعالجة المتعددة (Worker Pool)"""
        if not self.wss_url:
            logger.error("❌ [CRITICAL] WSS URL is missing from Secrets!")
            return

        self.is_running = True
        logger.info(f"🚀 [ULTRA] Initializing {self.workers_count} Processing Workers...")

        # إنشاء مجموعة من العمال للمعالجة المتوازية (كامل قدراتك هنا)
        workers = [asyncio.create_task(self._worker_logic(i)) for i in range(self.workers_count)]

        while self.is_running:
            try:
                # إعدادات الاتصال فائقة السرعة كما في كودك الأصلي
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=None, 
                    compression=None,   
                    extra_headers={"User-Agent": "Sovereign-Engine-v1.0"}
                ) as ws:
                    await self._subscribe(ws)
                    
                    while self.is_running:
                        raw_msg = await ws.recv()
                        if self._queue.full():
                            self._performance_metrics["dropped"] += 1
                            self._queue.get_nowait() 
                        
                        await self._queue.put((raw_msg, time.time()))

            except Exception as e:
                logger.error(f"⚠️ [CRITICAL] Radar Connection Lost: {e}")
                await asyncio.sleep(0.5) 

    async def _worker_logic(self, worker_id: int):
        """منطق العامل الذكي: تحليل فائق السرعة (لم يتم تغيير حرف واحد)"""
        while self.is_running:
            raw_msg, arrival_time = await self._queue.get()
            try:
                data = json.loads(raw_msg)
                if "params" in data:
                    result = data["params"]["result"]["value"]
                    event = self._deep_parse(result)
                    
                    if event:
                        # أرشفة فورية مع حساب زمن التأخير (Latency)
                        latency = (time.time() - arrival_time) * 1000
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature,
                            raw_data={"logs": event.raw_logs, "latency_ms": latency},
                            behavior_tag=event.event_type
                        )
                        self._performance_metrics["total_processed"] += 1
            except Exception as e:
                logger.error(f"Worker-{worker_id} Error: {e}")
            finally:
                self._queue.task_done()

    def _deep_parse(self, result: dict) -> Optional[MarketEvent]:
        """المحلل الهيكلي: فحص كثافة السجلات (منطقك الأصلي الفائق)"""
        logs = result.get("logs", [])
        sig = result.get("signature")
        logs_str = "|".join(logs)

        if "mintTo" in logs_str and "InitializeMint" in logs_str:
            return MarketEvent(sig, time.time(), "INSTANT_BUNDLE_LAUNCH", 90, logs)
        
        if "SetAuthority" in logs_str and "Trade" in logs_str:
            return MarketEvent(sig, time.time(), "SAFE_DEV_ENTRY", 20, logs)

        if logs_str.count("Trade") > 10:
            return MarketEvent(sig, time.time(), "HIGH_FREQUENCY_ACCUMULATION", 60, logs)

        return None
