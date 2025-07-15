# oracle_core.py (Oracle v5.0)
from typing import List, Optional, Tuple, Literal

Outcome = Literal["P", "B", "T"]

class OracleBrain:
    def __init__(self):
        self.history: List[Outcome] = []
        self.last_prediction: Optional[Outcome] = None
        self.prediction_log: List[Optional[Outcome]] = []
        self.result_log: List[Outcome] = []

    def add_result(self, outcome: Outcome):
        self.history.append(outcome)
        self.result_log.append(outcome)
        self.prediction_log.append(self.last_prediction)

    def predict_next(self) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], int]:
        # Mock data (ตัวอย่างผลลัพธ์)
        return "P", "Sniper", 93, "PBPB", 2

    def predict(self):  # ✅ เพิ่ม method นี้ให้รองรับ app.py
        return self.predict_next()

    def remove_last(self):
        if self.history:
            self.history.pop()
        if self.result_log:
            self.result_log.pop()
        if self.prediction_log:
            self.prediction_log.pop()

    def reset(self):
        self.history.clear()
        self.result_log.clear()
        self.prediction_log.clear()
        self.last_prediction = None
