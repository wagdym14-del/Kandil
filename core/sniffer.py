import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

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
    [2026-02-03] المحرك الفائق - النسخة النهائية المستقرة.
    تجمع بين الرصد المتوازي (Worker Pool) والـ API لتعزيز البيانات.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str, archiver, workers: int = 2):
        self.wss_url = wss_url
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=1000) # حجم متوازن للسحاب
        self.is_running = False

    async def _fetch_coin_info(self, mint: str) -> Optional[Dict]:
        """الاستعلام من الـ API السريع لإثراء الخزنة بالبيانات"""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                url = f"https://frontend-api.pump.fun/coins/{mint}"
                resp = await client.get(url)
                return resp.json() if resp.status_code == 200 else None
        except: return None

    async def start_sniffing(self):
        self.is_running = True
        # تشغيل العمال (Worker Pool) لضمان عدم ضياع أي ثانية
        for i in range(self.workers_count):
            asyncio.create_task(self._worker_logic(i))

        while self.is_running:
            try:
                async with websockets.connect(self.wss_url, ping_interval=25) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [SYSTEM] Radar Online & API Linked.")
                    while self.is_running:
                        msg = await ws.recv()
                        # تصفية أولية (Raw Filter) لحماية المعالج
                        if "mintTo" in msg or msg.count("Trade") > 15:
                            if not self._queue.full():
                                await self._queue.put((msg, time.time()))
            except Exception:
                await asyncio.sleep(10)

    async def _worker_logic(self, worker_id: int):
        while self.is_running:
            try:
                raw_msg, arrival_time = await self._queue.get()
                data = json.loads(raw_msg)
                
                if "params" in data:
                    val = data["params"]["result"]["value"]
                    logs = val.get("logs", [])
                    logs_str = "|".join(logs)
                    
                    event = None
                    # رصد إطلاق الباندل (صانع السوق المحترف)
                    if "InitializeMint" in logs_str:
                        event = MarketEvent(val["signature"], time.time(), "INSTANT_BUNDLE_LAUNCH", 95, logs)
                        mint = self._extract_mint(logs)
                        if mint: event.coin_data = await self._fetch_coin_info(mint)
                    
                    # رصد نشاط البوتات الكثيفة
                    elif logs_str.count("Trade") > 15:
                        event = MarketEvent(val["signature"], time.time(), "MM_HFT_ACTIVITY", 70, logs)

                    if event and self.archiver:
                        # الأرشفة مع حساب زمن الاستجابة الفعلي
                        latency = (time.time() - arrival_time) * 1000
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature,
                            raw_data={"logs": logs, "api": event.coin_data, "latency": latency},
                            behavior_tag=event.event_type
                        )
                self._queue.task_done()
                await asyncio.sleep(0.01) # راحة للمعالج
            except Exception: pass

    def _extract_mint(self, logs: List[str]) -> Optional[str]:
        for log in logs:
            if "mintTo" in log:
                parts = log.split(" ")
                for p in parts:
                    if p.endswith("pump"): return p
        return None
