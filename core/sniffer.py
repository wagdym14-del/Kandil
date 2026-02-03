import asyncio
import websockets
import json
import logging
import time
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass

# الحفاظ على نظام التسجيل الخاص بك
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
    تم التطوير للحفاظ على جودة الأداء تحت قيود السحاب.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str, archiver, workers: int = 2):
        self.wss_url = wss_url
        self.archiver = archiver
        self.workers_count = workers
        self._queue = asyncio.Queue(maxsize=1000)
        self.is_running = False

    async def _fetch_coin_info(self, mint: str) -> Optional[Dict]:
        """الاستعلام الاستخباراتي السريع مع معالجة الأخطاء"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                url = f"https://frontend-api.pump.fun/coins/{mint}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
                return None
        except Exception as e:
            logger.debug(f"API Fetch Hint: {e}")
            return None

    async def start_sniffing(self):
        self.is_running = True
        # إطلاق العمال (Worker Pool) كما في هيكلك الأصلي
        for i in range(self.workers_count):
            asyncio.create_task(self._worker_logic(i))

        while self.is_running:
            try:
                # إضافة ping_interval و ping_timeout لضمان عدم فصل Streamlit للاتصال
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=20, 
                    ping_timeout=10
                ) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [SYSTEM] Sovereign Radar Online & API Linked.")
                    
                    while self.is_running:
                        msg = await ws.recv()
                        # فلترة ذ
