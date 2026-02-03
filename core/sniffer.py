import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

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
    [2026-02-03] النسخة السيادية المخصصة للسحاب (Cloud-Optimized).
    توازن بين الأداء الاحترافي وقيود الذاكرة في Streamlit.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str, archiver):
        self.wss_url = wss_url
        self.archiver = archiver
        self._queue = asyncio.Queue(maxsize=500) # تقليل الحجم لمنع انفجار RAM
        self.is_running = False

    async def _fetch_api_data(self, mint: str):
        """جلب البيانات من API سريع جداً وخفيف"""
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(f"https://frontend-api.pump.fun/coins/{mint}")
                return resp.json() if resp.status_code == 200 else None
        except: return None

    async def start_sniffing(self):
        self.is_running = True
        # عامل واحد ذكي يكفي لبيئة Streamlit
        asyncio.create_task(self._worker_logic())

        while self.is_running:
            try:
                # إعدادات اتصال "Keep-Alive" متطورة لمنع فصل السحاب
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=20, 
                    ping_timeout=10
                ) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [CLOUD-MODE] Active & Shielded.")

                    while self.is_running:
                        raw_msg = await ws.recv()
                        
                        # [جودة]: فلترة أولية للنص الخام لتوفير الذاكرة
                        if "mintTo" in raw_msg or raw_msg.count("Trade") > 15:
                            if not self._queue.full():
                                await self._queue.put((raw_msg, time.time()))
                        
                        # إعطاء فرصة لـ Streamlit لتحديث الواجهة
                        await asyncio.sleep(0.001) 
            except Exception:
                await asyncio.sleep(10)

    async def _worker_logic(self):
        while self.is_running:
            try:
                raw_msg, arrival_time = await self._queue.get()
                data = json.loads(raw_msg)
                
                if "params" in data:
                    val = data["params"]["result"]["value"]
                    logs = val.get("logs", [])
                    logs_str = "|".join(logs)
                    
                    event = None
                    if "InitializeMint" in logs_str:
                        event = MarketEvent(val["signature"], time.time(), "BUNDLE_LAUNCH", 95, logs)
                        # جلب البيانات الإضافية فوراً
                        mint = self._extract_mint(logs)
                        if mint: event.coin_data = await self._fetch_api_data(mint)
                    elif logs_str.count("Trade") > 15:
                        event = MarketEvent(val["signature"], time.time(), "MM_HFT", 70, logs)

                    if event and self.archiver:
                        # أرشفة ذكية بناءً على طلبك [2026-02-03]
                        await self.archiver.analyze_and_archive(
                            wallet=event.signature,
                            raw_data={"logs": logs, "metadata": event.coin_data},
                            behavior_tag=event.event_type
                        )
                self._queue.task_done()
            except Exception: pass

    def _extract_mint(self, logs: List[str]) -> Optional[str]:
        for log in logs:
            if "mintTo" in log:
                parts = log.split(" ")
                for p in parts:
                    if p.endswith("pump"): return p
        return None
