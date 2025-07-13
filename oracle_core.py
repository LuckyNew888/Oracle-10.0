from typing import List, Optional, Literal, Tuple

Outcome = Literal["P", "B", "T"]

# --- RuleEngine ---
class RuleEngine:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 3:
            return None
        if history[-1] == history[-2] == history[-3]:
            return history[-1]
        if history[-1] != history[-2] and history[-2] != history[-3]:
            return history[-1]
        return None

# --- PatternAnalyzer ---
class PatternAnalyzer:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last6 = "".join(history[-6:])
        patterns = {
            "PPBPP": "P", "BBPBB": "B",
            "PPBB": "P", "BBPP": "B",
            "PBPB": "P", "BPBP": "B",
            "BBBB": "B", "PPPP": "P"
        }
        for pattern, pred in patterns.items():
            if last6.endswith(pattern):
                return pred
        return None

# --- TrendScanner ---
class TrendScanner:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last_10 = history[-10:]
        if last_10.count("P") > 6:
            return "P"
        if last_10.count("B") > 6:
            return "B"
        return None

# --- TwoTwoPattern ---
class TwoTwoPattern:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 4:
            return None
        last4 = history[-4:]
        if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
            return last4[0]
        return None

# --- SniperPattern ---
class SniperPattern:
    def __init__(self):
        self.known_patterns = {
            "PBPB": "P", "BPBP": "B",
            "PPBB": "P", "BBPP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPBBB": "B", "BBBPBB": "P",
            "PPPP": "P", "BBBB": "B",
            "PBBP": "B", "BPPB": "P"
        }

    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 4:
            return None
        joined = "".join(history[-6:])
        for length in range(6, 3, -1):
            pattern = joined[-length:]
            if pattern in self.known_patterns:
                return self.known_patterns[pattern]
        return None

# --- ConfidenceScorer ---
class ConfidenceScorer:
    def score(self, predictions: dict, weights: dict, history: List[Outcome]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        total_score = {"P": 0.0, "B": 0.0}
        for name, pred in predictions.items():
            if pred in total_score:
                weight = weights.get(name, 0.5)
                total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None

        best = max(total_score, key=total_score.get)
        raw_conf = total_score[best] / sum(total_score.values())
        confidence = min(int(raw_conf * 100), 95)  # 🔒 ไม่เกิน 95%
        source_name = next((name for name, pred in predictions.items() if pred == best), None)
        pattern = self.extract_pattern(history)
        return best, source_name, confidence, pattern

    def extract_pattern(self, history: List[Outcome]) -> Optional[str]:
        if len(history) < 6:
            return None
        last6 = "".join(history[-6:])
        for pat in ["PBPB", "BPBP", "PPBB", "BBPP", "PPBPP", "BBPBB", "BBBB", "PPPP"]:
            if last6.endswith(pat):
                return pat
        return None

# --- OracleBrain ---
class OracleBrain:
    def __init__(self):
        self.history: List[Outcome] = []
        self.last_prediction: Optional[Outcome] = None
        self.prediction_log: List[Optional[Outcome]] = []
        self.result_log: List[Outcome] = []

        self.rule = RuleEngine()
        self.pattern = PatternAnalyzer()
        self.trend = TrendScanner()
        self.two_two = TwoTwoPattern()
        self.sniper = SniperPattern()
        self.scorer = ConfidenceScorer()
        self.show_initial_wait_message = True

    def add_result(self, outcome: Outcome):
        self.history.append(outcome)
        self.result_log.append(outcome)
        self.prediction_log.append(self.last_prediction)
        self.history = self.history[-100:]
        self.result_log = self.result_log[-100:]
        self.prediction_log = self.prediction_log[-100:]

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()

    def reset(self):
        self.history.clear()
        self.last_prediction = None
        self.prediction_log.clear()
        self.result_log.clear()
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

    def get_module_accuracy(self) -> dict:
        modules = {
            "Rule": self.rule,
            "Pattern": self.pattern,
            "Trend": self.trend,
            "2-2 Pattern": self.two_two,
            "Sniper": self.sniper
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
            accuracy[name] = (win / total * 100) if total else 0
        return accuracy

    def get_module_accuracy_normalized(self) -> dict:
        acc = self.get_module_accuracy()
        max_val = max(acc.values()) if acc else 1
        return {k: (v / max_val) for k, v in acc.items()}

    def get_best_recent_module(self, lookback: int = 10) -> Optional[str]:
        modules = {
            "Rule": self.rule,
            "Pattern": self.pattern,
            "Trend": self.trend,
            "2-2 Pattern": self.two_two,
            "Sniper": self.sniper
        }
        scores = {}
        for name, module in modules.items():
            wins, total = 0, 0
            for i in range(len(self.history) - lookback, len(self.history)):
                if i < 4: continue
                pred = module.predict(self.history[:i])
                if pred and pred == self.history[i]:
                    wins += 1
                if pred:
                    total += 1
            if total:
                scores[name] = wins / total
        return max(scores, key=scores.get) if scores else None

    def predict_next(self) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], int]:
        p_count = self.history.count("P")
        b_count = self.history.count("B")
        current_miss_streak = self.calculate_miss_streak()

        if (p_count + b_count) < 20 or current_miss_streak >= 6:
            self.last_prediction = None
            return None, None, None, None, current_miss_streak

        preds = {
            "Rule": self.rule.predict(self.history),
            "Pattern": self.pattern.predict(self.history),
            "Trend": self.trend.predict(self.history),
            "2-2 Pattern": self.two_two.predict(self.history),
            "Sniper": self.sniper.predict(self.history)
        }

        weights = self.get_module_accuracy_normalized()
        result, source, confidence, pattern_code = self.scorer.score(preds, weights, self.history)

        if current_miss_streak in [3, 4, 5]:
            best_module = self.get_best_recent_module()
            if best_module and preds.get(best_module):
                result = preds[best_module]
                source = f"{best_module}-Recovery"

        self.last_prediction = result
        return result, source, confidence, pattern_code, current_miss_streak
