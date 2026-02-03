import asyncio
import os
import logging
import signal
import time
import subprocess
import sys
from dotenv import load_dotenv
import yaml
from typing import Optional

# استيراد المكونات الاحترافية
from core.archiver import MMArchiver
from core.sniffer import PumpSniffer

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | [%(name)s] -> %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Sovereign_Apex")

class SovereignEngine:
    """
    [2026-02-03] محرك القمة المدمج (الرادار + الواجهة الذكية).
    إدارة العمليات المتوازية لضمان أرشفة سلوك صناع السوق وعرضها حياً.
    """
    def __init__(self):
        self.start_time = time.time()
        self.version = "1.5.0-APEX"
        load_dotenv()
        
        self.config = self._load_config()
        self.archiver = MMArchiver(
            db_path=self.config['analysis_engine']['archiver_settings']['db_path']
        )
        self.sniffer: Optional[PumpSniffer] = None
        self.dashboard_proc: Optional[subprocess.Popen] = None
        self._running = False

    def _load_config(self) -> dict:
        try:
            with open("config.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.critical(f"💥 Failed to load config.yaml: {e}")
            raise SystemExit(1)

    def _launch_dashboard(self):
        """إطلاق واجهة Dashboard.py كعملية مستقلة"""
        logger.info("🎨 [UI] Launching Sovereign Intelligence Dashboard...")
        try:
            # تشغيل streamlit في وضع headless (بدون فتح متصفح تلقائي إذا كنت على سيرفر)
            self.dashboard_proc = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", "dashboard.py",
                "--server.port", "8501",
                "--server.headless", "true"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.info("✅ [UI] Dashboard is active on http://localhost:8501")
        except Exception as e:
            logger.error(f"❌ [UI] Failed to start dashboard: {e}")

    async def boot_sequence(self):
        """تسلسل الإقلاع الشامل"""
        logger.info(f"🛡️  [SYSTEM] Initializing Sovereign Engine v{self.version}")
        
        # 1. تهيئة الذاكرة السيادية
        await self.archiver.boot_system()
        
        # 2. إطلاق الواجهة الرسومية (The Dashboard)
        self._launch_dashboard()
        
        # 3. جلب الروابط وتدقيقها
        wss_url = os.getenv("WSS_URL_PRIMARY")
        if not wss_url:
            logger.error("❌ [SECURITY] Critical Error: WSS_URL_PRIMARY is missing in .env")
            return

        # 4. بناء الرادار
        self.sniffer = PumpSniffer(wss_url=wss_url, archiver=self.archiver)
        
        self._running = True
        logger.info("📡 [RADAR] Scanning Solana for MM Fingerprints... [2026-02-03]")
        
        await self._main_loop()

    async def _main_loop(self):
        retry_count = 0
        while self._running:
            try:
                await self.sniffer.start_sniffing()
            except Exception as e:
                retry_count += 1
                wait_time = min(retry_count * 5, 60)
                logger.error(f"⚠️ [RECOVERY] Connection lost. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            
            if not self._running:
                break

    async def shutdown(self, signal_type=None):
        """الإغلاق الآمن للمحرك والواجهة"""
        if not self._running:
            return
            
        self._running = False
        logger.warning(f"🔌 [SHUTDOWN] Signal received. Cleaning up processes...")
        
        # إيقاف الرادار
        if self.sniffer:
            self.sniffer.stop()
        
        # إيقاف واجهة الويب
        if self.dashboard_proc:
            self.dashboard_proc.terminate()
            logger.info("✅ [UI] Dashboard process terminated.")
            
        uptime = time.time() - self.start_time
        logger.info(f"🏁 [OFFLINE] System Secured. Uptime: {uptime:.2f}s.")
        
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [t.cancel() for t in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    engine = SovereignEngine()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(engine.shutdown(s)))

    try:
        await engine.boot_sequence()
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
