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
    [2026-02-03] النسخة الاحترافية المستقرة.
    تحسين استهلاك الذاكرة وإضافة نظام Keep-Alive لمنع إعادة التشغيل.
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
                # [تعديل 1]: إضافة ping_interval للحفاظ على الاتصال حياً ومنع السيرفر من فصلك
                async with websockets.connect(
                    self.wss_url, 
                    ping_interval=20, 
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [self.PROGRAM_ID]}, {"commitment": "processed"}]
                    }))
                    logger.info("📡 [RADAR] Stable Connection Established...")

                    while self.is_running:
                        # [تعديل 2]: انتظار الرسالة مع timeout لمنع التجميد (Freeze)
                        try:
                            raw_msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(raw_msg)
                        except asyncio.TimeoutError:
                            # إذا لم تصل رسالة، نرسل نبضة يدوية للتأكد من حيوية الرابط
                            await ws.ping()
                            continue

                        if "params" not in data: continue
                        
                        val = data["params"]["result"]["value"]
                        logs = val.get("logs", [])
                        if not logs: continue # [تعديل 3]: تجاهل الرسائل الفارغة فوراً لتوفير الذاكرة

                        logs_str = "|".join(logs)
                        
                        event_type = None
                        # رصد صناع السوق (العملات الجديدة أو البوتات المكثفة)
                        if "mintTo" in logs_str and "InitializeMint" in logs_str:
                            event_type = "MM_BUNDLE_LAUNCH" 
                        elif logs_str.count("Trade") > 12: # رفعنا المعيار لـ 12 لتقليل الزحام
                            event_type = "MM_HFT_ACTIVITY" 

                        if event_type and self.archiver:
                            # الأرشفة والتتبع بناءً على طلبك السابق [2026-02-03]
                            await self.archiver.analyze_and_archive(
                                wallet=val.get("signature"),
                                raw_data={"logs": logs},
                                behavior_tag=event_type
                            )
                            # استراحة مجهرية لضمان عدم استهلاك الـ CPU بالكامل
                            await asyncio.sleep(0.01)

            except Exception as e:
                # [تعديل 4]: زيادة وقت التبريد عند حدوث خطأ لمنع حظر الـ IP
                logger.warning(f"🔄 Cooling down for 10s... Error: {str(e)[:30]}")
                await asyncio.sleep(10)
