import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

# إعداد التسجيل بشكل خفيف لبيئة Streamlit
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
    # عناوين Jito Tip للكشف عن صناع السوق المحترفين
    JITO_TIP_PROGRAMS = ["9619WQCpPLM3U3M8qfT9MGP3C667XvQGczpG6GvV5Q66", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe"]

    def __init__(self, wss_url: str, archiver):
        # التأكد من بروتوكول WebSocket
        self.wss_url = wss_url.replace("https://", "wss://") if "wss://" not in wss_url else wss_url
        self.archiver = archiver
        self._queue = asyncio.Queue(maxsize=100) # حجم صغير للحفاظ على الذاكرة
        self.is_running = False

    async def _worker_logic(self):
        """معالجة ذكية وموفرة للموارد في الخلفية"""
        while self.is_running:
            event = await self._queue.get()
            try:
                # الكشف عن بصمة Jito في سجلات المعاملة
                jito_found = any(tip in str(event.raw_logs) for tip in self.JITO_TIP_PROGRAMS)
                
                if jito_found or "Create" in event.event_type:
                    if self.archiver:
                        # وسم السلوك (Pattern Recognition)
                        tag = "🚀 HIGH_VOLUME_MM" if jito_found else "New Launch"
                        # إرسال البيانات للأرشيف ليقوم بفحص الـ 11k$ والـ 70 هولدر
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature[:16], 
                            raw_data={"sig": event.signature, "mint": "Scanning..."},
                            behavior_tag=tag
                        )
            except Exception as e:
                logger.debug(f"Worker process skip: {e}")
            finally:
                self._queue.task_done()
                await asyncio.sleep(0.1) # راحة للمعالج لضمان استقرار الموقع

    async def start_sniffing(self):
        """المحرك الرئيسي للاتصال بالبلوكشين"""
        self.is_running = True
        # تشغيل عامل المعالجة في الخلفية
        asyncio.create_task(self._worker_logic())

        while self.is_running:
            try:
                async with websockets.connect(self.wss_url, ping_interval=20, ping_timeout=10) as ws:
                    # الاشتراك في سجلات برنامج Pump.fun
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 Sovereign Radar Online & Connected.")
                    
                    while self.is_running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if "params" in data:
                            res = data["params"]["result"]["value"]
                            logs = res.get("logs", [])
                            signature = res.get("signature")
                            
                            # التقاط عمليات الإطلاق الجديدة لتحليلها
                            if any("Instruction: Create" in l for l in logs):
                                ev = MarketEvent(
                                    signature=signature, 
                                    timestamp=time.time(), 
                                    event_type="Create", 
                                    raw_logs=logs
                                )
                                if not self._queue.full():
                                    await self._queue.put(ev)
            except Exception as e:
                logger.warning(f"Connection lost, retrying in 5s... ({e})")
                await asyncio.sleep(5)

    def start(self):
        """
        الخوارزمية المعدلة للعمل داخل Thread مستقل في Streamlit.
        تقوم بإنشاء Event Loop جديد لتجنب خطأ Bridge Error.
        """
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        try:
            logger.info("⚙️ Starting Engine inside dedicated thread...")
            new_loop.run_until_complete(self.start_sniffing())
        except Exception as e:
            logger.error(f"❌ Critical Engine Error: {e}")
        finally:
            new_loop.close()
            logger.info("⚙️ Engine loop closed.")
