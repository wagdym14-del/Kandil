import asyncio
import websockets
import json
import logging
import time
import streamlit as st
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignSniffer.Ultra")

class PumpSniffer:
    """
    [2026-02-03] المحرك السيادي (النسخة الخفيفة).
    فلترة فورية في الهواء وتجاهل للضجيج لضمان عدم الانهيار.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str = None, archiver=None, workers: int = 1):
        try:
            self.wss_url = st.secrets.get("WSS_URL_PRIMARY") or wss_url
        except Exception:
            self.wss_url = wss_url
            
        self.archiver = archiver
        self.is_running = False

    async def start_sniffing(self):
        if not self.wss_url: return
        self.is_running = True
        
        while self.is_running:
            try:
                async with websockets.connect(self.wss_url) as ws:
                    # الاشتراك
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [RADAR] Monitoring Active...")

                    while self.is_running:
                        raw_msg = await ws.recv()
                        data = json.loads(raw_msg)
                        
                        # [المصفاة الفورية]: تجاهل الرسائل التي لا تحتوي على بيانات فعلية
                        if "params" not in data: continue
                        
                        val = data["params"]["result"]["value"]
                        logs = val.get("logs", [])
                        logs_str = "|".join(logs)
                        
                        # [تجاهل غير الضروري]: تصفية صارمة لرصد صناع السوق فقط
                        event_type = None
                        if "mintTo" in logs_str and "InitializeMint" in logs_str:
                            event_type = "MM_BUNDLE_LAUNCH" # إطلاق بمحافظ متعددة
                        elif logs_str.count("Trade") > 10: # رفع المعيار لـ 10 لتقليل الضغط
                            event_type = "MM_HFT_ACTIVITY" # نشاط بوت مكثف

                        # إذا كانت الرسالة "ضرورية"، نؤرشفها فوراً
                        if event_type and self.archiver:
                            await self.archiver.analyze_and_archive(
                                wallet=val.get("signature"),
                                raw_data={"logs": logs},
                                behavior_tag=event_type
                            )
            except Exception as e:
                logger.warning("🔄 Reconnecting in 5s...")
                await asyncio.sleep(5)
