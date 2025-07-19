from typing import Literal, List, Optional, Tuple, Dict

Outcome = Literal["P", "B", "T"]

class OracleBrain:
    def __init__(self):
        self.history: List[Outcome] = []
        self.ties: List[int] = []
        self.result_log: List[Outcome] = []
        self.prediction_log: List[Optional[Outcome]] = []
        self.last_prediction: Optional[Outcome] = None
        self.show_initial_wait_message = True

    def add_result(self, outcome: Outcome, tie_count: int = 0):
        if outcome == "T":
            if self.history:
                self.ties[-1] += 1
        else:
            self.history.append(outcome)
            self.ties.append(tie_count)
            self.result_log.append(outcome)
            self.prediction_log.append(self.last_prediction)

    def remove_last(self):
        if self.history:
            self.history.pop()
        if self.ties:
            self.ties.pop()
        if self.result_log:
            self.result_log.pop()
        if self.prediction_log:
            self.prediction_log.pop()

    def reset(self):
        self.history.clear()
        self.ties.clear()
        self.result_log.clear()
        self.prediction_log.clear()
        self.last_prediction = None
        self.show_initial_wait_message = True

    def calculate_miss_streak(self) -> int:
        streak = 0
        for pred, actual in zip(reversed(self.prediction_log), reversed(self.result_log)):
            if actual == "T" or pred is None:
                continue
            if pred != actual:
                streak += 1
            else:
                break
        return streak

    def get_module_accuracy(self) -> Dict[str, float]:
        modules = {
            "Rule": RuleEngine(),
            "Pattern": PatternAnalyzer(),
            "Trend": TrendScanner(),
            "2-2": TwoTwoPattern()
        }
        accuracy = {}
        for name, module in modules.items():
            win, total = 0, 0
            for i in range(4, len(self.history)):
                pred = module.predict(self.history[:i])
                if pred is not None:
                    total += 1
                    if pred == self.history[i]:
                        win += 1
            accuracy[name] = (win / total * 100) if total > 0 else 0
        return accuracy

    def predict_next(self) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        if len([x for x in self.history if x in ("P", "B")]) < 20:
            return None, None, None, None

        miss_streak = self.calculate_miss_streak()
        if miss_streak >= 6:
            return None, None, None, None

        rule = RuleEngine()
        pattern = PatternAnalyzer()
        trend = TrendScanner()
        two_two = TwoTwoPattern()
        scorer = ConfidenceScorer()

        predictions = {
            "Rule": rule.predict(self.history),
            "Pattern": pattern.predict(self.history),
            "Trend": trend.predict(self.history),
            "2-2": two_two.predict(self.history)
        }

        result, source, confidence, pattern_code = scorer.score(predictions, self.history)
        self.last_prediction = result
        return result, source, confidence, pattern_code

# --- Modules ---

class RuleEngine:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 3:
            return None
        if history[-1] == history[-2] == history[-3]:
            return history[-1]
        return None

class PatternAnalyzer:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last6 = "".join(history[-6:])
        patterns = {
            "PPBB": "P", "BBPP": "B",
            "PBPB": "P", "BPBP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPP": "P", "BBBB": "B"
        }
        for pat, pred in patterns.items():
            if last6.endswith(pat):
                return pred
        return None

class TrendScanner:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        recent = history[-10:]
        if recent.count("P") > 6:
            return "P"
        if recent.count("B") > 6:
            return "B"
        return None

class TwoTwoPattern:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 4:
            return None
        h = history[-4:]
        if h[0] == h[1] and h[2] == h[3] and h[0] != h[2]:
            return h[0]
        return None

class ConfidenceScorer:
    def score(self, predictions: dict, history: List[Outcome]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        tally = {"P": 0, "B": 0}
        for name, pred in predictions.items():
            if pred in tally:
                tally[pred] += 1
        if not any(tally.values()):
            return None, None, None, None
        best = max(tally, key=tally.get)
        source = next((k for k, v in predictions.items() if v == best), None)
        confidence = int((tally[best] / len(predictions)) * 100)
        pattern_code = PatternAnalyzer().predict(history)
        return best, source, confidence, pattern_code
