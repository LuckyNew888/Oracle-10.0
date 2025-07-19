class OracleBrain:
    def __init__(self):
        self.history = []
        self.ties = []  # ← ใช้เก็บผลเสมอ
        self.prediction_log = []
        self.result_log = []
        ...

    def add_result(self, outcome: Outcome, tie_count: int = 0):
        self.history.append(outcome)
        self.ties.append(tie_count)
        self.result_log.append(outcome)
        self.prediction_log.append(self.last_prediction)
        self.trim_logs()

    def reset(self):
        self.history.clear()
        self.ties.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        ...
