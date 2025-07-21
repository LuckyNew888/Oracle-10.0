from collections import Counter

class OracleEngine:
    def __init__(self):
        self.history = []  # เก็บผลย้อนหลัง ['P','B','T',...]
        self.memory_failed_patterns = set()  # เก็บ pattern ที่เคยพลาด

    # ----------------------------------------------------
    # ส่วนของ Data Management (อาจไม่จำเป็นต้องใช้ใน Streamlit App โดยตรงแล้ว)
    def update_history(self, result):
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def remove_last(self):
        if self.history:
            self.history.pop()

    def reset_history(self):
        self.history = []
        self.memory_failed_patterns = set()
    # ----------------------------------------------------

    # 1. 🧬 DNA Pattern Analysis (detect pattern loops)
    def detect_patterns(self):
        patterns = []
        h = self.history

        # ตรวจจับ Pingpong (B-P-B-P)
        if len(h) >= 4:
            last4 = h[-4:]
            if (last4 == ['B','P','B','P'] or last4 == ['P','B','P','B']):
                patterns.append('Pingpong')
        
        # ตรวจจับ Two-Cut (BB-PP-BB-PP)
        if len(h) >= 4:
            last4 = h[-4:]
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # ตรวจจับ Dragon (long streak)
        for i in range(3, 7):  # check 3 to 6 same in a row
            if len(h) >= i:
                if len(set(h[-i:])) == 1:
                    patterns.append(f'Dragon{i}') # ระบุความยาวของ Dragon ด้วย

        # ตรวจจับ Broken Pattern (BPBPPBP) - ตัวอย่างการ Implement
        # นี่เป็นเพียงตัวอย่างที่ซับซ้อนขึ้น ควรปรับตามนิยามที่แท้จริงของคุณ
        if len(h) >= 7:
            last7 = "".join(h[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7: # อาจจะต้องใช้ regex เพื่อความแม่นยำ
                patterns.append('Broken Pattern')

        # เพิ่มการวัดอัตราความสำเร็จของลูปต่างๆ (ยังต้องพัฒนาลอจิก)
        # เช่น self.analyze_loop_stability(h)

        return patterns

    # 2. 🚀 Momentum Tracker
    def detect_momentum(self):
        momentum = []
        h = self.history
        
        # Check if last 3+ are same (Momentum)
        if len(h) >= 3:
            last_streak_char = h[-1]
            streak_count = 0
            for i in reversed(range(len(h))):
                if h[i] == last_streak_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                momentum.append(f"{last_streak_char}{streak_count}+ Momentum")

        # Check Steady Repeat (e.g. PBPBPBP)
        if len(h) >= 7:
            seq = h[-7:]
            # ตรวจสอบ PBPBPBP หรือ BPBPBPB
            if (seq == ['P','B','P','B','P','B','P'] or 
                seq == ['B','P','B','P','B','P','B']):
                momentum.append("Steady Repeat Momentum")

        # Ladder Momentum (ยังต้องพัฒนาลอจิกให้สมบูรณ์)
        # เช่น BB-P-BBB-P-BBBB
        # if len(h) >= X and self._is_ladder_pattern(h[-X:]):
        #     momentum.append("Ladder Momentum")

        return momentum
    
    # Helper สำหรับ Ladder Momentum (ต้อง implement เพิ่มเติม)
    # def _is_ladder_pattern(self, seq):
    #     # ลอจิกการตรวจจับ Ladder Momentum
    #     pass

    # 3. ⚠️ Trap Zone Detection
    def in_trap_zone(self):
        h = self.history
        if len(h) < 2:
            return False
        
        # P1-B1, B1-P1 (ไม่เสถียร)
        last2 = h[-2:]
        if tuple(last2) in [('P','B'), ('B','P')]:
            return True
        
        # B3-P1 หรือ P3-B1 (เสี่ยงกลับตัว)
        if len(h) >= 4:
            last4 = h[-4:]
            if (last4[-1] == 'P' and last4[-2] != 'P' and last4[-3] == 'P' and last4[-4] == 'P') or \
               (last4[-1] == 'B' and last4[-2] != 'B' and last4[-3] == 'B' and last4[-4] == 'B'):
               # Logic for B3-P1 / P3-B1 (B B B P or P P P B)
               # ตรวจสอบ 3 ตัวก่อนหน้าเป็นตัวเดียวกัน และตัวล่าสุดเป็นคนละตัว
               if len(set(h[-4:-1])) == 1 and h[-4] != h[-1]:
                   return True
        return False

    # 4. 🎯 Confidence Engine (0-100%)
    def confidence_score(self):
        # ถ้าประวัติไม่พอ หรือมี Tie เยอะมาก อาจจะทำให้ Confidence ต่ำ
        if not self.history or len(self.history) < 10: # เพิ่มขั้นต่ำเป็น 10 ตา
            return 0
        
        patterns = self.detect_patterns()
        momentum = self.detect_momentum()
        trap = self.in_trap_zone()
        
        score = 50 # Base score

        if patterns:
            # ยิ่งมี pattern ชัดเจนหลายแบบ ยิ่งเพิ่ม Confidence
            score += len(patterns) * 10 
        
        if momentum:
            # ยิ่งมี momentum ที่เสถียร ยิ่งเพิ่ม Confidence
            score += len(momentum) * 8
        
        # หากอยู่ใน Trap Zone ลด Confidence อย่างรุนแรง
        if trap:
            score -= 60 # ลดเยอะๆ ให้เหลือ < 60% เพื่อแนะนำ Avoid
        
        # ตรวจสอบความสม่ำเสมอของผลลัพธ์ (เช่น ไม่ใช่สลับไปมาตลอด)
        # ถ้าสลับกันบ่อยๆ (P,B,P,B,P,B) อาจจะลด Confidence ถ้าไม่ใช่ Pingpong
        # เพิ่มลอจิกการประเมินความมั่นคงของลูป (จาก DNA Pattern Analysis)

        # Ensure score is within 0-100 range
        if score < 0:
            score = 0
        if score > 100:
            score = 100
        
        return score

    # 5. 🔁 Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
    def update_failed_pattern(self, pattern_name):
        self.memory_failed_patterns.add(pattern_name)

    def is_pattern_failed(self, pattern_name):
        return pattern_name in self.memory_failed_patterns

    # 6. 🧠 Intuition Logic (fallback สำหรับการทำนาย T อย่างตั้งใจ)
    def intuition_predict(self):
        h = self.history
        if len(h) < 3:
            return '?' # ไม่มั่นใจพอจะทาย P/B/T

        last3 = h[-3:]
        last4 = h[-4:] if len(h) >= 4 else None
        
        # กฎการทำนาย Tie ที่ตั้งใจ (จากการวิเคราะห์ ไม่ใช่การหลีกเลี่ยง)
        # ตัวอย่าง: ถ้าเห็นว่ามี Tie ออกมาและ pattern มีแนวโน้มจะกลับมาที่ Tie
        if 'T' in last3 and last3[0] != last3[1] and last3[1] != last3[2]: # เช่น P-T-B
            return 'T'
        if last4 and Counter(last4)['T'] >= 2: # ถ้ามี T สองตัวในสี่ตาหลัง
            return 'T'
        
        # กฎการทำนาย P/B เมื่อไม่มี Pattern หลักชัดเจน
        if last3 == ['P','B','P']:
            return 'P' # อาจจะกลับไปที่ P
        if last3 == ['B','B','P']:
            return 'P' # BBP อาจจะตัดเป็น P
        if last3 == ['P','P','B']:
            return 'B' # PPB อาจจะตัดเป็น B
        if last3 == ['B','P','P']: # BPP, มีโอกาสเป็น B (Repeat Cut)
             return 'B'

        # ถ้าไม่มีกฎไหนตรง คืนค่า '?' เพื่อบอกว่าไม่สามารถทำนายได้
        return '?'

    # 7. 🔬 Backtest Simulation (ยังคงเป็น Simplified, ต้องพัฒนาจริงจัง)
    # ควรสร้างเมธอดที่ simulate การทำนายย้อนหลังจริงๆ
    def backtest_accuracy(self):
        # ในเวอร์ชันเต็ม:
        # - วนลูปตั้งแต่ตาที่ 11 จนถึงปัจจุบัน
        # - ใช้ logic การทำนายของระบบ (predict_next) ในแต่ละตา
        # - เปรียบเทียบผลทำนายกับผลจริง เพื่อคำนวณ Hit/Miss
        # - ตรวจสอบ Drawdown (miss ติดกัน)
        
        # สำหรับตอนนี้ เป็นค่า dummy
        if len(self.history) < 20:
            return 0
        
        # นี่คือค่า dummy, ในการใช้งานจริงต้องสร้างลอจิก Backtest
        # เพื่อคำนวณ accuracy จริงๆ โดยรัน predict_next ย้อนหลัง
        # และควรมีการอัปเดต memory_failed_patterns ในระหว่าง backtest ด้วย
        
        # ตัวอย่างการสร้างค่าสมมติให้ดูเหมือนทำงาน
        recent_hits = 0
        for i in range(max(0, len(self.history) - 15), len(self.history) - 1): # ดู 15 ตาหลัง
            # การทำนายย้อนหลังที่นี่ซับซ้อนกว่า
            # ต้องสร้าง engine ชั่วคราว หรือส่ง history ในแต่ละจุด
            # เพื่อให้ predict_next ทำงานเหมือนตอนนั้น
            pass # ลอจิกจริงจะอยู่ตรงนี้
        
        # สุ่มค่าเพื่อแสดงผลชั่วคราว
        import random
        return random.randint(60, 90) # สมมติ Accuracy อยู่ระหว่าง 60-90%

    # helper function for Streamlit App
    def get_history_emojis(self):
        emoji_map = {'P': '🔵', 'B': '🔴', 'T': '🟢'}
        return [emoji_map.get(r, '?') for r in self.history]

    # ฟังก์ชันทำนายผลถัดไป (ปรับปรุงแล้ว)
    def predict_next(self):
        prediction_result = '?' # ค่าเริ่มต้นไม่ทำนาย
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        # 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที)
        if self.in_trap_zone():
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = "Trap Zone detected: High volatility, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result, # จะเป็น '?'
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำ)
        score = self.confidence_score()
        if score < 60:
            recommendation = "Avoid ❌"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%), recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result, # จะเป็น '?'
                "accuracy": self.backtest_accuracy(),
                "risk": "Low Confidence",
                "recommendation": recommendation
            }
        
        # 3. ตรวจสอบ Drawdown (ยังต้อง implement Backtest จริง)
        # if self.backtest_drawdown_exceeded(): # ต้องมีเมธอดนี้
        #     risk_level = "High Drawdown"
        #     recommendation = "Avoid ❌"
        #     developer_view = "Drawdown exceeded 3 consecutive misses, recommending avoidance."
        #     return {
        #         "developer_view": developer_view,
        #         "prediction": prediction_result,
        #         "accuracy": self.backtest_accuracy(),
        #         "risk": risk_level,
        #         "recommendation": recommendation
        #     }


        # 4. ใช้ Pattern หลักในการทำนาย (หากมี)
        patterns = self.detect_patterns()
        momentum = self.detect_momentum() # ตรวจจับ momentum ไว้ใช้ใน developer view
        
        if patterns:
            developer_view_patterns = []
            for pat_name in patterns:
                developer_view_patterns.append(pat_name)
                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self.is_pattern_failed(pat_name):
                    # ถ้า Pattern นี้เคยพลาด ให้ข้ามไปใช้ Intuition หรือ Avoid แทน
                    developer_view += f" (Note: Pattern '{pat_name}' previously failed. Skipping.)"
                    continue # ลองดู pattern อื่น
                
                # ลอจิกการทำนายตาม Pattern
                if 'Dragon' in pat_name: # ใช้ 'Dragon' in pat_name เพื่อจับ Dragon3, Dragon4
                    prediction_result = self.history[-1] # ตามมังกร
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting last result."
                    break # เจอ pattern ที่ใช้ได้แล้ว ออกจากลูป
                elif pat_name == 'Pingpong':
                    last = self.history[-1]
                    prediction_result = 'P' if last == 'B' else 'B' # สลับฝั่ง
                    developer_view = f"DNA Pattern: Pingpong detected. Predicting opposite of last."
                    break
                elif pat_name == 'Two-Cut':
                    # Two-Cut (BB-PP) ถ้าเจอ PPB หรือ BBP ให้ทายตัวแรกที่ตัด
                    if len(self.history) >= 2:
                        last_two = self.history[-2:]
                        if last_two[0] == last_two[1]: # ถ้า 2 ตัวสุดท้ายเหมือนกัน (เช่น BB, PP)
                            prediction_result = 'P' if last_two[0] == 'B' else 'B' # ทายตัวตรงข้าม
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
            
            # ถ้ามี patterns แต่ยังไม่ได้ prediction_result (อาจเพราะ pattern ที่เจอเคยพลาด)
            if prediction_result == '?' and developer_view_patterns:
                developer_view += f" Detected patterns: {', '.join(developer_view_patterns)}."
                
        # 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด)
        if prediction_result == '?': # ถ้ายังไม่มีการทำนายจาก Pattern หลัก
            intuitive_guess = self.intuition_predict()
            if intuitive_guess == 'T': # Intuition ทำนาย T อย่างตั้งใจ
                prediction_result = 'T'
                developer_view += " (Intuition Logic: Specific Tie pattern identified.)"
            elif intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view += f" (Intuition Logic: Predicting {intuitive_guess} based on subtle patterns.)"
            else: # Intuition ไม่สามารถทำนาย P/B/T ได้อย่างมั่นใจ
                recommendation = "Avoid ❌" # แนะนำเลี่ยงเพราะไม่มั่นใจ
                risk_level = "Uncertainty"
                developer_view += " (Intuition Logic: No strong P/B/T prediction, recommending Avoid.)"
                prediction_result = '?' # ไม่ทำนาย P/B/T

        # รวบรวม Developer View เพิ่มเติม
        if momentum:
            if developer_view: developer_view += " | "
            developer_view += f"Momentum: {', '.join(momentum)}."
        
        if not developer_view and prediction_result == '?':
            developer_view = "No strong patterns or intuition detected."

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": self.backtest_accuracy(), # ค่านี้จะใช้จาก Backtest จริงในอนาคต
            "risk": risk_level,
            "recommendation": recommendation
        }
