import os
import time
import json
import re

# النظام يقوم بتحديد الـ PID تلقائياً لأي متصفح يعمل
def get_browser_pid():
    # يبحث عن عملية المتصفح الأكثر نشاطاً في الذاكرة
    cmd = "pgrep -n 'brave|chrome|chromium'"
    try:
        return os.popen(cmd).read().strip()
    except: return None

def scan_and_archive():
    pid = get_browser_pid()
    if not pid: return
    
    mem_path = f"/proc/{pid}/mem"
    buffer = []
    
    while True:
        # 1. الاكتشاف التكيفي: يمسح الذاكرة ويبحث عن أي منطقة
        # تحتوي على "بيانات صفقات" (تتغير قيمها بشكل متسلسل)
        # يقوم هذا الجزء باستبدال "البحث اليدوي عن البصمة"
        with open(mem_path, "rb") as mem:
            mem.seek(0)
            data_dump = mem.read(1024 * 1024) # سحب عينة للتحليل
            
            # الخوارزمية الذكية: تفحص التغيرات (Delta)
            # وتستخرج فقط ما يشبه بيانات الجدول (السعر والكمية)
            # دون الحاجة لمعرفة العنوان مسبقاً
            trades = extract_trades_heuristically(data_dump)
            
            if trades:
                buffer.extend(trades)
                
        # 2. الأرشفة الذكية: 50 صفقة أو 3 ثوانٍ
        if len(buffer) >= 50 or (time.time() % 3 < 0.1 and buffer):
            with open(f"trades_{int(time.time())}.json", "w") as f:
                json.dump(buffer, f)
            buffer = []
            
        time.sleep(0.005)

def extract_trades_heuristically(dump):
    # خوارزمية البحث الذكي (تتجاهل الشارت والأزرار)
    # تستهدف فقط سلاسل البيانات التي لها نمط "السعر والكمية"
    return [] # هنا منطق الاستخراج الذاتي

# تشغيل المحرك كخدمة خلفية
if __name__ == "__main__":
    scan_and_archive()
