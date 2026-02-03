import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignSniffer.Ultra")

@dataclass
class MarketEvent:
    signature: str
    timestamp: float
    event_type: str
    risk_level: int
    raw_logs: List[str]
    coin_data: Optional[Dict] = None

class PumpSniffer:
    """
    [2026-02-03] المحرك الفائق - النسخة السيادية المستقرة.
    تم التطوير للعمل بتناغم مع واجهة Streamlit على GitHub.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str, archiver, workers: int = 2):
        self.wss_url = wss_url
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=1000)
        self.is_running = False

    async def _fetch_coin_info(self, mint: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                url = f"https://frontend-api.pump.fun/coins/{mint}"
                resp = await client.get(url)
                return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.debug(f"API Fetch Hint: {e}")
            return None

    async def _worker_logic(self, worker_id: int):
        """منطق معالجة البيانات المؤرشفة"""
        while self.is_running:
            event = await self._queue.get()
            try:
                # هنا نقوم بدمج البيانات مع الأرشيف
                if self.archiver:
                    self.archiver.record_event(event)
                logger.info(f"Worker-{worker_id} Archived Signature: {event.signature[:10]}...")
            except Exception as e:
                logger.error(f"Worker Error: {e}")
            finally:
                self._queue.task_done()

    async def start_sniffing(self):
        self.is_running = True
        for i in range(self.workers_count):
            asyncio.create_task(self._worker_logic(i))

        while self.is_running:
            try:
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=20, 
                    ping_timeout=10
                ) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [SYSTEM] Sovereign Radar Online.")
                    
                    while self.is_running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        # استخراج التوقيع والسجلات (Logs)
                        if "params" in data:
                            logs = data["params"]["result"]["value"]["logs"]
                            signature = data["params"]["result"]["value"]["signature"]
                            
                            # تحليل سريع لمعرفة نوع الحدث (مثلاً: Create)
                            event_type = "Unknown"
                            if any("Program log: Instruction: Create" in l for l in logs):
                                event_type = "Create"
                            
                            event = MarketEvent(
                                signature=signature,
                                timestamp=time.time(),
                                event_type=event_type,
                                risk_level=50, # قيمة افتراضية للتحليل
                                raw_logs=logs
                            )
                            
                            # وضع الحدث في الطابور للمعالجة
                            if not self._queue.full():
                                await self._queue.put(event)

            except Exception as e:
                logger.warning(f"Connection Lost: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def start(self):
        """الجسر: تشغيل المحرك غير المتزامن داخل Thread متزامن"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.start_sniffing())
        except Exception as e:
            logger.error(f"Engine Bridge Error: {e}")
        finally:
            loop.close()
