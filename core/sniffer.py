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
    [2026-02-03] النسخة السيادية - الاستقرار المطلق.
    تمت إضافة 'مكابح الذاكرة' لمنع إعادة التشغيل اللانهائي.
    """
    PROGRAM_ID = "6EF8rrecthR5DkZJbdz4P8hHKXY6yizQ2EtJhEqNpump"

    def __init__(self, wss_url: str = None, archiver=None, workers: int = 1):
        try:
            self.wss_url = st.secrets.get("WSS_URL_PRIMARY") or wss_url
        except Exception:
            self.wss_url = wss_url
            
        self.archiver = archiver
        self.is_running = False
        self._msg_count = 0 # تتبع عدد الرسائل لمنع التراكم

    async def start_sniffing(self):
        if not self.wss_url: return
        self.is_running = True
        
        while self.is_running:
            try:
                # [تعديل الاستقرار]: استخدام ping_interval وإعدادات اتصال صارمة
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=20, 
                    ping_timeout=15,
                    max_size=500_000 # تحديد حجم الرسالة بـ 0.5 ميجا كحد أقصى لحماية الذاكرة
                ) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [RADAR] Monitoring Active & Stabilized.")

                    while self.is_running:
                        try:
                            raw_msg = await asyncio.wait_for(ws.recv(), timeout=35)
                            self._msg_count += 1
                            
                            # [مكابح الطوارئ]: كل 50 رسالة، خذ استراحة 0.1 ثانية لتنظيف الذاكرة
                            if self._msg_count % 50 == 0:
                                await asyncio.sleep(0.1)

                            data = json.loads(raw_msg)
                        except asyncio.TimeoutError:
                            await ws.ping()
                            continue

                        if "params" not in data: continue
                        
                        val = data["params"]["result"]["value"]
                        logs = val.get("logs", [])
                        if not logs: continue 

                        logs_str = "|".join(logs)
                        
                        # [تعديل الجودة]: رصد صناع السوق عبر "بصمة البوت"
                        event_type = None
                        if "mintTo" in logs_str and "InitializeMint" in logs_str:
                            event_type = "MM_BUNDLE_LAUNCH" 
                        elif logs_str.count("Trade") > 15: # رفع المعيار لـ 15 لضمان رصد البوتات فقط
                            event_type = "MM_HFT_ACTIVITY" 

                        if event_type and self.archiver:
                            # [2026-02-03] أرشفة وتتبع صناع السوق بمحافظهم المتعددة
                            await self.archiver.analyze_and_archive(
                                wallet=val.get("signature"),
                                raw_data={"logs": logs},
                                behavior_tag=event_type
                            )
                        
                        # تصفير العداد لتجنب الأرقام الضخمة
                        if self._msg_count > 10000: self._msg_count = 0

            except Exception as e:
                # زيادة وقت التبريد لـ 15 ثانية لضمان استقرار السيرفر
                logger.warning(f"🔄 Cooling down (15s)... Stability Protection Active.")
                await asyncio.sleep(15)
