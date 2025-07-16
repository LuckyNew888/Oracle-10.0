# oracle_core.py (Oracle V5.2 - Stricter Sniper Accuracy)
from typing import List, Optional, Literal, Tuple, Dict
import random

Outcome = Literal["P", "B", "T"]

# --- Prediction Modules ---

class RuleEngine:
    """
    Predicts based on simple repeating patterns (e.g., P P P -> P, B B B -> B)
    or alternating patterns (e.g., P B P -> P).
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        # Need at least 3 non-tie outcomes for these rules
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 3:
            return None

        # Rule: Three consecutive same outcomes (e.g., P P P -> P)
        if filtered_history[-1] == filtered_history[-2] == filtered_history[-3]:
            return filtered_history[-1]
        
        # Rule: Alternating pattern (e.g., P B P -> B, B P B -> P)
        if filtered_history[-1] != filtered_history[-2] and filtered_history[-2] != filtered_history[-3]:
            if filtered_history[-1] == filtered_history[-3]: # PBP or BPB
                return "P" if filtered_history[-1] == "B" else "B" # Predict the opposite of the last one
        
        return None

class PatternAnalyzer:
    """
    Predicts based on specific predefined patterns in the recent history.
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        # Filter out ties for pattern analysis
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 4: # Need at least 4 for most patterns
            return None

        # Check for patterns of length 4 to 6
        joined_filtered = "".join(filtered_history)
        
        patterns_and_predictions = {
            "PBPB": "P", "BPBP": "B",       # Ping Pong
            "PPBB": "P", "BBPP": "B",       # Two Two
            "PPPP": "P", "BBBB": "B",       # Dragon / Long streak
            "PPBPP": "P", "BBPBB": "B",     # Long Ping Pong (PBPBP)
            "PPPBBB": "B", "BBBPBB": "P",   # Three-In-A-Row Cut (3P3B)
            "PBBP": "B", "BPPB": "P"        # Double P/B with alternating
        }

        # Check for longest matching pattern first
        for length in range(6, 3, -1): # Check patterns of length 6 down to 4
            if len(joined_filtered) >= length:
                current_pattern = joined_filtered[-length:]
                if current_pattern in patterns_and_predictions:
                    return patterns_and_predictions[current_pattern]
        return None

class TrendScanner:
    """
    Predicts based on the dominant outcome in the recent history.
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 10: # Need at least 10 outcomes for trend
            return None
        
        last_10 = filtered_history[-10:]
        p_count = last_10.count("P")
        b_count = last_10.count("B")

        # If one outcome is significantly more frequent (e.g., > 60% or 7 out of 10)
        if p_count >= 7: # More than 6 (7 or more)
            return "P"
        if b_count >= 7: # More than 6 (7 or more)
            return "B"
        return None

class TwoTwoPattern:
    """
    Predicts based on a specific 2-2 alternating pattern (e.g., PPBB -> P).
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 4:
            return None
        
        last4 = filtered_history[-4:]
        # Check for PPBB, BBPP, and predict the next in sequence
        if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
            # If PPBB, predict P. If BBPP, predict B.
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
            "PBBP": "B", "BPPB": "P"
        }

    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 4: 
            return None
        
        joined = "".join(filtered_history)
        
        for length in range(6, 3, -1):
            if len(joined) >= length:
                pattern_to_check = joined[-length:]
                if pattern_to_check in self.known_patterns:
                    return self.known_patterns[pattern_to_check]
        return None

class FallbackModule:
    """
    Provides a random prediction if no other module can make a prediction.
    """
    def predict(self, history: List[Outcome]) -> Optional[Outcome]:
        return random.choice(["P", "B"])


class ConfidenceScorer:
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy.
    """
    def score(self, 
              predictions: Dict[str, Optional[Outcome]], 
              module_accuracies: Dict[str, float], 
              history: List[Outcome]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
        
        total_score = {"P": 0.0, "B": 0.0}
        
        active_predictions = {name: pred for name, pred in predictions.items() if pred in ("P", "B")}

        if not active_predictions:
            return None, None, 0, None 

        for name, pred in active_predictions.items():
            weight = module_accuracies.get(name, 50.0) / 100.0 
            total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None 

        best_prediction_outcome = max(total_score, key=total_score.get)
        
        sum_of_scores = sum(total_score.values())
        raw_confidence = (total_score[best_prediction_outcome] / sum_of_scores) * 100
        
        confidence = min(int(raw_confidence), 95)
        
        source_modules = [name for name, pred in active_predictions.items() if pred == best_prediction_outcome]
        source_name = ", ".join(source_modules) if source_modules else "Combined"

        pattern = self._extract_relevant_pattern(history, predictions)
        
        return best_prediction_outcome, source_name, confidence, pattern

    def _extract_relevant_pattern(self, history: List[Outcome], predictions: Dict[str, Optional[Outcome]]) -> Optional[str]:
        filtered_history = [o for o in history if o in ("P", "B")]
        if len(filtered_history) < 4:
            return None
        
        joined_filtered = "".join(filtered_history)

        common_patterns = {
            "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
            "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
            "PPPP": "มังกร", "BBBB": "มังกร",
            "PPBPP": "ปิงปองยาว", "BBPBB": "ปิงปองยาว",
            "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
            "PBBP": "คู่สลับ", "BPPB": "คู่สลับ"
        }

        for length in range(6, 3, -1):
            if len(joined_filtered) >= length:
                current_pattern_str = joined_filtered[-length:]
                if current_pattern_str in common_patterns:
                    return common_patterns[current_pattern_str]
        return None


class OracleBrain:
    def __init__(self):
        self.history: List[Outcome] = []
        self.prediction_log: List[Optional[Outcome]] = [] 
        self.result_log: List[Outcome] = [] 
        self.last_prediction: Optional[Outcome] = None 
        self.last_module: Optional[str] = None 

        self.modules_accuracy_log: Dict[str, List[bool]] = {} 
        # New: Log individual module predictions for recent accuracy checks
        # { "ModuleName": [(prediction, actual_outcome_at_that_time), ...] }
        self.individual_module_prediction_log: Dict[str, List[Tuple[Outcome, Outcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": []
        }

        self.rule_engine = RuleEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_scanner = TrendScanner()
        self.two_two_pattern = TwoTwoPattern()
        self.sniper_pattern = SniperPattern() 
        self.fallback_module = FallbackModule() 

        self.scorer = ConfidenceScorer()
        self.show_initial_wait_message = True 

    def add_result(self, outcome: Outcome):
        """
        Adds a new actual outcome to history and logs,
        and updates module accuracy based on the last prediction.
        """
        # First, record individual module predictions *before* adding the new outcome
        # This is crucial for accurate recent module performance tracking
        current_predictions_from_modules = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history),
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history) 
        }
        
        # Log each module's prediction against the *incoming* actual outcome
        for module_name, pred in current_predictions_from_modules.items():
            if pred in ("P", "B") and outcome in ("P", "B"):
                self.individual_module_prediction_log[module_name].append((pred, outcome))


        # Now, add the actual outcome to main history and logs
        self.history.append(outcome)
        self.result_log.append(outcome)
        self.prediction_log.append(self.last_prediction) 

        # Update overall module accuracy log based on the system's final prediction
        if self.last_prediction in ("P", "B") and outcome in ("P", "B"):
            correct = (self.last_prediction == outcome)
            module_name_to_log = self.last_module if self.last_module else "NoPrediction" 
            
            if module_name_to_log not in self.modules_accuracy_log:
                self.modules_accuracy_log[module_name_to_log] = []
            self.modules_accuracy_log[module_name_to_log].append(correct)
        
        self._trim_logs() 

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()
        
        # Remove the last accuracy entry for the module that made the last prediction
        if self.last_module and self.last_module in self.modules_accuracy_log:
            if self.modules_accuracy_log[self.last_module]:
                self.modules_accuracy_log[self.last_module].pop()

        # Remove the last entry from individual module prediction logs
        for module_name in self.individual_module_prediction_log:
            if self.individual_module_prediction_log[module_name]:
                self.individual_module_prediction_log[module_name].pop()


    def reset(self):
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        self.modules_accuracy_log.clear() 
        # Clear individual module prediction logs as well
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name].clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True

    def _trim_logs(self, max_length=100):
        self.history = self.history[-max_length:]
        self.result_log = self.result_log[-max_length:]
        self.prediction_log = self.prediction_log[-max_length:]
        for module_name in self.modules_accuracy_log:
            self.modules_accuracy_log[module_name] = self.modules_accuracy_log[module_name][-max_length:]
        
        # Trim individual module prediction logs
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name] = self.individual_module_prediction_log[module_name][-max_length:]


    def calculate_miss_streak(self) -> int:
        streak = 0
        for pred, actual in zip(reversed(self.prediction_log), reversed(self.result_log)):
            if actual not in ("P", "B") or pred not in ("P", "B"):
                continue 
            
            if pred != actual:
                streak += 1
            else:
                break 
        return streak

    def _calculate_module_accuracy_for_period(self, module_name: str, lookback: Optional[int] = None) -> float:
        """
        Calculates accuracy for a specific module over a given lookback period
        using the overall system's prediction log (for general module accuracy display).
        If lookback is None, calculates all-time accuracy.
        """
        results = self.modules_accuracy_log.get(module_name, [])
        
        if lookback is not None:
            results = results[-lookback:] 

        if results:
            wins = sum(results) 
            total = len(results)
            return (wins / total) * 100
        return 0.0

    def _calculate_individual_module_recent_accuracy(self, module_name: str, predictions_count: int) -> float:
        """
        Calculates the accuracy of a specific module based on its own recent predictions.
        This uses the new individual_module_prediction_log.
        """
        log = self.individual_module_prediction_log.get(module_name, [])
        
        # Take the last 'predictions_count' entries where the module actually made a P/B prediction
        recent_relevant_preds = []
        for pred, actual in reversed(log):
            if pred in ("P", "B") and actual in ("P", "B"):
                recent_relevant_preds.append((pred, actual))
            if len(recent_relevant_preds) >= predictions_count:
                break
        
        if not recent_relevant_preds:
            return 0.0 # No recent relevant predictions
        
        wins = 0
        for pred, actual in recent_relevant_preds:
            if pred == actual:
                wins += 1
        
        return (wins / len(recent_relevant_preds)) * 100


    def get_module_accuracy_all_time(self) -> Dict[str, float]:
        """Returns all-time accuracy for all modules."""
        accuracy_results = {}
        # Ensure all known modules are present in the output, even if they have no history yet
        all_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
        for module_name in all_modules:
            accuracy_results[module_name] = self._calculate_module_accuracy_for_period(module_name, lookback=None)
        
        # Add "NoPrediction" if it exists in logs
        if "NoPrediction" in self.modules_accuracy_log:
            accuracy_results["NoPrediction"] = self._calculate_module_accuracy_for_period("NoPrediction", lookback=None)

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        """Returns accuracy for all modules over the last 'lookback' predictions."""
        accuracy_results = {}
        all_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
        for module_name in all_modules:
            accuracy_results[module_name] = self._calculate_module_accuracy_for_period(module_name, lookback)
        
        if "NoPrediction" in self.modules_accuracy_log:
            accuracy_results["NoPrediction"] = self._calculate_module_accuracy_for_period("NoPrediction", lookback)
        
        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        """
        Returns normalized accuracy (0-1 scale) for each module (all-time),
        used as weights in ConfidenceScorer.
        """
        acc = self.get_module_accuracy_all_time() 
        if not acc:
            # Provide default neutral weights for all known modules if no accuracies exist
            all_known_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
            return {name: 0.5 for name in all_known_modules}
        
        active_accuracies = {k: v for k, v in acc.items() if v > 0 and k not in ["NoPrediction", "Fallback"]} 
        
        if not active_accuracies:
            all_known_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
            return {name: 0.5 for name in all_known_modules}
            
        max_val = max(active_accuracies.values()) 
        if max_val == 0: 
            max_val = 1 
            
        normalized_acc = {}
        for k, v in acc.items():
            if k in ["NoPrediction", "Fallback"]: # Fallback and NoPrediction get neutral weight
                normalized_acc[k] = 0.5
            else:
                normalized_acc[k] = (v / max_val)
        return normalized_acc

    def get_best_recent_module(self, lookback: int = 10) -> Optional[str]:
        modules_to_check = {
            "Rule": self.rule_engine,
            "Pattern": self.pattern_analyzer,
            "Trend": self.trend_scanner,
            "2-2 Pattern": self.two_two_pattern,
            "Sniper": self.sniper_pattern,
            "Fallback": self.fallback_module
        }
        
        module_scores: Dict[str, float] = {}

        for name, module in modules_to_check.items():
            wins = 0
            total_preds = 0
            start_index = max(4, len(self.history) - lookback) 
            
            for j in range(start_index, len(self.history)):
                current_sub_history = self.history[:j]
                
                module_pred = module.predict(current_sub_history)
                
                if module_pred in ("P", "B") and self.history[j] in ("P", "B"): 
                    total_preds += 1
                    if module_pred == self.history[j]:
                        wins += 1
            
            if total_preds > 0:
                module_scores[name] = wins / total_preds
            else:
                module_scores[name] = 0.0 

        if not module_scores:
            return None
        
        return max(module_scores, key=module_scores.get)


    def predict_next(self) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], int, bool]:
        """
        Generates the next prediction, its source, confidence, current miss streak,
        and a flag indicating if it's a "Sniper" opportunity.
        """
        p_count = self.history.count("P")
        b_count = self.history.count("B")
        current_miss_streak = self.calculate_miss_streak()

        # Minimum history for any prediction (20 P/B outcomes)
        # Minimum history for Sniper opportunity (e.g., 30 P/B outcomes)
        MIN_HISTORY_FOR_PREDICTION = 20
        MIN_HISTORY_FOR_SNIPER = 30 # NEW: Stricter minimum history for Sniper

        if (p_count + b_count) < MIN_HISTORY_FOR_PREDICTION or current_miss_streak >= 6:
            self.last_prediction = None
            self.last_module = None
            return None, None, None, None, current_miss_streak, False # No sniper opportunity

        # Get predictions from all active modules
        predictions_from_modules = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history),
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history) 
        }
        
        module_accuracies_for_weights = self.get_module_accuracy_all_time() # Use all-time accuracy for weights

        final_prediction, source_module_name, confidence, pattern_code = \
            self.scorer.score(predictions_from_modules, module_accuracies_for_weights, self.history)

        # Recovery strategy for miss streak 3 or 4
        if current_miss_streak in [3, 4]:
            best_module_for_recovery = self.get_best_recent_module()
            if best_module_for_recovery and predictions_from_modules.get(best_module_for_recovery) in ("P", "B"):
                final_prediction = predictions_from_modules[best_module_for_recovery]
                source_module_name = f"{best_module_for_recovery}-Recovery"

        # --- NEW: Sniper Opportunity Logic (Stricter for V5.2) ---
        is_sniper_opportunity = False
        if final_prediction in ("P", "B") and confidence is not None:
            # Condition 1: Overall confidence is at its maximum
            # Condition 2: No recent miss streak
            # Condition 3: Sufficient history for a highly reliable sniper
            if confidence == 95 and current_miss_streak == 0 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER:
                # Condition 4: All contributing modules must have very high individual ALL-TIME accuracy
                contributing_modules = [m.strip() for m in source_module_name.split(',')]
                all_contributing_modules_high_all_time_accuracy = True
                
                SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD = 90 # Raised from 85% to 90%

                if not contributing_modules or "NoPrediction" in contributing_modules or "Fallback" in contributing_modules:
                    all_contributing_modules_high_all_time_accuracy = False
                else:
                    for module_name in contributing_modules:
                        mod_acc = self._calculate_module_accuracy_for_period(module_name, lookback=None) # Use all-time accuracy
                        if mod_acc < SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD:
                            all_contributing_modules_high_all_time_accuracy = False
                            break
                
                # Condition 5: If Sniper module is a contributor, its recent performance must also be excellent
                sniper_module_recent_accuracy_ok = True
                if "Sniper" in contributing_modules:
                    # Check Sniper's recent accuracy (e.g., last 5 predictions it actually made)
                    SNIPER_RECENT_PREDICTION_COUNT = 5 # Number of recent predictions to check
                    SNIPER_RECENT_ACCURACY_THRESHOLD = 90 # e.g., 90% or 100%

                    sniper_recent_acc = self._calculate_individual_module_recent_accuracy("Sniper", SNIPER_RECENT_PREDICTION_COUNT)
                    
                    # If Sniper made at least some predictions recently and its recent accuracy is high
                    if sniper_recent_acc < SNIPER_RECENT_ACCURACY_THRESHOLD:
                        sniper_module_recent_accuracy_ok = False
                
                if all_contributing_modules_high_all_time_accuracy and sniper_module_recent_accuracy_ok:
                    is_sniper_opportunity = True
        # --- END NEW Sniper Opportunity Logic ---

        self.last_prediction = final_prediction
        self.last_module = source_module_name 

        return final_prediction, source_module_name, confidence, pattern_code, current_miss_streak, is_sniper_opportunity

