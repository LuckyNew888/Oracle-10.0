from typing import Literal, List, Optional, Tuple, Dict

Outcome = Literal["P", "B", "T"]

class RuleEngine:
    """
    โมดูล RuleEngine: ทำนายตามกฎง่ายๆ เช่น การออกซ้ำ 3 ครั้ง
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 3:
            return None
        # ถ้า 3 ผลลัพธ์ล่าสุดเหมือนกัน ให้ทำนายผลลัพธ์นั้น
        if history[-1] == history[-2] == history[-3]:
            return history[-1]
        return None

class PatternAnalyzer:
    """
    โมดูล PatternAnalyzer: ทำนายตามรูปแบบที่กำหนดไว้ล่วงหน้า
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last6 = "".join(history[-6:]) # นำ 6 ผลลัพธ์ล่าสุดมาต่อกันเป็นสตริง
        patterns = {
            "PPBB": "P", "BBPP": "B",
            "PBPB": "P", "BPBP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPP": "P", "BBBB": "B"
        }
        # ตรวจสอบว่า 6 ผลลัพธ์ล่าสุดตรงกับรูปแบบใดหรือไม่
        for pat, pred in patterns.items():
            if last6.endswith(pat):
                return pred
        return None

class TrendScanner:
    """
    โมดูล TrendScanner: ทำนายตามแนวโน้มส่วนใหญ่ใน 10 ผลลัพธ์ล่าสุด
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        recent = history[-10:] # 10 ผลลัพธ์ล่าสุด
        # ถ้า Player ออกมากกว่า 6 ครั้งใน 10 ครั้งล่าสุด ให้ทำนาย Player
        if recent.count("P") > 6:
            return "P"
        # ถ้า Banker ออกมากกว่า 6 ครั้งใน 10 ครั้งล่าสุด ให้ทำนาย Banker
        if recent.count("B") > 6:
            return "B"
        return None

class TwoTwoPattern:
    """
    โมดูล TwoTwoPattern: ทำนายตามรูปแบบ 2-2 (XXYY)
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 4:
            return None
        h = history[-4:] # 4 ผลลัพธ์ล่าสุด
        # ถ้า 2 ตัวแรกเหมือนกัน และ 2 ตัวหลังเหมือนกัน และ 2 กลุ่มนี้ต่างกัน (XXYY)
        if h[0] == h[1] and h[2] == h[3] and h[0] != h[2]:
            return h[0] # ทำนายตัวแรกของกลุ่มแรก
        return None

class ConfidenceScorer:
    """
    ConfidenceScorer: ให้คะแนนความมั่นใจในการทำนายโดยรวมจากโมดูลต่างๆ
    """
    def score(self, predictions: dict, history: List[Outcome]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        tally = {"P": 0, "B": 0}
        # นับคะแนนโหวตจากแต่ละโมดูล
        for name, pred in predictions.items():
            if pred in tally:
                tally[pred] += 1
        
        # ถ้าไม่มีโมดูลใดทำนายเลย
        if not any(tally.values()):
            return None, None, None, None
        
        # หาผลลัพธ์ที่มีคะแนนโหวตสูงสุด
        best = max(tally, key=tally.get)
        # หาชื่อโมดูลที่ทำนายผลลัพธ์ที่ดีที่สุด
        source = next((k for k, v in predictions.items() if v == best), None)
        # คำนวณความมั่นใจเป็นเปอร์เซ็นต์
        confidence = int((tally[best] / len(predictions)) * 100)
        # ดึงรหัสรูปแบบจาก PatternAnalyzer อีกครั้งเพื่อส่งคืน (แม้ว่าจะไม่ใช่ source หลัก)
        pattern_code = PatternAnalyzer().predict(history) 
        return best, source, confidence, pattern_code

class OracleBrain:
    """
    OracleBrain: คลาสหลักที่จัดการประวัติผลลัพธ์ ทำการทำนาย และคำนวณความแม่นยำ
    """
    def __init__(self):
        self.history: List[Outcome] = [] # เก็บประวัติผลลัพธ์ P/B
        self.ties: List[int] = [] # เก็บจำนวน Tie ที่เกิดขึ้นกับแต่ละมือ P/B
        self.result_log: List[Outcome] = [] # บันทึกผลลัพธ์จริงทั้งหมด (P, B, T)
        self.prediction_log: List[Optional[Outcome]] = [] # บันทึกการทำนายของ OracleBrain
        self.last_prediction: Optional[Outcome] = None # การทำนายล่าสุด
        self.show_initial_wait_message = True # แฟล็กสำหรับข้อความเริ่มต้น

    def add_result(self, outcome: Outcome, tie_count: int = 0):
        """
        เพิ่มผลลัพธ์ของเกมลงในประวัติ
        """
        if outcome == "T":
            # ถ้าเป็น Tie, และมีประวัติ P/B อยู่แล้ว ให้เพิ่มจำนวน Tie ของมือล่าสุด
            if self.history:
                self.ties[-1] += 1
            # ถ้า Tie เป็นผลลัพธ์แรกสุด (ซึ่งไม่ควรเกิดขึ้นในเกมปกติ) จะถูกละเว้นสำหรับ history
            else:
                pass 
        else:
            # ถ้าเป็น P หรือ B, เพิ่มผลลัพธ์และจำนวน Tie ที่สะสม (ปกติจะเป็น 0 ถ้าไม่ใช่ Tie)
            self.history.append(outcome)
            self.ties.append(tie_count)
            self.result_log.append(outcome)
            self.prediction_log.append(self.last_prediction)

    def remove_last(self):
        """
        ลบผลลัพธ์ล่าสุดออกจากประวัติ
        """
        if self.history:
            self.history.pop()
        if self.ties:
            self.ties.pop()
        if self.result_log:
            self.result_log.pop()
        if self.prediction_log:
            self.prediction_log.pop()
        self.last_prediction = None # รีเซ็ตการทำนายล่าสุด

    def reset(self):
        """
        รีเซ็ตประวัติและสถานะทั้งหมด
        """
        self.history.clear()
        self.ties.clear()
        self.result_log.clear()
        self.prediction_log.clear()
        self.last_prediction = None
        self.show_initial_wait_message = True

    def calculate_miss_streak(self) -> int:
        """
        คำนวณจำนวนครั้งที่ทำนายผิดพลาดติดต่อกัน
        """
        streak = 0
        # วนย้อนกลับเพื่อตรวจสอบผลลัพธ์และการทำนาย
        for i in range(len(self.result_log) - 1, -1, -1):
            pred = self.prediction_log[i]
            actual = self.result_log[i]
            
            # ข้ามผลเสมอและการทำนายที่เป็น None
            if actual == "T" or pred is None:
                continue 
            
            # ถ้าทำนายผิด ให้เพิ่ม streak
            if pred != actual:
                streak += 1
            # ถ้าทำนายถูก ให้หยุด streak
            else:
                break 
        return streak

    def get_module_accuracy(self) -> Dict[str, float]:
        """
        คำนวณความแม่นยำของแต่ละโมดูลการทำนาย
        """
        modules = {
            "Rule": RuleEngine(),
            "Pattern": PatternAnalyzer(),
            "Trend": TrendScanner(),
            "2-2": TwoTwoPattern()
        }
        accuracy = {}
        
        # คำนวณความแม่นยำของแต่ละโมดูลโดยจำลองการทำนายในอดีต
        for name, module in modules.items():
            module_wins = 0
            module_total_predictions = 0
            
            # วนผ่านประวัติ P/B ทั้งหมด (ไม่รวม Tie ใน history)
            for i in range(len(self.history)):
                history_slice = self.history[:i] # ประวัติที่มีอยู่ ณ จุดนั้น
                
                # ตรวจสอบเฉพาะเมื่อมีประวัติเพียงพอสำหรับโมดูลที่จะทำนายได้ (อย่างน้อย 4 สำหรับ TwoTwoPattern)
                if len(history_slice) >= 4: 
                    module_pred = module.predict(history_slice)
                    if module_pred is not None:
                        module_total_predictions += 1
                        # เปรียบเทียบกับผลลัพธ์จริงของมือปัจจุบัน (history[i])
                        if module_pred == self.history[i]:
                            module_wins += 1
            
            accuracy[name] = (module_wins / module_total_predictions * 100) if module_total_predictions > 0 else 0
        return accuracy


    def predict_next(self) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        """
        ทำการทำนายผลลัพธ์ถัดไปโดยรวมจากโมดูลต่างๆ
        """
        # นับเฉพาะผลลัพธ์ที่ไม่ใช่ Tie สำหรับเงื่อนไข 20 มือ
        non_tie_history_count = len([x for x in self.history if x in ("P", "B")])
        if non_tie_history_count < 20:
            return None, None, None, None

        miss_streak = self.calculate_miss_streak()
        # ถ้าทำนายผิดติดต่อกัน 6 ครั้งขึ้นไป จะไม่ทำนาย
        if miss_streak >= 6:
            return None, None, None, None

        # สร้างอินสแตนซ์ของแต่ละโมดูล
        rule = RuleEngine()
        pattern = PatternAnalyzer()
        trend = TrendScanner()
        two_two = TwoTwoPattern()
        scorer = ConfidenceScorer()

        # ให้แต่ละโมดูลทำการทำนาย
        predictions = {
            "Rule": rule.predict(self.history),
            "Pattern": pattern.predict(self.history),
            "Trend": trend.predict(self.history),
            "2-2": two_two.predict(self.history)
        }

        # ให้ ConfidenceScorer ประเมินผลการทำนาย
        result, source, confidence, pattern_code = scorer.score(predictions, self.history)
        self.last_prediction = result # บันทึกการทำนายล่าสุด
        return result, source, confidence, pattern_code
    
    @staticmethod
    def _generate_big_road_columns_for_display(history: List[Outcome], ties: List[int]):
        """
        สร้างโครงสร้าง Big Road สำหรับการแสดงผล โดยเชื่อมโยง Tie เข้ากับมือ P/B ที่เกี่ยวข้อง
        แต่ละคอลัมน์เป็นลิสต์ของ (outcome, total_ties_for_this_hand) tuples
        จำกัด 6 แถวสำหรับ Big Road มาตรฐาน
        """
        if not history:
            return []

        display_columns = []
        current_display_col = []
        last_display_outcome = None
        
        # p_b_idx ใช้ติดตาม index ใน history และ ties ที่เป็นผลลัพธ์ P/B
        p_b_idx = -1 

        # วนผ่าน result_log เพื่อสร้าง Big Road ที่ถูกต้อง
        for i, actual_outcome_from_log in enumerate(history): # ใช้ history แทน result_log เพราะ history มีเฉพาะ P/B
            if actual_outcome_from_log == "T":
                # ถ้าเป็น Tie, จะถูกจัดการโดยการเพิ่ม tie_count ของมือ P/B ก่อนหน้า
                # ใน OracleBrain's internal history (ผ่าน add_result)
                # ดังนั้น ที่นี่เราไม่จำเป็นต้องทำอะไรพิเศษสำหรับ Tie เพราะ tie_count
                # จะถูกดึงมาเมื่อมือ P/B ที่เกี่ยวข้องถูกประมวลผล
                continue # ข้ามผลลัพธ์ 'T' ในลูปนี้
            else: # ถ้าเป็นผลลัพธ์ P หรือ B
                p_b_idx += 1 # เลื่อน index สำหรับ history/ties
                
                # ดึงจำนวน Tie ทั้งหมดที่เกี่ยวข้องกับมือ P/B ปัจจุบัน
                current_tie_count = ties[p_b_idx] 
                
                # ถ้าผลลัพธ์ปัจจุบันเหมือนกับผลลัพธ์สุดท้ายในคอลัมน์ และคอลัมน์ยังไม่เต็ม 6 แถว
                if actual_outcome_from_log == last_display_outcome and len(current_display_col) < 6:
                    current_display_col.append((actual_outcome_from_log, current_tie_count))
                else:
                    # ถ้าผลลัพธ์เปลี่ยน หรือคอลัมน์เต็ม ให้ขึ้นคอลัมน์ใหม่
                    if current_display_col:
                        display_columns.append(current_display_col)
                    current_display_col = [(actual_outcome_from_log, current_tie_count)]
                    last_display_outcome = actual_outcome_from_log
        
        if current_display_col: # เพิ่มคอลัมน์สุดท้ายถ้ามี
            display_columns.append(current_display_col)
            
        return display_columns


    def get_simplified_trend(self) -> Optional[str]:
        """
        วิเคราะห์คอลัมน์ Big Road ล่าสุดเพื่อระบุแนวโน้มอย่างง่าย
        """
        # ใช้ history และ ties เพื่อคำนวณ Big Road display columns
        big_road_cols = self._generate_big_road_columns_for_display(self.history, self.ties)
        
        if len(big_road_cols) < 3: # ต้องมีอย่างน้อย 3 คอลัมน์เพื่อดูแนวโน้มพื้นฐาน
            return None

        # ดู 3 คอลัมน์สุดท้ายเพื่อหาแนวโน้ม
        last_col_start_outcomes = [col[0][0] for col in big_road_cols[-3:]]

        # ตรวจสอบรูปแบบ "ปิงปอง" (Alternating)
        if len(last_col_start_outcomes) >= 3 and \
           last_col_start_outcomes[-1] != last_col_start_outcomes[-2] and \
           last_col_start_outcomes[-2] != last_col_start_outcomes[-3]:
            return "ปิงปอง (Alternating)" 
        
        # ตรวจสอบรูปแบบ "สลับ" ทั่วไป (Choppy)
        if len(last_col_start_outcomes) >= 2 and last_col_start_outcomes[-1] != last_col_start_outcomes[-2]:
            return "สลับ (Choppy)" 

        # ตรวจสอบรูปแบบ "มังกร" (Streaky)
        last_col = big_road_cols[-1]
        if len(last_col) >= 4: # Streak 4 ครั้งขึ้นไปถือเป็น "มังกร"
            if last_col[0][0] == "P":
                return "มังกร P (Streaky P)"
            elif last_col[0][0] == "B":
                return "มังกร B (Streaky B)"
        
        # ถ้าไม่เป็นปิงปอง สลับ หรือมังกรที่ชัดเจน
        # แสดง "ตามแนวโน้ม" ถ้ามีประวัติเพียงพอ (อย่างน้อย 20 มือ)
        return "ตามแนวโน้ม (Following Trend)" if len(self.history) >= 20 else None

