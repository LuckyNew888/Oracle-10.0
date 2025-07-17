# oracle_core.py (Oracle V7.9.4 - Fix Module Accuracy)
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
    # Removed 'NATURAL' type as PockPredictor is removed
    return []


class RuleEngine:
    """
    Predicts based on simple repeating patterns (e.g., P P P -> P, B B B -> B)
    or alternating patterns (e.g., P B P -> P).
    V6.1: Added more basic rule patterns.
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
        
        # V6.1 New Rule: Two consecutive, then chop (P P B -> P, B B P -> B)
        if len(filtered_history) >= 3:
            if filtered_history[-1] != filtered_history[-2] and filtered_history[-2] == filtered_history[-3]:
                return filtered_history[-2] # Predict a return to the streak that was chopped

        return None

class PatternAnalyzer:
    """
    Predicts based on specific predefined patterns in the recent history.
    V6.1: Expanded the dictionary of known patterns for better coverage.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None

        joined_filtered = "".join(filtered_history)
        
        # V6.1: Expanded patterns
        patterns_and_predictions = {
            # Basic Repeating/Alternating
            "PBPB": "P", "BPBP": "B",       
            "PPBB": "P", "BBPP": "B",       
            "PPPP": "P", "BBBB": "B",       
            
            # Longer Streaks/Chops
            "PPPPP": "P", "BBBBB": "B", # 5 in a row
            "PBPBP": "B", "BPBPB": "P", # Longer alternating
            
            # Specific Combinations
            "PBB": "P", "BPP": "B", # Two of one, then one of other, predict first
            "PPBP": "P", "BBPA": "B", # Two, chop, one, predict first
            "PBPP": "P", "BPPB": "B", # Chop, two, chop, predict first
            "PBBPP": "P", "BPBB": "B", # Two, two, then chop, predict first
            "PBPBPB": "P", "BPBPBP": "B", # Longer alternating, predict next
            "PPPBBB": "B", "BBBPBB": "P", # Three of one, three of other, predict chop
            "PPBPP": "P", "BBPBB": "B", # Two, chop, two, predict first
            "PBBP": "B", "BPPB": "P" # Specific chop pattern
        }

        # Iterate from longest to shortest pattern for matching
        for length in range(6, 2, -1): # Check patterns from length 6 down to 3
            if len(joined_filtered) >= length:
                current_pattern = joined_filtered[-length:]
                if current_pattern in patterns_and_predictions:
                    return patterns_and_predictions[current_pattern]
        return None

class TrendScanner:
    """
    Predicts based on the dominant outcome in the recent history.
    V6.1: Made trend detection slightly more sensitive and added a "minority trend" consideration.
    V6.6: Implemented dynamic lookback based on choppiness.
    """
    def predict(self, history: List[RoundResult], choppiness_rate: float) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        # V6.6: Dynamic lookback based on choppiness
        if choppiness_rate > 0.6: # High choppiness, focus on very recent
            lookback_len = 5
        elif choppiness_rate < 0.3: # Low choppiness (streaky), use a longer lookback
            lookback_len = 15
        else: # Moderate choppiness
            lookback_len = 10

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
        
        # V6.1 New: Consider a shorter, very strong recent trend (e.g., 4 out of last 5)
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
    V6.1: No significant changes, already robust.
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
    V6.1: Expanded known patterns for sniper opportunities.
    """
    def __init__(self):
        self.known_patterns = {
            "PBPB": "P", "BPBP": "B",
            "PPBB": "P", "BBPP": "B",
            "PPBPP": "P", "BBPBB": "B",
            "PPPBBB": "B", "BBBPBB": "P", 
            "PPPP": "P", "BBBB": "B",
            "PBBP": "B", "BPPB": "P",
            # V6.1 Added more sniper patterns
            "PBBBP": "B", "BPBPP": "P", # Specific reversal points
            "PBBBP": "B", "BPBPP": "P", 
            "PBPBPP": "P", "BPBPBB": "B", # Alternating then streak
            "PPPPB": "B", "BBBB P": "P" # End of long streak
        }

    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4: 
            return None
        
        joined = "".join(filtered_history)
        
        for length in range(6, 3, -1): # Check patterns from length 6 down to 4
            if len(joined) >= length:
                current_pattern = joined[-length:]
                if current_pattern in self.known_patterns:
                    return self.known_patterns[current_pattern]
        return None

class FallbackModule:
    """
    Provides a random prediction if no other module can make a prediction.
    V6.1: No change, its purpose is to always provide an answer.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        # This module should always return a prediction unless history is empty, which is handled
        # by MIN_HISTORY_FOR_PREDICTION in OracleBrain.predict_next
        return random.choice(["P", "B"])

class ChopDetector:
    """
    V6.3: Specifically designed to detect "chop" patterns (long streak broken by opposite).
    When a chop is detected, it predicts the outcome that broke the streak.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        # Look for a streak of at least 4-5, followed by a single opposite outcome
        # Example: BBBBB P (predict P), PPPPP B (predict B)
        if len(filtered_history) >= 6: # Need at least 5 for streak + 1 for chop
            last_6 = filtered_history[-6:]
            # Check for 5 of one, then 1 of other
            if last_6[0] == last_6[1] == last_6[2] == last_6[3] == last_6[4] and last_6[4] != last_6[5]:
                return last_6[5] # Predict the outcome that broke the streak
        
        if len(filtered_history) >= 5: # Look for 4 of one, then 1 of other
            last_5 = filtered_history[-5:]
            if last_5[0] == last_5[1] == last_5[2] == last_5[3] and last_5[3] != last_5[4]:
                return last_5[4] # Predict the outcome that broke the streak

        # V6.3: Also detect shorter, immediate chops after a pair
        # Example: PP B (predict P), BB P (predict B) - this might be handled by RuleEngine, but reinforce
        if len(filtered_history) >= 3:
            if filtered_history[-3] == filtered_history[-2] and filtered_history[-2] != filtered_history[-1]:
                # If the last two were the same, and then it chopped, predict the original streak to continue
                # This is a common "chop" scenario where the streak tries to re-establish
                return filtered_history[-2] # Predict P for PPB, B for BBP

        return None


# --- ENHANCED PREDICTION MODULES FOR SIDE BETS (V7.5, V7.6, V7.8, V7.9, V7.9.1, V7.9.2, V7.9.3, V7.9.4) ---

class TiePredictor:
    """
    Predicts Tie outcomes with confidence.
    V7.3: Returns confidence score. Logic adjusted for balance.
    V7.4: Fixed NameError.
    V7.5: Enhanced confidence and filtering for more accurate predictions.
    V7.6: Further refined probability and pattern based logic for Tie.
    V7.8: Adjusted confidence thresholds for easier Sniper trigger.
    V7.9: Added more aggressive filtering to prevent continuous incorrect predictions.
    V7.9.1: Refined probability thresholds for Tie prediction to improve accuracy and reduce over-prediction.
    """
    THEORETICAL_PROB = 0.0952 # Approx. 9.52% for 8 decks

    def predict(self, history: List[RoundResult]) -> Tuple[Optional[Literal["T"]], Optional[int]]:
        tie_flags = _get_side_bet_history_flags(history, "T")
        main_history_pb = _get_main_outcome_history(history) 
        
        tie_confidence = 0

        # V7.5: Increased history requirement for Tie prediction for more reliable probability calculation
        if len(tie_flags) < 25: 
            return None, None
        
        lookback_for_prob = min(len(tie_flags), 50) 
        actual_tie_count = recent_tie_flags.count(True) if (recent_tie_flags := tie_flags[-lookback_for_prob:]) else 0
        expected_tie_count = lookback_for_prob * self.THEORETICAL_PROB

        # V7.9.1: More precise probability-based prediction thresholds
        if actual_tie_count < expected_tie_count * 0.9: # Ties are significantly "due"
            # Confidence calculation: Base 65, boost if very due. Max 90.
            tie_confidence = min(90, 65 + int((expected_tie_count * 0.9 - actual_tie_count) / expected_tie_count * 100)) 
            if tie_confidence >= 60: # Only predict if confidence meets minimum display threshold
                return "T", tie_confidence
            else:
                return None, None
        # V7.9.1: If ties have been slightly more frequent than expected, stop predicting.
        elif actual_tie_count > expected_tie_count * 1.0: 
            return None, None 

        # Pattern-based rules (these will now be filtered by the probability check above and confidence threshold)
        # Rule 1: Tie after a long streak of P/B (e.g., 12+ non-tie outcomes)
        if len(main_history_pb) >= 12 and not any(tie_flags[-12:]):
            return "T", 70 # High confidence if due after a long non-tie streak
        
        # Rule 2: If tie occurred recently and then a few non-ties, it might repeat (T _ _ _ T)
        if len(tie_flags) >= 5 and tie_flags[-5] and not any(tie_flags[-4:]):
            return "T", 65
            
        # Rule 3: Tie after specific alternating patterns in main outcomes (e.g., PBPBPB, then T)
        if len(main_history_pb) >= 6:
            recent_main = "".join(main_history_pb[-6:])
            if recent_main in ["PBPBPB", "BPBPBP"]: 
                return "T", 75
        
        # V7.9.1: Adjusted threshold for frequent ties to be more conservative
        # Rule 4: If ties are very frequent in recent history (e.g., 6+ in last 20) - this might be caught by prob check
        if tie_flags[-20:].count(True) >= 6 and actual_tie_count < expected_tie_count * 0.95: 
            return "T", 60
            
        # Rule 5: Tie after a specific main outcome sequence (e.g., P B B P, then T)
        if len(main_history_pb) >= 5:
            recent_main_5 = "".join(main_history_pb[-5:])
            if recent_main_5 == "PBBPB" or recent_main_5 == "BPPBP": 
                return "T", 60

        # Rule 6: Tie after a long streak of one side winning (e.g., 7+ P's or 7+ B's)
        if len(main_history_pb) >= 7:
            if main_history_pb[-7:].count("P") == 7 or main_history_pb[-7:].count("B") == 7:
                return "T", 70
        
        # Rule 7: Tie after a specific "chop" pattern (e.g., P B P B, then P P -> T)
        if len(main_history_pb) >= 6:
            recent_main_6 = "".join(main_history_pb[-6:])
            if recent_main_6 == "PBPBPP" or recent_main_6 == "BPBPBB":
                return "T", 65
        
        # Rule 8: Tie after a very short streak (e.g., PP or BB) followed by a chop
        if len(main_history_pb) >= 3:
            if main_history_pb[-3:] == ["P", "P", "B"] or main_history_pb[-3:] == ["B", "B", "P"]:
                if not any(tie_flags[-5:]): 
                    return "T", 60

        return None, None # No confident prediction

# Removed PockPredictor class entirely

class AdaptiveScorer:
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy, with adaptive weighting.
    This scorer is primarily for main P/B outcomes.
    V6.1: Adjusted blending ratio for more responsiveness to recent accuracy.
    V6.3: Give ChopDetector a slightly higher base weight.
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

            # Use 50% (0.5 weight) if accuracy is 0.0 or module hasn't made enough predictions yet
            all_time_weight = (all_time_acc_val if all_time_acc_val > 0.0 else 50.0) / 100.0
            recent_weight = (recent_acc_val if recent_acc_val > 0.0 else 50.0) / 100.0
            
            # V6.1: Adjusted blend ratio - more emphasis on recent performance (80% recent, 20% all-time)
            weight = (recent_weight * 0.8) + (all_time_weight * 0.2)
            
            # V6.3: Give ChopDetector a slightly higher base weight if it makes a prediction
            if name == "ChopDetector" and predictions.get(name) is not None:
                weight += 0.1 # Add a small bonus weight (can be tuned)
            
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
            # V7.9.3: Fixed NameError: 'filtered_filtered' -> 'filtered_history'
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

        self.individual_module_prediction_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [] 
        }
        self.tie_module_prediction_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 
        # Removed self.pock_module_prediction_log


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
        # Removed self.pock_predictor = PockPredictor()

        self.scorer = AdaptiveScorer() 
        self.show_initial_wait_message = True 

    def add_result(self, main_outcome: MainOutcome, is_any_natural: bool = False):
        """
        Adds a new actual outcome to history and logs,
        and updates module accuracy based on the last prediction.
        """
        new_round_result = RoundResult(main_outcome, is_any_natural)
        
        # --- Record individual main P/B module predictions *before* adding the new outcome ---
        # V6.6: Calculate choppiness rate for the current history (before adding new result)
        choppiness_rate_for_trend = self._calculate_choppiness_rate(self.history, 20)

        current_predictions_from_modules_main = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate_for_trend), # Pass choppiness rate
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history),
            "ChopDetector": self.chop_detector.predict(self.history) 
        }
        
        for module_name, pred in current_predictions_from_modules_main.items():
            if pred in ("P", "B") and main_outcome in ("P", "B"):
                self.individual_module_prediction_log[module_name].append((pred, main_outcome))

        # --- Record individual side bet module predictions *before* adding the new outcome ---
        # Note: We only log the prediction itself, not the confidence, for accuracy tracking
        tie_pred_for_log, _ = self.tie_predictor.predict(self.history)
        # Removed pock_pred_for_log, _ = self.pock_predictor.predict(self.history) 

        self.tie_module_prediction_log.append((tie_pred_for_log, main_outcome == "T"))
        # Removed self.pock_module_prediction_log.append((pock_pred_for_log, is_any_natural)) 

        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.prediction_log.append(self.last_prediction) 
        self.result_log.append(main_outcome) 
        
        self._trim_logs() 

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()
        
        for module_name in self.individual_module_prediction_log:
            if self.individual_module_prediction_log[module_name]:
                self.individual_module_prediction_log[module_name].pop()
        
        self.tie_module_prediction_log.pop() if self.tie_module_prediction_log else None
        # Removed self.pock_module_prediction_log.pop() if self.pock_module_prediction_log else None 


    def reset(self):
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name].clear()
        
        self.tie_module_prediction_log.clear()
        # Removed self.pock_module_prediction_log.clear() 

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True

    def _trim_logs(self, max_length=100):
        self.history = self.history[-max_length:]
        self.result_log = self.result_log[-max_length:]
        self.prediction_log = self.prediction_log[-max_length:]
        
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name] = self.individual_module_prediction_log[module_name][-max_length:]
        
        self.tie_module_prediction_log = self.tie_module_prediction_log[-max_length:]
        # Removed self.pock_module_prediction_log = self.pock_module_prediction_log[-max_length:] 


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
            if predicted_val in ("P", "B") and actual_val in ("P", "B"):
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
            if predicted_val is not None: # Only count if a prediction was made
                total_predictions += 1
                if predicted_val == "T" and actual_flag: # Predicted Tie, and actual was Tie
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0


    def get_module_accuracy_all_time(self) -> Dict[str, float]:
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy(module_name, lookback=None)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback=None)
        # Removed accuracy_results["Pock"] = self._calculate_side_bet_module_accuracy(self.pock_module_prediction_log, lookback=None) 

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy(module_name, lookback)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback)
        # Removed accuracy_results["Pock"] = self._calculate_side_bet_module_accuracy(self.pock_module_prediction_log, lookback) 

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        all_known_modules_for_norm = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "Tie"] # Removed "Pock"
        
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
            if k in ["Fallback", "Tie"]: # Removed "Pock"
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
                
                # V6.6: Special handling for TrendScanner when calculating its historical performance
                if name == "Trend":
                    # Calculate choppiness for the sub-history
                    choppiness_for_sub_history = self._calculate_choppiness_rate(current_sub_history, 20) 
                    module_pred = module.predict(current_sub_history, choppiness_for_sub_history)
                else:
                    module_pred = module.predict(current_sub_history)

                actual_outcome_for_this_round = self.history[j].main_outcome 
                
                if module_pred in ("P", "B") and actual_outcome_for_this_round in ("P", "B"): 
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
        Optional[MainOutcome], Optional[str], Optional[int], Optional[str], int, bool, # Main prediction
        Optional[Literal["T"]], Optional[int], # Tie prediction and its confidence
        bool # is_tie_sniper_opportunity (Removed is_pock_sniper_opportunity)
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
        MIN_HISTORY_FOR_SNIPER = 30 
        MIN_HISTORY_FOR_SIDE_BET_SNIPER = 30 
        MIN_DISPLAY_CONFIDENCE = 55 
        MIN_DISPLAY_CONFIDENCE_SIDE_BET = 60 

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
            # Adjusted return tuple
            return None, None, None, None, current_miss_streak, False, None, None, False 

        # V6.6: Calculate choppiness rate once for TrendScanner
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

        final_prediction_main, source_module_name_main, confidence_main, pattern_code_main = \
            self.scorer.score(predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history) 

        # V6.2: Apply minimum display confidence for main prediction
        if final_prediction_main is not None and confidence_main is not None and confidence_main < MIN_DISPLAY_CONFIDENCE:
            final_prediction_main = None
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None

        if current_miss_streak in [3, 4]:
            best_module_for_recovery = self.get_best_recent_module()
            if best_module_for_recovery and predictions_from_modules.get(best_module_for_recovery) in ("P", "B"):
                # V7.9.2: Fixed NameError: 'predictions' was undefined. Changed to 'predictions_from_modules'.
                final_prediction_main = predictions_from_modules[best_module_for_recovery] 
                source_module_name_main = f"{best_module_for_recovery}-Recovery"
                confidence_main = 70 


        # --- Main Outcome Sniper Opportunity Logic ---
        if final_prediction_main in ("P", "B") and confidence_main is not None:
            # V7.8: Changed miss streak condition from == 0 to <= 2
            if confidence_main == 95 and current_miss_streak <= 2 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER:
                contributing_modules = [m.strip() for m in source_module_name_main.split(',')]
                all_contributing_modules_high_all_time_accuracy = True
                
                # V7.8: Changed threshold from 90 to 80
                SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD = 80 

                if not contributing_modules or "NoPrediction" in contributing_modules or "Fallback" in contributing_modules:
                    all_contributing_modules_high_all_time_accuracy = False
                else:
                    for module_name in contributing_modules:
                        mod_acc = self._calculate_main_module_accuracy(module_name, lookback=None) 
                        if mod_acc < SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD:
                            all_contributing_modules_high_all_time_accuracy = False
                            break
                
                sniper_module_recent_accuracy_ok = True
                if "Sniper" in contributing_modules:
                    SNIPER_RECENT_PREDICTION_COUNT = 5 
                    # V7.8: Changed threshold from 90 to 80
                    SNIPER_RECENT_ACCURACY_THRESHOLD = 80 

                    sniper_recent_acc = self._calculate_main_module_accuracy("Sniper", SNIPER_RECENT_PREDICTION_COUNT) 
                    
                    if sniper_recent_acc < SNIPER_RECENT_ACCURACY_THRESHOLD:
                        sniper_module_recent_accuracy_ok = False
                
                if all_contributing_modules_high_all_time_accuracy and sniper_module_recent_accuracy_ok:
                    is_sniper_opportunity_main = True
        # --- END Main Outcome Sniper Logic ---

        self.last_prediction = final_prediction_main
        self.last_module = source_module_name_main 

        # --- Side Bet Predictions with Confidence ---
        tie_pred_raw, tie_conf_raw = self.tie_predictor.predict(self.history)

        # V7.9: Implement cool-down for Tie prediction if the last one was incorrect.
        # Check the very last entry in tie_module_prediction_log (if it exists)
        # This log entry is added *before* the current round's prediction is made, but *before* predict_next is called for the *next* round.
        # So, to check the *previous* round's tie prediction accuracy, we look at the last entry.
        # IMPORTANT: The tie_module_prediction_log stores (predicted_value, actual_is_tie_flag)
        if self.tie_module_prediction_log:
            # Get the last recorded prediction and actual result for Tie
            last_logged_tie_pred, last_actual_is_tie = self.tie_module_prediction_log[-1]
            
            # If the system *predicted* Tie in the last round (last_logged_tie_pred == "T")
            # AND the *actual* result of the last round was NOT a Tie (not last_actual_is_tie)
            # Then, suppress the current Tie prediction for this round
            if last_logged_tie_pred == "T" and not last_actual_is_tie:
                tie_prediction = None
                tie_confidence = None
            else:
                # If the last Tie prediction was correct, or there was no Tie prediction, or it was not a Tie,
                # then proceed with the current round's Tie prediction logic.
                if tie_pred_raw is not None and tie_conf_raw is not None and tie_conf_raw >= MIN_DISPLAY_CONFIDENCE_SIDE_BET:
                    tie_prediction = tie_pred_raw
                    tie_confidence = tie_conf_raw
        else: # No history yet for tie predictions, so just apply the normal threshold
            if tie_pred_raw is not None and tie_conf_raw is not None and tie_conf_raw >= MIN_DISPLAY_CONFIDENCE_SIDE_BET:
                tie_prediction = tie_pred_raw
                tie_confidence = tie_conf_raw

        # --- Side Bet Sniper Opportunity Logic ---
        SIDE_BET_SNIPER_ACCURACY_THRESHOLD = 80 
        SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD = 80 
        SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT = 3 

        # Tie Sniper
        if tie_prediction == "T" and tie_confidence is not None:
            if tie_confidence >= 85 and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER: 
                tie_all_time_acc = module_accuracies_all_time.get("Tie", 0)
                # V7.9.1: Ensure tie_module_prediction_log is long enough for recent accuracy calculation
                if len(self.tie_module_prediction_log) >= SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT:
                    tie_recent_acc = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
                else:
                    tie_recent_acc = 0 # Not enough recent data for sniper
                
                if tie_all_time_acc >= SIDE_BET_SNIPER_ACCURACY_THRESHOLD and tie_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                    is_tie_sniper_opportunity = True

        return (
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_miss_streak, is_sniper_opportunity_main,
            tie_prediction, tie_confidence, 
            is_tie_sniper_opportunity 
        )

