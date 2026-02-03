import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignSniffer.Light")

@dataclass
class MarketEvent:
    signature: str
    timestamp: float
    event_type: str
    jito_detected: bool = False
    raw_logs: List[str] = None

class PumpSniffer:
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"
    JITO_TIP_PROGRAMS = ["9619WQCpPLM3U3M8qfT9MGP3C667XvQGczpG6GvV5Q66", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe"]

    def __init__(self, wss_url: str, archiver):
        # تحويل الرابط ليتوافق مع WebSocket
        self.wss_url = wss_url.replace("https://", "wss://") if "wss://" not in wss_url else wss_url
        self.archiver = archiver
        self._queue = asyncio.Queue(maxsize=100) # تقليل الحجم للحفاظ على RAM
        self.is_running = False

    async def _worker_logic(self):
        """معالجة ذكية وموفرة للموارد"""
        while self.is_running:
            event = await self._queue.get()
            try:
                # فلترة الفوليوم العالي (نكتفي هنا بكشف Jito كدليل على الاحترافية)
                jito_found = any(tip in str(event.raw_logs) for l in event.raw_logs for tip in self.JITO_TIP_PROGRAMS)
                
                if jito_found or "Create" in event.event_type:
                    if self.archiver:
                        # وسم السلوك
                        tag = "🚀 HIGH_VOLUME_MM" if jito_found else "New Launch"
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature[:12], 
                            raw_data={"sig": event.signature},
                            behavior_tag=tag
                        )
            except Exception as e:
                logger.debug(f"Worker process skip: {e}")
            finally:
                self._queue.task_done()
                await asyncio.sleep(0.1) # تنفس للمُعالج (Resource Friendly)

    async def start_sniffing(self):
        self.is_running = True
        # اكتفِ بعامل واحد أو اثنين لـ Streamlit
        asyncio.create_task(self._worker_logic())

        while self.is_running:
            try:
                async with websockets.connect(self.wss_url, ping_interval=20) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 Sovereign Radar (Light Mode) Online.")
                    
                    while self.is_running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if "params" in data:
                            res = data["params"]["result"]["value"]
                            logs = res.get("logs", [])
                            # رصد الفوليوم العالي يبدأ من رصد عمليات الـ Create
                            if any("Instruction: Create" in l for l in logs):
                                ev = MarketEvent(signature=res["signature"], timestamp=time.time(), 
                                                event_type="Create", raw_logs=logs)
                                if not self._queue.full():
                                    await self._queue.put(ev)
            except Exception as e:
                await asyncio.sleep(5)

    def start(self):
        """تشغيل متوافق مع Streamlit"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.start_sniffing())
            else:
                loop.run_until_complete(self.start_sniffing())
        except Exception as e:
            logger.error(f"Bridge Error: {e}")
