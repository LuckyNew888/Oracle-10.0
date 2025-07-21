from collections import Counter
import random

class OracleEngine:
    def __init__(self):
        self.history = []
        self.memory_failed_patterns = set()

    # --- ส่วน Data Management (สำหรับ Engine เอง) ---
    def update_history(self, result):
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def remove_last(self):
        if self.history:
            self.history.pop()

    def reset_history(self):
        self.history = []
        self.memory_failed_patterns = set()

    # --- 1. 🧬 DNA Pattern Analysis (ตรวจจับรูปแบบ) ---
    def detect_patterns(self):
        """ตรวจจับรูปแบบต่างๆ เช่น Pingpong, Two-Cut, Dragon, Broken Pattern, Triple Cut"""
        patterns = []
        h = self.history

        # ตรวจจับ Pingpong (B-P-B-P หรือ P-B-P-B)
        if len(h) >= 4:
            last4 = h[-4:]
            if (last4 == ['B','P','B','P'] or last4 == ['P','B','P','B']):
                patterns.append('Pingpong')
        
        # ตรวจจับ Two-Cut (BB-PP หรือ PP-BB)
        if len(h) >= 4:
            last4 = h[-4:]
            # ตรวจสอบว่า 2 ตัวแรกเหมือนกัน 2 ตัวหลังเหมือนกัน และ 2 คู่ต่างกัน
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # ตรวจจับ Dragon (long streak: 3 ถึง 6 ตัวติดกัน)
        for i in range(3, 7): 
            if len(h) >= i:
                if len(set(h[-i:])) == 1: # ถ้าตัวสุดท้าย i ตัวเหมือนกันหมด
                    patterns.append(f'Dragon ({i})') # ระบุความยาวของ Dragon ด้วย

        # ตรวจจับ Triple Cut (ตัด 3) เช่น PPPBBB หรือ BBBPPP
        if len(h) >= 6:
            last6 = h[-6:]
            # ตรวจสอบว่า 3 ตัวแรกเหมือนกัน และ 3 ตัวหลังเหมือนกัน และ 3 ตัวแรกต่างจาก 3 ตัวหลัง
            if (last6[0] == last6[1] == last6[2] and 
                last6[3] == last6[4] == last6[5] and 
                last6[0] != last6[3]):
                patterns.append('Triple Cut')

        # ตรวจจับ Broken Pattern (BPBPPBP) - ตัวอย่างการ Implement
        # **Note:** ลอจิกนี้เป็นเพียงตัวอย่างเริ่มต้น ควรพัฒนาให้แม่นยำยิ่งขึ้นตามนิยามที่แท้จริง
        if len(h) >= 7:
            last7 = "".join(h[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7: 
                patterns.append('Broken Pattern')

        return patterns

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self):
        """ตรวจจับแรงเหวี่ยง เช่น B3+, P3+, Steady Repeat"""
        momentum = []
        h = self.history
        
        # ตรวจสอบ Momentum (3 ตัวขึ้นไปเหมือนกัน)
        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
            # นับจำนวนตัวที่เหมือนกันจากท้ายสุด
            for i in reversed(range(len(h))):
                if h[i] == last_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                momentum.append(f"{last_char}{streak_count}+ Momentum")

        # ตรวจจับ Steady Repeat (PBPBPBP หรือ BPBPBPB)
        if len(h) >= 7:
            seq = h[-7:]
            if (seq == ['P','B','P','B','P','B','P'] or 
                seq == ['B','P','B','P','B','P','B']):
                momentum.append("Steady Repeat Momentum")

        return momentum
    
    # --- 3. ⚠️ Trap Zone Detection (ตรวจจับโซนอันตราย) ---
    def in_trap_zone(self):
        """ตรวจจับโซนที่การเปลี่ยนแปลงเร็วและอันตราย"""
        h = self.history
        if len(h) < 2:
            return False
        
        # P1-B1, B1-P1 (ไม่เสถียร)
        last2 = h[-2:]
        if tuple(last2) in [('P','B'), ('B','P')]:
            return True

        # B3-P1 หรือ P3-B1 (เสี่ยงกลับตัว) - 3 ตัวติดแล้วตัด
        if len(h) >= 4:
            if (len(set(h[-4:-1])) == 1 and h[-4] != h[-1]):
                return True
        return False

    # --- 4. 🎯 Confidence Engine (ระบบประเมินความมั่นใจ 0-100%) ---
    def confidence_score(self):
        """คำนวณคะแนนความมั่นใจของระบบในการทำนาย"""
        if not self.history or len(self.history) < 10: 
            return 0
        
        patterns = self.detect_patterns()
        momentum = self.detect_momentum()
        trap = self.in_trap_zone()
        
        score = 50

        if patterns:
            score += len(patterns) * 10 
        
        if momentum:
            score += len(momentum) * 8
        
        if trap:
            score -= 60 
        
        if score < 0:
            score = 0
        if score > 100:
            score = 100
        
        return score

    # --- 5. 🔁 Memory Logic (จดจำ Pattern ที่เคยพลาด) ---
    def update_failed_pattern(self, pattern_name):
        """เพิ่ม pattern ที่ทำให้ทายผิดลงในหน่วยความจำ"""
        self.memory_failed_patterns.add(pattern_name)

    def is_pattern_failed(self, pattern_name):
        """ตรวจสอบว่า pattern นี้เคยทำให้ทายผิดหรือไม่"""
        return pattern_name in self.memory_failed_patterns

    # --- 6. 🧠 Intuition Logic (ลอจิกเชิงลึกเมื่อไม่มี Pattern ชัดเจน) ---
    def intuition_predict(self):
        """ใช้ลอจิกเชิงลึกในการทำนายเมื่อไม่มี Pattern ชัดเจน"""
        h = self.history
        if len(h) < 3:
            return '?'

        last3 = h[-3:]
        last4 = h[-4:] if len(h) >= 4 else None
        
        if 'T' in last3 and last3.count('T') == 1 and last3[0] != last3[1] and last3[1] != last3[2]:
            return 'T'
        if last4 and Counter(last4)['T'] >= 2:
            return 'T'
        
        if last3 == ['P','B','P']:
            return 'P'
        if last3 == ['B','B','P']:
            return 'P'
        if last3 == ['P','P','B']:
            return 'B'
        if len(h) >= 5 and h[-5:] == ['B','P','B','P','P']:
             return 'B'

        return '?'

    # --- 7. 🔬 Backtest Simulation (ทดสอบผลย้อนหลัง) ---
    def backtest_accuracy(self):
        """
        คำนวณความแม่นยำของระบบจากการทำนายย้อนหลัง (จำเป็นต้องพัฒนาลอจิกจริง)
        และตรวจสอบ Drawdown
        """
        if len(self.history) < 20:
            return 0
        
        # TODO: Implement การจำลองการทำนายย้อนหลังจริงๆ
        return random.randint(60, 90) # สุ่มค่าความแม่นยำระหว่าง 60-90% (ค่า dummy)

    def backtest_drawdown_exceeded(self):
        """
        ตรวจสอบว่า Drawdown (miss ติดกัน) เกิน 3 ครั้งหรือไม่ (จำเป็นต้องพัฒนาลอจิกจริง)
        """
        # TODO: Implement ลอจิกการตรวจสอบ Drawdown จริงๆ
        return False # สมมติว่ายังไม่เกิน (ค่า dummy)

    # --- ฟังก์ชันหลักในการทำนายผลถัดไป ---
    def predict_next(self):
        """
        ฟังก์ชันหลักในการวิเคราะห์และทำนายผลลัพธ์ถัดไป
        คืนค่าเป็น dictionary ที่มี prediction, risk, recommendation, developer_view
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        # --- 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที) ---
        if self.in_trap_zone():
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = "Trap Zone detected: High volatility, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำกว่าเกณฑ์) ---
        score = self.confidence_score()
        if score < 60:
            recommendation = "Avoid ❌"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%), recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": "Low Confidence",
                "recommendation": recommendation
            }
        
        # --- 3. ตรวจสอบ Drawdown (หากเกิน 3 miss ติดกัน ให้งดเดิมพัน) ---
        if self.backtest_drawdown_exceeded(): 
            risk_level = "High Drawdown"
            recommendation = "Avoid ❌"
            developer_view = "Drawdown exceeded 3 consecutive misses, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 4. ใช้ Pattern หลักในการทำนาย (หากมี) ---
        patterns = self.detect_patterns()
        momentum = self.detect_momentum() 
        
        if patterns:
            developer_view_patterns_list = []
            for pat_name in patterns:
                developer_view_patterns_list.append(pat_name)
                
                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self.is_pattern_failed(pat_name):
                    developer_view += f" (Note: Pattern '{pat_name}' previously failed. Skipping.)"
                    continue
                
                # ลอจิกการทำนายตาม Pattern ที่มั่นใจ
                if 'Dragon' in pat_name: 
                    prediction_result = self.history[-1]
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting last result."
                    break
                elif pat_name == 'Pingpong':
                    last = self.history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    developer_view = f"DNA Pattern: Pingpong detected. Predicting opposite of last."
                    break
                elif pat_name == 'Two-Cut':
                    if len(self.history) >= 2:
                        last_two = self.history[-2:]
                        if last_two[0] == last_two[1]:
                            prediction_result = 'P' if last_two[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
                elif pat_name == 'Triple Cut': # NEW: Logic for Triple Cut
                    if len(self.history) >= 3:
                        last_three = self.history[-3:]
                        if len(set(last_three)) == 1: # E.g., PPP
                            # Predict the opposite of the current triple
                            prediction_result = 'P' if last_three[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Triple Cut detected. Predicting opposite of last three."
                            break
            
            if developer_view_patterns_list and not developer_view:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            elif developer_view_patterns_list:
                developer_view += f" | Other patterns: {', '.join(developer_view_patterns_list)}."
                
        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if prediction_result == '?': # ถ้ายังไม่มีการทำนายจาก Pattern หลัก
            intuitive_guess = self.intuition_predict()
            
            if intuitive_guess == 'T':
                prediction_result = 'T'
                developer_view += " (Intuition Logic: Specific Tie pattern identified.)"
            elif intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view += f" (Intuition Logic: Predicting {intuitive_guess} based on subtle patterns.)"
            else:
                recommendation = "Avoid ❌"
                risk_level = "Uncertainty"
                developer_view += " (Intuition Logic: No strong P/B/T prediction, recommending Avoid.)"
                prediction_result = '?'

        # รวบรวม Developer View เพิ่มเติมจาก Momentum
        if momentum:
            if developer_view: developer_view += " | "
            developer_view += f"Momentum: {', '.join(momentum)}."
        
        # หากไม่มีอะไรเลยและยังทำนายไม่ได้
        if not developer_view and prediction_result == '?':
            developer_view = "No strong patterns or intuition detected."

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": self.backtest_accuracy(), 
            "risk": risk_level,
            "recommendation": recommendation
        }

    # Helper function for Streamlit App
    def get_history_emojis(self):
        """แปลงประวัติผลลัพธ์เป็น emoji สำหรับแสดงผล"""
        emoji_map = {'P': '🔵', 'B': '🔴', 'T': '🟢'}
        return [emoji_map.get(r, '?') for r in self.history]
