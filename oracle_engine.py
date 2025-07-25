# oracle_engine.py

import random

class OracleEngine:
    """
    OracleEngine เป็นคลาสที่ใช้สำหรับจัดการตรรกะการทำนายผลลัพธ์
    และติดตามสถานะการเรียนรู้ของระบบ
    """

    VERSION = "V1.14" # กำหนดเวอร์ชันของ OracleEngine

    def __init__(self):
        """
        เริ่มต้น OracleEngine กำหนดค่าเริ่มต้นสำหรับสถิติการชนะ
        และตัวแปรสถานะที่จำเป็น
        """
        # สถิติการชนะของแต่ละกลยุทธ์
        self.tam_sutr_wins = 0      # จำนวนครั้งที่ทำนาย 'ตาม' แล้วชนะ
        self.suan_sutr_wins = 0     # จำนวนครั้งที่ทำนาย 'สวน' แล้วชนะ
        self.pattern_analysis_wins = 0 # จำนวนครั้งที่ชนะจากการวิเคราะห์รูปแบบ
        self.momentum_wins = 0      # จำนวนครั้งที่ชนะจากการวิเคราะห์โมเมนตัม
        self.intuition_wins = 0     # จำนวนครั้งที่ชนะจากการทำนายด้วยสัญชาตญาณ (ในกรณีที่ระบบไม่มีข้อมูลพอ)

        # ตัวแปรสถานะสำหรับการเรียนรู้และการทำนาย
        self.last_prediction_context = None # เก็บข้อมูลการทำนายครั้งล่าสุด เพื่อใช้อัปเดตสถานะการเรียนรู้
        self.last_dominant_pattern_id = None # ID ของรูปแบบที่โดดเด่นครั้งล่าสุด (สำหรับ mock data)

        # สำหรับการทดสอบ (คุณสามารถปรับปรุงหรือเพิ่มตรรกะที่นี่ได้)
        self.prediction_counter = 0 # ตัวนับรอบ เพื่อให้ผลทำนายจำลองเปลี่ยนไปเรื่อยๆ

    def detect_dna_patterns(self, history):
        """
        (Placeholder) ตรวจจับรูปแบบ DNA จากประวัติผลลัพธ์
        ในเวอร์ชันจริง คุณจะใช้ตรรกะที่ซับซ้อนในการระบุรูปแบบซ้ำๆ
        และอาจจะกำหนด ID ให้กับรูปแบบที่โดดเด่น

        Args:
            history (list): รายการประวัติผลลัพธ์ เช่น [{'main_outcome': 'P'}, ...]

        Returns:
            dict: ข้อมูลเกี่ยวกับรูปแบบที่ตรวจพบ
        """
        # อัปเดต last_dominant_pattern_id สำหรับการทดสอบใน app.py
        if len(history) % 2 == 0:
            self.last_dominant_pattern_id = "PatternA"
        else:
            self.last_dominant_pattern_id = "PatternB"
        return {"detected_patterns": "Mock Pattern Analysis"} # Placeholder

    def detect_momentum(self, history):
        """
        (Placeholder) ตรวจจับโมเมนตัมจากประวัติผลลัพธ์
        ในเวอร์ชันจริง คุณจะวิเคราะห์แนวโน้มของผลลัพธ์

        Args:
            history (list): รายการประวัติผลลัพธ์

        Returns:
            str: ข้อมูลเกี่ยวกับโมเมนตัมที่ตรวจพบ
        """
        if len(history) > 5 and history[-1]['main_outcome'] == history[-2]['main_outcome']:
            return "Strong Momentum"
        return "No Strong Momentum" # Placeholder

    def predict_next(self, history, is_backtest=False):
        """
        ทำนายผลลัพธ์ถัดไปตามประวัติที่ให้มา

        Args:
            history (list): รายการประวัติผลลัพธ์ เช่น [{'main_outcome': 'P'}, ...]
            is_backtest (bool): ระบุว่ากำลังทำงานในโหมด backtest หรือไม่

        Returns:
            dict: พจนานุกรมที่มีผลทำนายและความเกี่ยวข้อง
                - 'prediction': 'P', 'B', 'T', '⚠️' (งดเดิมพัน), หรือ '?' (ยังไม่มีข้อมูล)
                - 'prediction_mode': 'ตาม', 'สวน', '⚠️', หรือ None
                - 'accuracy': ความแม่นยำของระบบ (string เช่น "75.00%")
                - 'developer_view': ข้อมูลรายละเอียดสำหรับนักพัฒนา
                - 'predicted_by': ระบุว่าทำนายด้วยวิธีใด (Pattern, Momentum, Intuition)
        """
        # อัปเดตตัวนับเพื่อทำให้ผลทำนายจำลองเปลี่ยนไปเรื่อยๆ
        if not is_backtest:
            self.prediction_counter += 1

        # กำหนดผลลัพธ์เริ่มต้น
        prediction = "?"
        prediction_mode = None
        predicted_by = "Not enough data"
        accuracy = "N/A"
        developer_view = "ยังไม่มีข้อมูลเพียงพอสำหรับวิเคราะห์ (ต้องมีอย่างน้อย 15 ตา)"

        # ตรวจสอบว่ามีข้อมูลเพียงพอสำหรับการทำนายหรือไม่
        if len(history) >= 15:
            # (Placeholder) ตรรกะการทำนายจริงจะอยู่ตรงนี้
            # สำหรับตอนนี้ เราจะใช้ตรรกะง่ายๆ เพื่อให้ app.py ทำงานได้

            # Simulate prediction based on simple alternating logic or random
            if self.prediction_counter % 2 == 0:
                prediction = "P"
                predicted_by = "Pattern Analysis" # จำลองว่ามาจาก Pattern
            else:
                prediction = "B"
                predicted_by = "Momentum" # จำลองว่ามาจาก Momentum

            # Simulate prediction mode
            prediction_mode = random.choice(["ตาม", "สวน"])

            # Simulate when to warn (e.g., if history shows high volatility or mixed signals)
            if len(history) % 5 == 0 and random.random() < 0.3: # Randomly show warning
                 prediction = "⚠️"
                 prediction_mode = "⚠️"
                 predicted_by = "Intuition (Low Confidence)"

            # Simulate accuracy (placeholder)
            total_playable_predictions = max(1, len(history) - 14) # Assuming first 14 are warm-up
            accurate_predictions = 0
            # This would normally involve replaying history and checking past predictions
            # For this mock, let's just use a fixed number or simple calculation
            if total_playable_predictions > 0:
                accurate_predictions = int(total_playable_predictions * 0.75) # Simulate 75% accuracy
            
            accuracy = f"{((self.pattern_analysis_wins + self.momentum_wins + self.intuition_wins) / max(1, total_playable_predictions)) * 100:.2f}%"


            # Generate developer view info
            developer_view = f"""
            ---
            [Developer View]
            Input History Length: {len(history)}
            Simulated Prediction: {prediction} (Predicted by: {predicted_by})
            Simulated Prediction Mode: {prediction_mode}

            Internal State (Mock):
            - tam_sutr_wins: {self.tam_sutr_wins}
            - suan_sutr_wins: {self.suan_sutr_wins}
            - pattern_analysis_wins: {self.pattern_analysis_wins}
            - momentum_wins: {self.momentum_wins}
            - intuition_wins: {self.intuition_wins}
            - Last dominant pattern ID: {self.last_dominant_pattern_id}

            Detected Patterns (Mock): {self.detect_dna_patterns(history)}
            Detected Momentum (Mock): {self.detect_momentum(history)}
            ---
            """
        
        # Store prediction context if not in backtest, for update_learning_state
        if not is_backtest:
            self.last_prediction_context = {
                'prediction': prediction,
                'prediction_mode': prediction_mode,
                'patterns': self.detect_dna_patterns(history),
                'momentum': self.detect_momentum(history),
                'intuition_applied': 'Intuition' in predicted_by, # Check if 'Intuition' was part of predicted_by
                'predicted_by': predicted_by,
                'dominant_pattern_id_at_prediction': self.last_dominant_pattern_id,
            }

        return {
            'prediction': prediction,
            'prediction_mode': prediction_mode,
            'accuracy': accuracy,
            'developer_view': developer_view,
            'predicted_by': predicted_by # Ensure this is always returned
        }

    def update_learning_state(self, actual_outcome, current_full_history):
        """
        อัปเดตสถานะการเรียนรู้ของ OracleEngine หลังจากทราบผลลัพธ์จริง
        ฟังก์ชันนี้จะใช้ self.last_prediction_context เพื่ออัปเดตสถิติ
        """
        if self.last_prediction_context:
            predicted = self.last_prediction_context['prediction']
            predicted_mode = self.last_prediction_context['prediction_mode']
            predicted_by = self.last_prediction_context['predicted_by']
            intuition_applied = self.last_prediction_context['intuition_applied']

            # Only update win/loss if the system made a valid prediction (not '⚠️' or '?')
            if predicted in ['P', 'B']:
                if actual_outcome != 'T': # ไม่นับ Tie ในการอัปเดตสถานะชนะ/แพ้
                    if predicted == actual_outcome:
                        # อัปเดตตามโหมดการทำนาย
                        if predicted_mode == 'ตาม':
                            self.tam_sutr_wins += 1
                        elif predicted_mode == 'สวน':
                            self.suan_sutr_wins += 1
                        
                        # อัปเดตตามวิธีการทำนาย
                        if "Pattern" in predicted_by:
                            self.pattern_analysis_wins += 1
                        elif "Momentum" in predicted_by:
                            self.momentum_wins += 1
                        elif "Intuition" in predicted_by:
                             self.intuition_wins += 1
                        # หากชนะ ก็รีเซ็ต last_prediction_context เพื่อเตรียมพร้อมสำหรับการทำนายถัดไป
                        self.last_prediction_context = None 
                    else:
                        # หากแพ้ ก็ยังคง last_prediction_context ไว้ เพื่อให้รู้ว่าแพ้ด้วยการทำนายครั้งล่าสุดนี้
                        pass # Losing streak handled in app.py

            # หลังจากอัปเดตสถานะการเรียนรู้แล้ว ให้รีเซ็ต last_prediction_context
            # เพื่อให้การทำนายครั้งต่อไปเป็น "ใหม่"
            self.last_prediction_context = None

        # (Optional) คุณอาจจะใช้ current_full_history เพื่อปรับโมเดลการเรียนรู้ที่นี่
        # เช่น Re-train model, Adjust weights for patterns, etc.
        # สำหรับเวอร์ชันจำลองนี้ เราจะยังไม่ทำอะไรซับซ้อน
