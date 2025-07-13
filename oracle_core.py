# oracle_core.py v4.1

from typing import List, Optional, Literal, Tuple

Outcome = Literal["P", "B", "T"]

# --- Modules ---
class RuleEngine:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 3:
            return None
        if history[-1] == history[-2] == history[-3]:
            return history[-1]
        if history[-1] != history[-2] and history[-2] != history[-3]:
            return history[-1]
        return None

class PatternAnalyzer:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last6 = "".join(history[-6:])
        patterns = {
            "PPBPP": "P", "BBPBB": "B",
            "PPBB": "P", "BBPP": "B",
            "PBPB": "P", "BPBP": "B",
            "BBBB": "B", "PPPP": "P",
            "PBBP": "B", "BPPB": "P"
        }
        for pattern, pred in patterns.items():
            if last6.endswith(pattern):
                return pred
        return None

class TrendScanner:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        last_10 = history[-10:]
        if last_10.count("P") > 6:
            return "P"
        if last_10.count("B") > 6:
            return "B"
        return None

class TwoTwoPattern:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 4:
            return None
        last4 = history[-4:]
        if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
            return last4[0]
        return None

class SniperPattern:
    def __init__(self):
        self.known_patterns = {
            "PBPB": "P", "BPBP": "B",
            "PPBB": "P", "BBPP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPBBB": "B", "BBBPBB": "P",
            "PPPP": "P", "BBBB": "B",
            "PBBP": "B", "BPPB": "P",
            "BPBPBP": "B", "PBPBPB": "P"
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

class SmartPredictor:
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        if len(history) < 5:
            return None
        last5 = "".join(history[-5:])
        if last5.count("P") > 3:
            return "P"
        if last5.count("B") > 3:
            return "B"
        if history[-1] != history[-2]:
            return history[-1]
        return None

# --- Scorer ---
class ConfidenceScorer:
    def score(self, predictions: dict, weights: dict, history: List[Outcome], cap: int = 95) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        total_score = {"P": 0.0, "B": 0.0}
        for name, pred in predictions.items():
            if pred in total_score:
                weight = weights.get(name, 0.5)
                total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None

        best = max(total_score, key=total_score.get)
        confidence = int((total_score[best] / sum(total_score.values())) * 100)
        confidence = min(confidence, cap)
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

        self.modules = {
            "Rule": RuleEngine(),
            "Pattern": PatternAnalyzer(),
            "Trend": TrendScanner(),
            "2-2 Pattern": TwoTwoPattern(),
            "Sniper": SniperPattern(),
            "Smart": SmartPredictor()
        }
        self.scorer = ConfidenceScorer()
        self.show_initial_wait_message = True

    def add_result(self, outcome: Outcome):
        self.history.append(outcome)
        self.result_log.append(outcome)
        self.prediction_log.append(self.last_prediction)
        if len(self.history) > 200:
            self.history.pop(0)
        if len(self.result_log) > 200:
            self.result_log.pop(0)
        if len(self.prediction_log) > 200:
            self.prediction_log.pop(0)

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
        accuracy = {}
        for name, module in self.modules.items():
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
        scores = {}
        for name, module in self.modules.items():
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

        preds = {name: mod.predict(self.history) for name, mod in self.modules.items() if name != "Smart"}
        weights = self.get_module_accuracy_normalized()

        result, source, confidence, pattern_code = self.scorer.score(preds, weights, self.history)

        # Recovery Chain
        if current_miss_streak in [3, 4, 5]:
            best_module = self.get_best_recent_module()
            if best_module and self.modules[best_module].predict(self.history):
                result = self.modules[best_module].predict(self.history)
                source = f"{best_module}-Recovery"

        if current_miss_streak >= 5:
            # Activate SmartPredictor override
            smart = self.modules["Smart"].predict(self.history)
            if smart:
                result = smart
                source = "SmartOverride"
                confidence = min(confidence or 90, 93)

        self.last_prediction = result
        return result, source, confidence, pattern_code, current_miss_streak
