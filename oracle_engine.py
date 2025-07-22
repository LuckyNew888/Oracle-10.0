# oracle_engine.py
# OracleEngine v1.0 – วิเคราะห์แนวโน้มเบื้องต้นจากผลย้อนหลังโดยไม่ใช้ระบบ Pattern
# พร้อมฟังก์ชันเสริมให้ใช้งานกับ Streamlit ได้

class OracleEngine:
    def __init__(self):
        self.history = []  # เก็บผลย้อนหลัง เช่น ['P', 'B', 'B', 'P', 'T']

    def add_result(self, result):
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def reset(self):
        self.history = []

    def analyze(self):
        if len(self.history) < 20:
            return "🔄 รอสะสมข้อมูลอย่างน้อย 20 ตา"

        last_5 = self.history[-5:]
        p_count = last_5.count('P')
        b_count = last_5.count('B')
        t_count = last_5.count('T')

        if p_count >= 4:
            return "🔵 แนวโน้ม: ผู้เล่น (Player)"
        elif b_count >= 4:
            return "🔴 แนวโน้ม: เจ้ามือ (Banker)"
        elif t_count >= 3:
            return "🟢 แนวโน้ม: เสมอ (Tie)"
        else:
            return "⚪ แนวโน้มไม่ชัดเจน"

# -------------------------------
# ฟังก์ชันจำลองไว้ให้ระบบ Streamlit ใช้งานได้ (Placeholder)

def _cached_backtest_accuracy():
    # ยังไม่มีระบบ Backtest เต็มใน v1.0
    return "ยังไม่เปิดใช้ระบบ Backtest ในเวอร์ชันนี้"

def _build_big_road_data(history):
    """
    สร้าง Big Road ขนาดเล็กจากประวัติ เช่น [['P', 'P'], ['B'], ['P']]
    เพื่อใช้แสดงใน Streamlit (แบบง่าย)
    """
    if not history:
        return []

    grid = []
    col = []

    prev = history[0]
    for res in history:
        if res == prev:
            col.append(res)
        else:
            grid.append(col)
            col = [res]
            prev = res
    if col:
        grid.append(col)
    return grid
