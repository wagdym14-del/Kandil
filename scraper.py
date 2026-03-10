import os
import time
import json
import subprocess

# البصمة (Pattern): هذه مصفوفة سداسية تعبر عن "شكل بيانات الصفقات"
# يجب العثور عليها مرة واحدة (أشرح لك الطريقة لاحقاً)
DATA_PATTERN = b"\x00\x00\x00\x00\x01\x00\x00\x05" 

def get_browser_pid(name="chrome"):
    """تحديد معرف العملية (PID) تلقائياً للمتصفح"""
    try:
        pid = subprocess.check_output(["pgrep", "-n", name]).decode().strip()
        return pid
    except:
        return None

def find_data_address(pid):
    """البحث عن مصفوفة الصفقات في الذاكرة (Memory Signature Scanning)"""
    maps_path = f"/proc/{pid}/maps"
    mem_path = f"/proc/{pid}/mem"
    with open(maps_path, 'r') as maps_file:
        for line in maps_file:
            if "rw-p" in line: # البحث عن الذاكرة القابلة للقراءة والكتابة
                addr_range = line.split('-')
                start, end = int(addr_range[0], 16), int(addr_range[1].split(' ')[0], 16)
                with open(mem_path, "rb") as mem:
                    mem.seek(start)
                    data = mem.read(end - start)
                    pos = data.find(DATA_PATTERN)
                    if pos != -1: return start + pos
    return None

def run_pro_scraper():
    pid = get_browser_pid()
    if not pid: print("المتصفح غير مفتوح"); return
    
    address = find_data_address(pid)
    buffer = []
    
    while True:
        try:
            # القراءة الاحترافية
            with open(f"/proc/{pid}/mem", "rb") as mem:
                mem.seek(address)
                raw_data = mem.read(256)
                buffer.append(raw_data.hex())
            
            # منطق الأرشفة التلقائي (50 صفقة أو 3 ثوانٍ)
            if len(buffer) >= 50 or (time.time() % 3 < 0.1):
                with open(f"archive_{int(time.time())}.json", "w") as f:
                    json.dump(buffer, f)
                buffer = []
            
            time.sleep(0.001)
        except:
            address = find_data_address(pid) # إعادة البحث إذا تغير الموقع
            time.sleep(1)

if __name__ == "__main__":
    run_pro_scraper()
