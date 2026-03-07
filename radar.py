import os
import json
import time
import re
from playwright.sync_api import sync_playwright

# إعداد المسارات
BASE_DIR = os.path.expanduser("~/Desktop/solx")
USER_DATA_DIR = os.path.join(BASE_DIR, "user_profile")
BROWSERS_PATH = os.path.join(BASE_DIR, "pw-browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_PATH

def run(playwright):
    context = playwright.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=False,
        no_viewport=True, 
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
    )

    def classify_data(data):
        """ذكاء اصطناعي مصغر لتصنيف نوع البيانات المجمعة"""
        text_data = str(data).lower()
        if any(x in text_data for x in ["price", "liquidity", "marketcap"]):
            return "MARKET_STATS"
        if any(x in text_data for x in ["signature", "tx", "hash"]):
            return "TRADES_LOG"
        if any(x in text_data for x in ["wallet", "address", "balance"]):
            return "WALLET_INFO"
        return "GENERAL_DATA"

    def save_organized_log(source_type, tab_title, content, url=""):
        """تنظيم المعلومات في هيكل بيانات واضح"""
        category = classify_data(content)
        log_entry = {
            "time": time.strftime("%H:%M:%S"),
            "category": category,
            "source": source_type,
            "tab": tab_title[:30],
            "details": content,
            "url_snippet": url[-50:] if url else "N/A"
        }
        
        # حفظ في ملف منظم بصيغة JSON Lines لسهولة القراءة لاحقاً
        with open(os.path.join(BASE_DIR, "smart_archive.json"), "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def smart_interceptor(response):
        try:
            if "json" in response.header_value("content-type"):
                data = response.json()
                # فحص ما إذا كانت البيانات ضخمة ومهمة (ليست مجرد أيقونات أو إعدادات)
                if len(str(data)) > 200: 
                    title = response.frame.page.title()
                    save_organized_log("API", title, data, response.url)
                    print(f"[📂 تصنيف]: تم حفظ {classify_data(data)} من {title[:15]}")
        except:
            pass

    def socket_interceptor(ws):
        title = ws.page.title()
        ws.on("framereceived", lambda payload: handle_ws(payload, title))

    def handle_ws(payload, title):
        try:
            data = json.loads(payload)
            if len(payload) > 100:
                save_organized_log("SOCKET", title, data)
                print(f"[⚡ لحظي]: صيد منظّم من {title[:15]}")
        except:
            pass

    def setup_page(page):
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => False});")
        page.on("response", smart_interceptor)
        page.on("websocket", socket_interceptor)

    context.on("page", setup_page)
    page = context.pages[0] if context.pages else context.new_page()
    setup_page(page)
    
    print("\n" + "📊" * 15)
    print("🚀 محرك التنظيم الذكي انطلق!")
    print("💡 المعلومات الآن تُحفظ مصنفة حسب النوع (تجارة، أسعار، محافظ).")
    print("📊" * 15 + "\n")

    page.goto("https://axiom.trade")
    page.wait_for_timeout(999999999)

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
