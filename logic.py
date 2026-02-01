def calculate_mm_score(token_data):
    """حساب اليقين بناءً على البنود الـ 30"""
    score = 0
    # بند 11: اختبار العرض المتناقص
    if token_data['vol_dryness'] < 0.15: score += 25
    # بند 16: جدار الزجاج
    if token_data['glass_wall']: score += 25
    # بند 5: القاع الأعلى
    if token_data['higher_low']: score += 25
    return score

def liquidity_alert_logic(old_pool, new_pool):
    """المنطق الذي طلبته: التنبيه عند انتقال السيولة"""
    if new_pool != old_pool:
        return "⚠️ The maker is transferring liquidity to currency (X); buying pressure here will stop, start taking profits immediately!"
    return None
