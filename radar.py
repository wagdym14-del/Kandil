import os
import json
import time
from playwright.sync_api import sync_playwright

BASE_DIR = "/sdcard/Sovereign_Project"
if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)

def run(playwright):
    # الربط بمتصفح Bromite المفتوح يدوياً عبر المنفذ 9222
    browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0]

    def save_log(data, source):
        with open(os.path.join(BASE_DIR, "smart_archive.json"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%H:%M:%S"), "source": source, "data": data}) + "\n")

    def intercept(response):
        if "json" in response.header_value("content-type"):
            try:
                data = response.json()
                save_log(data, "API")
                print(f"[📂] تم سحب بيانات جديدة من: {response.url[:30]}")
            except: pass

    page.on("response", intercept)
    print("🚀 البوت متصل بمتصفحك الآن. قم بالتصفح يدوياً وسأقوم بسحب البيانات في الخلفية...")
    page.wait_for_timeout(999999999)

if __name__ == "__main__":
    with sync_playwright() as p:
        run(p)
