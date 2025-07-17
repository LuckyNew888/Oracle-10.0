# oracle_core.py (Oracle V8.0.3 - Adjusted Tie Predictor Lookback)
from typing import List, Optional, Literal, Tuple, Dict, Any
import random
from dataclasses import dataclass

# Define main outcomes
MainOutcome = Literal["P", "B", "T"]

# Define additional outcomes (side bets)
@dataclass
class RoundResult:
    main_outcome: MainOutcome
    is_any_natural: bool = False # True if Player or Banker gets a Natural 8/9

# --- Prediction Modules ---

# Helper function to get filtered history (P/B only) from new RoundResult history
def _get_main_outcome_history(history: List[RoundResult]) -> List[MainOutcome]:
    return [r.main_outcome for r in history if r.main_outcome in ("P", "B")]

# Helper function to get specific side bet history flags (True/False for occurrence)
def _get_side_bet_history_flags(history: List[RoundResult], bet_type: str) -> List[bool]:
    if bet_type == "T":
        return [r.main_outcome == "T" for r in history]
    return []


class RuleEngine:
    """
    Predicts based on simple repeating patterns (e.g., P P P -> P, B B B -> B)
    or alternating patterns (e.g., P B P -> P).
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 3:
            return None

        # Rule 1: Simple streak (P P P -> P, B B B -> B)
        if filtered_history[-1] == filtered_history[-2] == filtered_history[-3]:
            return filtered_history[-1]
        
        # Rule 2: Alternating pattern (P B P -> B, B P B -> P)
        if filtered_history[-1] != filtered_history[-2] and filtered_history[-2] != filtered_history[-3]:
            if filtered_history[-1] == filtered_history[-3]: # P B P, B P B
                return "P" if filtered_history[-1] == "B" else "B"
        
        # Rule: Two consecutive, then chop (P P B -> P, B B P -> B)
        if len(filtered_history) >= 3:
            if filtered_history[-1] != filtered_history[-2] and filtered_history[-2] == filtered_history[-3]:
                return filtered_history[-2] # Predict a return to the streak that was chopped

        return None

class PatternAnalyzer:
    """
    Predicts based on specific predefined patterns in the recent history.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None

        joined_filtered = "".join(filtered_history)
        
        patterns_and_predictions = {
            "PBPB": "P", "BPBP": "B",       
            "PPBB": "P", "BBPP": "B",       
            "PPPP": "P", "BBBB": "B",       
            "PPPPP": "P", "BBBBB": "B", 
            "PBPBP": "B", "BPBPB": "P",       
            "PBB": "P", "BPP": "B", 
            "PPBP": "P", "BBPA": "B", 
            "PBPP": "P", "BPPB": "B", 
            "PBBPP": "P", "BPBB": "B", 
            "PBPBPB": "P", "BPBPBP": "B", 
            "PPPBBB": "B", "BBBPBB": "P", 
            "PPBPP": "P", "BBPBB": "B", 
            "PBBP": "B", "BPPB": "P" 
        }

        for length in range(6, 2, -1): 
            if len(joined_filtered) >= length:
                current_pattern = joined_filtered[-length:]
                if current_pattern in patterns_and_predictions:
                    return patterns_and_predictions[current_pattern]
        return None

class TrendScanner:
    """
    Predicts based on the dominant outcome in the recent history.
    V8.0.0: Refined dynamic lookback for smoother scaling and improved trend detection.
    """
    def predict(self, history: List[RoundResult], choppiness_rate: float) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        # V8.0.0: More precise dynamic lookback based on choppiness
        # Scale lookback_len from 5 (very choppy) to 20 (very streaky)
        # choppiness_rate ranges from 0.0 (streaky) to 1.0 (choppy)
        # (1 - choppiness_rate) will range from 1.0 (streaky) to 0.0 (choppy)
        # lookback_len will range from 20 (streaky) down to 5 (choppy)
        lookback_len = int(5 + (1 - choppiness_rate) * 15) # Min 5, Max 20
        lookback_len = max(5, min(20, lookback_len)) # Ensure bounds

        if len(filtered_history) < lookback_len:
            return None
        
        recent_history = filtered_history[-lookback_len:]
        p_count = recent_history.count("P")
        b_count = recent_history.count("B")

        # Strong trend (e.g., 60% or more in recent history)
        if p_count / lookback_len >= 0.6:
            return "P"
        if b_count / lookback_len >= 0.6:
            return "B"
        
        # Consider a shorter, very strong recent trend (e.g., 4 out of last 5)
        if len(filtered_history) >= 5:
            last_5 = filtered_history[-5:]
            p_count_5 = last_5.count("P")
            b_count_5 = last_5.count("B")
            if p_count_5 >= 4:
                return "P"
            if b_count_5 >= 4:
                return "B"

        return None

class TwoTwoPattern:
    """
    Predicts based on a specific 2-2 alternating pattern (e.g., PPBB -> P).
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None
        
        last4 = filtered_history[-4:]
        if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
            return last4[0]
        return None

class SniperPattern:
    """
    A more aggressive pattern matching module, often looking for specific "sniper" setups.
    """
    def __init__(self):
        self.known_patterns = {
            "PBPB": "P", "BPBP": "B",
            "PPBB": "P", "BBPP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPBBB": "B", "BBBPBB": "P", 
            "PPPP": "P", "BBBB": "B",
            "PBBP": "B", "BPPB": "P",
            "PBBBP": "B", "BPBPP": "P", 
            "PBBBP": "B", "BPBPP": "P", 
            "PBPBPP": "P", "BPBPBB": "B", 
            "PPPPB": "B", "BBBB P": "P" 
        }

    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4: 
            return None
        
        joined = "".join(filtered_history)
        
        for length in range(6, 3, -1): 
            if len(joined) >= length:
                current_pattern = joined[-length:]
                if current_pattern in self.known_patterns:
                    return self.known_patterns[current_pattern]
        return None

class FallbackModule:
    """
    Provides a random prediction if no other module can make a prediction.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        return random.choice(["P", "B"])

class ChopDetector:
    """
    Specifically designed to detect "chop" patterns (long streak broken by opposite).
    When a chop is detected, it predicts the outcome that broke the streak.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        if len(filtered_history) >= 6: 
            last_6 = filtered_history[-6:]
            if last_6[0] == last_6[1] == last_6[2] == last_6[3] == last_6[4] and last_6[4] != last_6[5]:
                return last_6[5] 
        
        if len(filtered_history) >= 5: 
            last_5 = filtered_history[-5:]
            if last_5[0] == last_5[1] == last_5[2] == last_5[3] and last_5[3] != last_5[4]:
                return last_5[4] 

        if len(filtered_history) >= 3:
            if filtered_history[-3] == filtered_history[-2] and filtered_history[-2] != filtered_history[-1]:
                return filtered_history[-2] 

        return None


# --- ENHANCED PREDICTION MODULES FOR SIDE BETS (V8.0.0, V8.0.1, V8.0.2, V8.0.3) ---

class TiePredictor:
    """
    Predicts Tie outcomes with confidence.
    V8.0.0: Significantly enhanced logic for better accuracy and more proactive predictions.
    V8.0.1: Adjusted long_lookback_for_prob to be more realistic for a Baccarat shoe.
    V8.0.3: Further adjusted long_lookback_for_prob to 50 for faster responsiveness within a shoe.
    """
    THEORETICAL_PROB = 0.0952 # Approx. 9.52% for 8 decks

    def predict(self, history: List[RoundResult]) -> Tuple[Optional[Literal["T"]], Optional[int]]:
        tie_flags = _get_side_bet_history_flags(history, "T")
        main_history_pb = _get_main_outcome_history(history) 
        
        tie_confidence = 0

        if len(tie_flags) < 25: 
            return None, None
        
        # V8.0.3: Adjusted long_lookback_for_prob to 50 (from 70) for faster responsiveness
        long_lookback_for_prob = min(len(tie_flags), 50) # Look at last 50 rounds
        short_lookback_for_prob = min(len(tie_flags), 20) # Look at last 20 rounds

        actual_tie_count_long = tie_flags[-long_lookback_for_prob:].count(True)
        actual_tie_count_short = tie_flags[-short_lookback_for_prob:].count(True)

        expected_tie_count_long = long_lookback_for_prob * self.THEORETICAL_PROB
        expected_tie_count_short = short_lookback_for_prob * self.THEORETICAL_PROB

        # Rule 1: Ties are "due" based on long-term underperformance
        if actual_tie_count_long < expected_tie_count_long * 0.9: # Ties significantly underperformed long-term
            # Boost confidence based on how "due" they are
            due_factor = (expected_tie_count_long * 0.9 - actual_tie_count_long) / expected_tie_count_long
            tie_confidence = min(90, 60 + int(due_factor * 100 * 0.7)) # Base 60, significant boost
            if tie_confidence >= 55: return "T", tie_confidence

        # Rule 2: Ties are "due" based on short-term underperformance, even if long-term is okay
        if actual_tie_count_short < expected_tie_count_short * 0.8: # Ties significantly underperformed short-term
            due_factor_short = (expected_tie_count_short * 0.8 - actual_tie_count_short) / expected_tie_count_short
            tie_confidence = min(85, 55 + int(due_factor_short * 100 * 0.6)) # Base 55, moderate boost
            if tie_confidence >= 55: return "T", tie_confidence

        # Rule 3: Tie Clustering - if a tie occurred recently
        if len(tie_flags) >= 2 and tie_flags[-1] == True: # Last round was a Tie
            return "T", 70 # High confidence for immediate repeat
        if len(tie_flags) >= 3 and tie_flags[-2] == True and not tie_flags[-1]: # Tie 2 rounds ago, then no tie
            return "T", 60 # Moderate confidence for a tie after one non-tie
        if len(tie_flags) >= 4 and tie_flags[-3] == True and not tie_flags[-1] and not tie_flags[-2]: # Tie 3 rounds ago, then two non-ties
            return "T", 55 # Lower confidence, but still a pattern

        # Rule 4: Tie after a long streak of P/B (e.g., 10+ non-tie outcomes)
        if len(main_history_pb) >= 10 and not any(tie_flags[-10:]):
            return "T", 75 # High confidence if due after a long non-tie streak

        # Rule 5: Tie after specific alternating patterns in main outcomes (e.g., PBPBPB, then T)
        if len(main_history_pb) >= 6:
            recent_main = "".join(main_history_pb[-6:])
            if recent_main in ["PBPBPB", "BPBPBP"]: 
                return "T", 70
        
        # Rule 6: Tie after a long streak of one side winning (e.g., 6+ P's or 6+ B's)
        if len(main_history_pb) >= 6:
            if main_history_pb[-6:].count("P") == 6 or main_history_pb[-6:].count("B") == 6:
                return "T", 65

        # Rule 7: If ties have been slightly more frequent than expected, stop predicting (to prevent over-prediction)
        if actual_tie_count_long > expected_tie_count_long * 1.1: 
            return None, None 

        return None, None # No confident prediction

class AdaptiveScorer:
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy, with adaptive weighting.
    This scorer is primarily for main P/B outcomes.
    V8.0.0: Enhanced dynamic blending ratio for more accurate weighting.
    """
    def score(self, 
              predictions: Dict[str, Optional[MainOutcome]], 
              module_accuracies_all_time: Dict[str, float], # All-time accuracy for baseline
              module_accuracies_recent: Dict[str, float], # Recent accuracy for adaptive weighting (last 10)
              history: List[RoundResult]) -> Tuple[Optional[MainOutcome], Optional[str], Optional[int], Optional[str]]:
        
        total_score = {"P": 0.0, "B": 0.0}
        
        active_predictions = {name: pred for name, pred in predictions.items() if pred in ("P", "B")}

        if not active_predictions:
            return None, None, 0, None 

        for name, pred in active_predictions.items():
            all_time_acc_val = module_accuracies_all_time.get(name, 0.0)
            recent_acc_val = module_accuracies_recent.get(name, 0.0)

            # V8.0.0: More sophisticated dynamic blend ratio
            # The blend ratio for recent accuracy will depend on how much recent performance deviates from all-time.
            # If recent is much better, lean heavily on recent. If much worse, lean more on all-time.
            # If similar, use a balanced blend.
            
            # Normalize accuracies to a 0-1 scale for ratio calculation
            all_time_norm = all_time_acc_val / 100.0 if all_time_acc_val > 0 else 0.5
            recent_norm = recent_acc_val / 100.0 if recent_acc_val > 0 else 0.5

            # Calculate a dynamic blend_recent_ratio (e.g., from 0.5 to 0.9)
            # A higher difference (recent_norm - all_time_norm) means recent is performing better
            # Map difference from -0.5 to 0.5 (approx) to blend_recent_ratio from 0.5 to 0.9
            # Clamp difference to avoid extreme values
            diff = max(-0.2, min(0.2, recent_norm - all_time_norm)) # Clamp diff to -0.2 to 0.2
            
            # Linear mapping: if diff is -0.2, ratio is 0.5. If diff is 0.2, ratio is 0.9.
            blend_recent_ratio = 0.7 + (diff * 1.0) # Base 0.7, adjusted by diff (range 0.5 to 0.9)
            blend_recent_ratio = max(0.5, min(0.9, blend_recent_ratio)) # Ensure bounds

            weight = (recent_norm * blend_recent_ratio) + (all_time_norm * (1 - blend_recent_ratio))
            
            # Give ChopDetector a slightly higher base weight if it makes a prediction
            if name == "ChopDetector" and predictions.get(name) is not None:
                weight += 0.1 
            
            total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None 

        best_prediction_outcome = max(total_score, key=total_score.get)
        
        sum_of_scores = sum(total_score.values())
        raw_confidence = (total_score[best_prediction_outcome] / sum_of_scores) * 100
        
        # Confidence capped at 95% to avoid overconfidence
        confidence = min(int(raw_confidence), 95)
        
        source_modules = [name for name, pred in active_predictions.items() if pred == best_prediction_outcome]
        source_name = ", ".join(source_modules) if source_modules else "Combined"

        pattern = self._extract_relevant_pattern(history, predictions)
        
        return best_prediction_outcome, source_name, confidence, pattern

    def _extract_relevant_pattern(self, history: List[RoundResult], predictions: Dict[str, Optional[MainOutcome]]) -> Optional[str]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None
        
        joined_filtered = "".join(filtered_history)

        common_patterns = {
            "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
            "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
            "PPPP": "มังกร", "BBBB": "มังกร",
            "PPBPP": "ปิงปองยาว", "BBPBB": "ปิงปองยาว",
            "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
            "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
            "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว", 
            "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว", 
            "PBB": "สองตัวตัด", "BPP": "สองตัวตัด", 
            "PPBP": "สองตัวตัด", "BBPA": "สองตัวตัด",
            "PBPP": "คู่สลับ", "BPPB": "คู่สลับ",
            "PBBPP": "สองตัวตัด", "BPBB": "สองตัวติด", 
            "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว"
        }

        if len(filtered_history) >= 5:
            if filtered_history[-5] == filtered_history[-4] == filtered_history[-3] == filtered_history[-2] and filtered_history[-2] != filtered_history[-1]:
                return "มังกรตัด" 

        for length in range(6, 2, -1): 
            if len(joined_filtered) >= length:
                current_pattern_str = joined_filtered[-length:]
                if current_pattern_str in common_patterns:
                    return common_patterns[current_pattern_str]
        return None


class OracleBrain:
    def __init__(self):
        self.history: List[RoundResult] = [] 
        self.prediction_log: List[Optional[MainOutcome]] = [] 
        self.result_log: List[MainOutcome] = [] 
        self.last_prediction: Optional[MainOutcome] = None 
        self.last_module: Optional[str] = None 

        # V8.0.2: These logs are now *only* for the current shoe.
        # Accuracy calculations will be based on these, but they are reset per shoe.
        # The underlying "knowledge" of module performance is implicit in how AdaptiveScorer uses the accuracies.
        self.individual_module_prediction_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [] 
        }
        self.tie_module_prediction_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 


        # Initialize all prediction modules (P/B)
        self.rule_engine = RuleEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_scanner = TrendScanner()
        self.two_two_pattern = TwoTwoPattern()
        self.sniper_pattern = SniperPattern() 
        self.fallback_module = FallbackModule() 
        self.chop_detector = ChopDetector() 

        # Initialize side bet prediction modules
        self.tie_predictor = TiePredictor()

        self.scorer = AdaptiveScorer() 
        self.show_initial_wait_message = True 

    def add_result(self, main_outcome: MainOutcome, is_any_natural: bool = False):
        """
        Adds a new actual outcome to history and logs,
        and updates module accuracy based on the last prediction.
        """
        new_round_result = RoundResult(main_outcome, is_any_natural)
        
        # --- Record individual main P/B module predictions *before* adding the new outcome ---
        choppiness_rate_for_trend = self._calculate_choppiness_rate(self.history, 20)

        current_predictions_from_modules_main = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate_for_trend), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history),
            "ChopDetector": self.chop_detector.predict(self.history) 
        }
        
        for module_name, pred in current_predictions_from_modules_main.items():
            if pred is not None and pred in ("P", "B") and main_outcome in ("P", "B"):
                self.individual_module_prediction_log[module_name].append((pred, main_outcome))

        # --- Record individual side bet module predictions *before* adding the new outcome ---
        tie_pred_for_log, _ = self.tie_predictor.predict(self.history)

        if tie_pred_for_log is not None:
            self.tie_module_prediction_log.append((tie_pred_for_log, main_outcome == "T"))

        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.prediction_log.append(self.last_prediction) 
        self.result_log.append(main_outcome) 
        
        # V8.0.2: Trim logs to MAX_LENGTH (which is 100) to keep history relevant to the shoe.
        # This is important for preventing old shoe data from influencing current shoe analysis.
        self._trim_logs() 

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()
        
        # V8.0.2: When removing, also remove from module logs
        for module_name in self.individual_module_prediction_log:
            if self.individual_module_prediction_log[module_name]:
                self.individual_module_prediction_log[module_name].pop()
        
        if self.tie_module_prediction_log:
            self.tie_module_prediction_log.pop()


    def reset_all_data(self):
        """
        V8.0.2: This method now explicitly resets ALL data, including module accuracy logs.
        Use with caution, typically for a full system restart or debugging.
        """
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        
        # Clear all module prediction logs as well
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name].clear()
        self.tie_module_prediction_log.clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True

    def start_new_shoe(self):
        """
        V8.0.2: This method resets the current shoe's history and prediction logs,
        but retains the historical accuracy data of the modules.
        """
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        
        # Clear only the *current* shoe's prediction logs for modules
        # This allows accuracy calculation to restart for the new shoe
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name].clear()
        self.tie_module_prediction_log.clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True


    def _trim_logs(self, max_length=100):
        # V8.0.2: This trimming is now primarily to keep the history within a reasonable shoe length
        # and prevent excessive memory usage. The shoe reset handles clearing for new shoes.
        self.history = self.history[-max_length:]
        self.result_log = self.result_log[-max_length:]
        self.prediction_log = self.prediction_log[-max_length:]
        
        # Individual module logs are also trimmed to ensure they don't grow indefinitely
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name] = self.individual_module_prediction_log[module_name][-max_length:]
        
        self.tie_module_prediction_log = self.tie_module_prediction_log[-max_length:]


    def calculate_miss_streak(self) -> int:
        streak = 0
        for pred, actual in zip(reversed(self.prediction_log), reversed(self.result_log)):
            if pred is None or actual not in ("P", "B") or pred not in ("P", "B"):
                continue 
            
            if pred != actual:
                streak += 1
            else:
                break 
        return streak

    def _calculate_main_module_accuracy(self, module_name: str, lookback: Optional[int] = None) -> float:
        log = self.individual_module_prediction_log.get(module_name, [])
        
        relevant_preds = log
        if lookback is not None:
            relevant_preds = log[-lookback:]
        
        wins = 0
        total_predictions = 0
        
        for predicted_val, actual_val in relevant_preds:
            if predicted_val is not None and predicted_val in ("P", "B") and actual_val in ("P", "B"):
                total_predictions += 1
                if predicted_val == actual_val:
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0

    def _calculate_side_bet_module_accuracy(self, log: List[Tuple[Optional[Any], bool]], lookback: Optional[int] = None) -> float:
        relevant_log = log
        if lookback is not None:
            relevant_log = log[-lookback:]
        
        wins = 0
        total_predictions = 0
        
        for predicted_val, actual_flag in relevant_log:
            if predicted_val is not None: 
                total_predictions += 1
                if predicted_val == "T" and actual_flag: 
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0


    def get_module_accuracy_all_time(self) -> Dict[str, float]:
        # V8.0.2: All-time accuracy is now calculated from the full individual_module_prediction_log
        # which is only trimmed, not reset by start_new_shoe. This ensures accumulated knowledge.
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy(module_name, lookback=None)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback=None)

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        # V8.0.2: Recent accuracy is calculated from the individual_module_prediction_log,
        # which is cleared at the start of a new shoe. This means recent accuracy reflects the current shoe.
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy(module_name, lookback)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback)

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        all_known_modules_for_norm = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "Tie"] 
        
        if not acc:
            return {name: 0.5 for name in all_known_modules_for_norm}
        
        active_main_accuracies = {k: v for k, v in acc.items() if k in ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "ChopDetector"] and v > 0} 
        
        if not active_main_accuracies:
            return {name: 0.5 for name in all_known_modules_for_norm}
            
        max_val = max(active_main_accuracies.values()) 
        if max_val == 0: 
            max_val = 1 
            
        normalized_acc = {}
        for k, v in acc.items():
            if k in ["Fallback", "Tie"]: 
                normalized_acc[k] = (v / 100.0) if v > 0 else 0.5 
            else: 
                normalized_acc[k] = (v / max_val) if max_val > 0 else 0.5 
        return normalized_acc


    def get_best_recent_module(self, lookback: int = 10) -> Optional[str]:
        modules_to_check = {
            "Rule": self.rule_engine,
            "Pattern": self.pattern_analyzer,
            "Trend": self.trend_scanner, 
            "2-2 Pattern": self.two_two_pattern,
            "Sniper": self.sniper_pattern,
            "Fallback": self.fallback_module,
            "ChopDetector": self.chop_detector 
        }
        
        module_scores: Dict[str, float] = {}

        min_history_for_module = 4 
        start_index = max(min_history_for_module, len(self.history) - lookback) 
        
        for name, module in modules_to_check.items():
            wins = 0
            total_preds = 0
            for j in range(start_index, len(self.history)):
                current_sub_history = self.history[:j] 
                
                if name == "Trend":
                    choppiness_for_sub_history = self._calculate_choppiness_rate(current_sub_history, 20) 
                    module_pred = module.predict(current_sub_history, choppiness_for_sub_history)
                else:
                    module_pred = module.predict(current_sub_history)

                actual_outcome_for_this_round = self.history[j].main_outcome 
                
                if module_pred is not None and module_pred in ("P", "B") and actual_outcome_for_this_round in ("P", "B"): 
                    total_preds += 1
                    if module_pred == actual_outcome_for_this_round:
                        wins += 1
            
            if total_preds > 0:
                module_scores[name] = wins / total_preds
            else:
                module_scores[name] = 0.0 

        if not module_scores:
            return None
        
        filtered_module_scores = {k: v for k, v in module_scores.items() if k != "Fallback"}
        
        if not filtered_module_scores:
            return None

        return max(filtered_module_scores, key=filtered_module_scores.get)

    def _calculate_choppiness_rate(self, history: List[RoundResult], lookback: int) -> float:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 2:
            return 0.0 

        recent_history = filtered_history[-lookback:]
        alternations = 0
        for i in range(1, len(recent_history)):
            if recent_history[i] != recent_history[i-1]:
                alternations += 1
        
        if len(recent_history) <= 1: 
            return 0.0
        
        return alternations / (len(recent_history) - 1)


    def predict_next(self) -> Tuple[
        Optional[MainOutcome], Optional[str], Optional[int], Optional[str], int, bool, 
        Optional[Literal["T"]], Optional[int], 
        bool 
    ]:
        """
        Generates the next predictions for main outcome and side bets,
        along with main outcome's source, confidence, miss streak, and Sniper opportunity flag.
        """
        main_history_filtered_for_pb = _get_main_outcome_history(self.history)
        p_count = main_history_filtered_for_pb.count("P")
        b_count = main_history_filtered_for_pb.count("B")
        
        current_miss_streak = self.calculate_miss_streak()

        MIN_HISTORY_FOR_PREDICTION = 20 
        
        MIN_HISTORY_FOR_SNIPER = 25 
        MIN_HISTORY_FOR_SIDE_BET_SNIPER = 25 
        MIN_DISPLAY_CONFIDENCE = 50 
        MIN_DISPLAY_CONFIDENCE_SIDE_BET = 55 

        final_prediction_main = None
        source_module_name_main = None
        confidence_main = None
        pattern_code_main = None
        is_sniper_opportunity_main = False 
        
        tie_prediction = None
        tie_confidence = None

        is_tie_sniper_opportunity = False

        if (p_count + b_count) < MIN_HISTORY_FOR_PREDICTION or current_miss_streak >= 6:
            self.last_prediction = None
            self.last_module = None
            return None, None, None, None, current_miss_streak, False, None, None, False 

        choppiness_rate = self._calculate_choppiness_rate(self.history, 20) 

        predictions_from_modules = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history),
            "ChopDetector": self.chop_detector.predict(self.history) 
        }
        
        module_accuracies_all_time = self.get_module_accuracy_all_time()
        module_accuracies_recent_10 = self.get_module_accuracy_recent(10) 
        module_accuracies_recent_20 = self.get_module_accuracy_recent(20) 

        final_prediction_main, source_module_name_main, confidence_main, pattern_code_main = \
            self.scorer.score(predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history) 

        if final_prediction_main is not None and confidence_main is not None and confidence_main < MIN_DISPLAY_CONFIDENCE:
            final_prediction_main = None
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None

        if current_miss_streak in [3, 4, 5]: 
            best_module_for_recovery = self.get_best_recent_module()
            if best_module_for_recovery and predictions_from_modules.get(best_module_for_recovery) in ("P", "B"):
                final_prediction_main = predictions_from_modules[best_module_for_recovery] 
                source_module_name_main = f"{best_module_for_recovery}-Recovery"
                confidence_main = 70 


        # --- Main Outcome Sniper Opportunity Logic ---
        if final_prediction_main in ("P", "B") and confidence_main is not None:
            if confidence_main >= 50 and current_miss_streak <= 3 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER:
                contributing_modules = [m.strip() for m in source_module_name_main.split(',')]
                
                relevant_contributing_modules = [m for m in contributing_modules if m not in ["Fallback", "NoPrediction"]]

                high_accuracy_contributing_count = 0
                
                CONTRIBUTING_MODULE_RECENT_ACCURACY_THRESHOLD = 50 

                for module_name in relevant_contributing_modules:
                    acc_10 = module_accuracies_recent_10.get(module_name, 0.0)
                    acc_20 = module_accuracies_recent_20.get(module_name, 0.0)
                    
                    effective_recent_acc = max(acc_10, acc_20)

                    if effective_recent_acc >= CONTRIBUTING_MODULE_RECENT_ACCURACY_THRESHOLD:
                        high_accuracy_contributing_count += 1
                
                if high_accuracy_contributing_count >= 3:
                    is_sniper_opportunity_main = True
        # --- END Main Outcome Sniper Logic ---

        self.last_prediction = final_prediction_main
        self.last_module = source_module_name_main 

        # --- Side Bet Predictions with Confidence ---
        tie_pred_raw, tie_conf_raw = self.tie_predictor.predict(self.history)

        # V8.0.0: Refined cooldown logic for Tie prediction.
        # Instead of full suppression, reduce confidence for a few rounds after a miss.
        if self.tie_module_prediction_log:
            last_logged_tie_pred, last_actual_is_tie = self.tie_module_prediction_log[-1]
            if last_logged_tie_pred == "T" and not last_actual_is_tie:
                # If last tie prediction was wrong, reduce current tie confidence
                if tie_conf_raw is not None:
                    tie_conf_raw = max(0, tie_conf_raw - 20) 
        
        if tie_pred_raw is not None and tie_conf_raw is not None and tie_conf_raw >= MIN_DISPLAY_CONFIDENCE_SIDE_BET:
            tie_prediction = tie_pred_raw
            tie_confidence = tie_conf_raw
        else:
            tie_prediction = None
            tie_confidence = None

        # --- Side Bet Sniper Opportunity Logic ---
        SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD = 60 
        SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT = 3 

        # Tie Sniper
        if tie_prediction == "T" and tie_confidence is not None:
            if tie_confidence >= 50 and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER: 
                if len(self.tie_module_prediction_log) >= SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT:
                    tie_recent_acc = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
                else:
                    tie_recent_acc = 0 
                
                if tie_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                    is_tie_sniper_opportunity = True

        return (
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_miss_streak, is_sniper_opportunity_main,
            tie_prediction, tie_confidence, 
            is_tie_sniper_opportunity 
        )

