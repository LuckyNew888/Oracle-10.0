# oracle_engine.py
from collections import Counter

class OracleEngine:
    def __init__(self):
        self.history = []  # เก็บผลย้อนหลัง ['P','B','T',...]
        self.memory_failed_patterns = set()  # เก็บ pattern ที่เคยพลาด

    def update_history(self, result):
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def remove_last(self):
        if self.history:
            self.history.pop()

    def reset_history(self):
        self.history = []
        self.memory_failed_patterns = set()

    # 1. DNA Pattern Analysis (detect pattern loops)
    def detect_patterns(self):
        patterns = []
        h = self.history

        # Detect Pingpong (B-P-B-P)
        if len(h) >= 4:
            last4 = h[-4:]
            if last4 == ['B','P','B','P'] or last4 == ['P','B','P','B']:
                patterns.append('Pingpong')

        # Detect Two-Cut (BB-PP-BB-PP)
        if len(h) >= 4:
            last4 = h[-4:]
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # Detect Dragon (long streak)
        for i in range(3, 7):  # check 3 to 6 same in a row
            if len(h) >= i:
                if len(set(h[-i:])) == 1:
                    patterns.append('Dragon')

        # Detect Broken Pattern (example)
        # This is example and can be expanded with real logic
        if len(h) >= 7:
            last7 = h[-7:]
            if last7.count('P') > 4 and last7.count('B') < 3:
                patterns.append('Broken Pattern')

        return patterns

    # 2. Momentum Tracker
    def detect_momentum(self):
        h = self.history
        momentum = []
        # Check if last 3+ are same (Momentum)
        if len(h) >= 3:
            last3 = h[-3:]
            if len(set(last3)) == 1:
                momentum.append(f"{last3[0]}3+")

        # Check Steady Repeat (e.g. PBPBPBP)
        if len(h) >= 7:
            seq = h[-7:]
            pattern = ['P','B','P','B','P','B','P']
            if seq == pattern:
                momentum.append("Steady Repeat")

        # Ladder Momentum example (simplified)
        # Could be improved with full logic
        return momentum

    # 3. Trap Zone Detection
    def in_trap_zone(self):
        h = self.history
        if len(h) < 2:
            return False
        last2 = h[-2:]
        trap_pairs = [('P','B'), ('B','P')]
        # Unstable zone pattern examples:
        if tuple(last2) in trap_pairs:
            return True
        # Add more trap detection as needed
        return False

    # 4. Confidence Engine (0-100%)
    def confidence_score(self):
        if not self.history or len(self.history) < 5:
            return 0
        patterns = self.detect_patterns()
        momentum = self.detect_momentum()
        trap = self.in_trap_zone()
        score = 50
        if patterns:
            score += 20
        if momentum:
            score += 15
        if trap:
            score -= 40
        if score < 0:
            score = 0
        if score > 100:
            score = 100
        return score

    # 5. Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
    def update_failed_pattern(self, pattern_name):
        self.memory_failed_patterns.add(pattern_name)

    def is_pattern_failed(self, pattern_name):
        return pattern_name in self.memory_failed_patterns

    # 6. Intuition Logic (fallback)
    def intuition_predict(self):
        h = self.history
        if len(h) < 3:
            return 'T'  # Tie หรือไม่มั่นใจ
        last3 = h[-3:]
        # ตัวอย่างตีความ pattern
        if last3 == ['P','B','P']:
            return 'P'
        if last3 == ['B','B','P']:
            return 'P'
        # เพิ่มกฎได้ตามต้องการ
        return 'T'

    # 7. Backtest Simulation (simplified)
    def backtest_accuracy(self):
        # สมมติให้ 0 หรือ 100 เป็นค่าเริ่มต้น
        # ควรใส่ระบบเก็บผลจริงและทำนายจริงเพื่อคำนวณ
        return 70  # ตัวอย่างค่าความแม่นยำ

    # ฟังก์ชันทำนายผลถัดไป
    def predict_next(self):
        score = self.confidence_score()
        if score < 60:
            return 'T'  # Confidence ต่ำ หลีกเลี่ยงแทง
        # ใช้ pattern วิเคราะห์จริง
        patterns = self.detect_patterns()
        if patterns:
            # ตัวอย่างใช้ pattern แรกทำนาย
            pat = patterns[0]
            if self.is_pattern_failed(pat):
                return 'T'  # งดแทงเพราะเคยพลาด
            if pat == 'Dragon':
                return self.history[-1]  # ตามมังกร
            if pat == 'Pingpong':
                # สลับฝั่ง
                last = self.history[-1]
                return 'P' if last == 'B' else 'B'
            if pat == 'Two-Cut':
                return 'P'  # สมมติแทง P
        # ถ้าไม่มี pattern ชัด
        return self.intuition_predict()

    # แปลง history เป็น emoji
    def get_history_emojis(self):
        emoji_map = {'P': '🔵', 'B': '🔴', 'T': '🟢'}
        return [emoji_map.get(r, '?') for r in self.history]
