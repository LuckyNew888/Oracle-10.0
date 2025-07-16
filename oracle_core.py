# oracle_core.py (Oracle V6.0 - Final Clean Version)
from typing import List, Optional, Literal, Tuple, Dict, Any
import random
from dataclasses import dataclass

# Define main outcomes
MainOutcome = Literal["P", "B", "T"]

# Define additional outcomes (side bets)
# These are flags for whether they occurred in a round
@dataclass
class RoundResult:
    main_outcome: MainOutcome
    is_player_pair: bool = False
    is_banker_pair: bool = False
    is_banker_6: bool = False # For Super 6 variant

# --- Prediction Modules ---

# Helper function to get filtered history (P/B only) from new RoundResult history
def _get_main_outcome_history(history: List[RoundResult]) -> List[MainOutcome]:
    return [r.main_outcome for r in history if r.main_outcome in ("P", "B")]

# Helper function to get specific side bet history flags (True/False for occurrence)
def _get_side_bet_history_flags(history: List[RoundResult], bet_type: str) -> List[bool]:
    if bet_type == "T":
        return [r.main_outcome == "T" for r in history]
    elif bet_type == "PP":
        return [r.is_player_pair for r in history]
    elif bet_type == "BP":
        return [r.is_banker_pair for r in history]
    elif bet_type == "B6":
        return [r.is_banker_6 for r in history]
    return []

# Helper function to get combined pair flags
def _get_combined_pair_history_flags(history: List[RoundResult]) -> List[bool]:
    return [r.is_player_pair or r.is_banker_pair for r in history]


class RuleEngine:
    """
    Predicts based on simple repeating patterns (e.g., P P P -> P, B B B -> B)
    or alternating patterns (e.g., P B P -> P).
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 3:
            return None

        if filtered_history[-1] == filtered_history[-2] == filtered_history[-3]:
            return filtered_history[-1]
        
        if filtered_history[-1] != filtered_history[-2] and filtered_history[-2] != filtered_history[-3]:
            if filtered_history[-1] == filtered_history[-3]:
                return "P" if filtered_history[-1] == "B" else "B"
        
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
            "PPBPP": "P", "BBPBB": "B",     
            "PPPBBB": "B", "BBBPBB": "P",   
            "PBBP": "B", "BPPB": "P"        
        }

        for length in range(6, 3, -1):
            if len(joined_filtered) >= length:
                current_pattern = joined_filtered[-length:]
                if current_pattern in patterns_and_predictions:
                    return patterns_and_predictions[current_pattern]
        return None

class TrendScanner:
    """
    Predicts based on the dominant outcome in the recent history.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 10:
            return None
        
        last_10 = filtered_history[-10:]
        p_count = last_10.count("P")
        b_count = last_10.count("B")

        if p_count >= 7:
            return "P"
        if b_count >= 7:
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
            "PBBP": "B", "BPPB": "P"
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
        # This module should always return a prediction unless history is empty, which is handled
        # by MIN_HISTORY_FOR_PREDICTION in OracleBrain.predict_next
        return random.choice(["P", "B"])

# --- ENHANCED PREDICTION MODULES FOR SIDE BETS (V6.0) ---

class TiePredictor:
    """
    Predicts Tie outcomes with further enhanced logic for V6.0.
    """
    def predict(self, history: List[RoundResult]) -> Optional[Literal["T"]]:
        tie_flags = _get_side_bet_history_flags(history, "T")
        main_history_pb = _get_main_outcome_history(history) # Only P/B for main patterns

        if len(tie_flags) < 25: # Increased history requirement for even better tie prediction
            return None
        
        # Rule 1: Tie after a long streak of P/B (e.g., 12+ non-tie outcomes)
        if len(main_history_pb) >= 12 and not any(tie_flags[-12:]):
            return "T"
        
        # Rule 2: If tie occurred recently and then a few non-ties, it might repeat (T _ _ _ T)
        # More specific: T followed by 4 non-ties, then predict T
        if len(tie_flags) >= 5 and tie_flags[-5] and not any(tie_flags[-4:]):
            return "T" 
            
        # Rule 3: Tie after specific alternating patterns in main outcomes (e.g., PBPBPB, then T)
        if len(main_history_pb) >= 6:
            recent_main = "".join(main_history_pb[-6:])
            if recent_main in ["PBPBPB", "BPBPBP"]: # Longer alternating patterns often break with T
                return "T"
        
        # Rule 4: If ties are very frequent in recent history (e.g., 6+ in last 20)
        # Higher threshold for frequency and longer lookback
        if tie_flags[-20:].count(True) >= 6:
            return "T"
            
        # Rule 5: Tie after a specific main outcome sequence (e.g., P B B P, then T)
        if len(main_history_pb) >= 5:
            recent_main_5 = "".join(main_history_pb[-5:])
            if recent_main_5 == "PBBPB" or recent_main_5 == "BPPBP": # More complex patterns for tie
                return "T"

        # Rule 6: Tie after a long streak of one side winning (e.g., 7+ P's or 7+ B's)
        if len(main_history_pb) >= 7:
            if main_history_pb[-7:].count("P") == 7 or main_history_pb[-7:].count("B") == 7:
                return "T"
        
        # Rule 7: Tie after a specific "chop" pattern (e.g., P B P B, then P P -> T)
        if len(main_history_pb) >= 6:
            recent_main_6 = "".join(main_history_pb[-6:])
            if recent_main_6 == "PBPBPP" or recent_main_6 == "BPBPBB":
                return "T"

        return None

class PairPredictor:
    """
    Predicts Player Pair or Banker Pair with further enhanced logic for V6.0.
    """
    def predict(self, history: List[RoundResult]) -> Optional[Literal["PP", "BP"]]:
        player_pair_flags = _get_side_bet_history_flags(history, "PP")
        banker_pair_flags = _get_side_bet_history_flags(history, "BP")
        combined_pair_flags = _get_combined_pair_history_flags(history)
        main_history_pb = _get_main_outcome_history(history)

        if len(combined_pair_flags) < 25: # Increased history requirement for pair prediction
            return None
        
        # Rule 1: Pair just occurred, strong chance of another pair (momentum)
        # Predict the specific pair if it just occurred, with higher confidence for immediate repeat
        if player_pair_flags[-1]:
            return "PP"
        if banker_pair_flags[-1]:
            return "BP"
        
        # Rule 2: If no pairs for a very long time (e.g., 20+ rounds), predict a pair might be due
        if not any(combined_pair_flags[-20:]):
            return random.choice(["PP", "BP"])
            
        # Rule 3: If pairs are very frequent in recent history (e.g., 6+ in last 20)
        if combined_pair_flags[-20:].count(True) >= 6:
            pp_recent_count = player_pair_flags[-20:].count(True)
            bp_recent_count = banker_pair_flags[-20:].count(True)
            if pp_recent_count > bp_recent_count:
                return "PP"
            elif bp_recent_count > pp_recent_count:
                return "BP"
            else: 
                return random.choice(["PP", "BP"])
        
        # Rule 4: Pair after specific main outcome patterns (e.g., P P P B, then Pair)
        if len(main_history_pb) >= 4:
            recent_main = "".join(main_history_pb[-4:])
            if recent_main == "PPPB": # Player streak followed by Banker, often a Player Pair
                return "PP" 
            if recent_main == "BBBP": # Banker streak followed by Player, often a Banker Pair
                return "BP"

        # Rule 5: Pair after an alternating sequence of pairs (e.g., PP BP PP -> BP)
        if len(combined_pair_flags) >= 4 and combined_pair_flags[-1] and combined_pair_flags[-2] and combined_pair_flags[-3] and combined_pair_flags[-4]:
            if player_pair_flags[-1] and banker_pair_flags[-2] and player_pair_flags[-3] and banker_pair_flags[-4]:
                return "PP" # BP PP BP PP -> PP (next in sequence)
            if banker_pair_flags[-1] and player_pair_flags[-2] and banker_pair_flags[-3] and player_pair_flags[-4]:
                return "BP" # PP BP PP BP -> BP (next in sequence)

        # Rule 6: Pair after a "dragon" (long streak) breaks
        if len(main_history_pb) >= 8:
            if main_history_pb[-8:].count("P") == 7 and main_history_pb[-1] == "B": # P P P P P P P B -> Pair (often PP)
                return "PP"
            if main_history_pb[-8:].count("B") == 7 and main_history_pb[-1] == "P": # B B B B B B B P -> Pair (often BP)
                return "BP"

        return None

class Banker6Predictor:
    """
    Predicts Banker 6 (Super 6) outcomes with further enhanced, but still conservative, logic for V6.0.
    B6 is rare, so predictions should be very cautious.
    """
    def predict(self, history: List[RoundResult]) -> Optional[Literal["B6"]]:
        b6_flags = _get_side_bet_history_flags(history, "B6")
        main_history_outcomes = [r.main_outcome for r in history] 
        main_history_pb = _get_main_outcome_history(history) 

        if len(b6_flags) < 50: # Increased history requirement for B6, very rare
            return None
        
        # Rule 1: B6 just occurred (very strong immediate signal)
        if b6_flags[-1]:
            return "B6"
        
        # Rule 2: If Banker has won with 6 points recently (e.g., in last 20 rounds)
        # and there's a very strong Banker trend (e.g., 6+ Banker wins in last 7)
        if b6_flags[-20:].count(True) >= 1: # B6 occurred in last 20 rounds
            recent_banker_wins = [o for o in main_history_pb[-7:] if o == "B"]
            if recent_banker_wins.count("B") >= 6: # Very strong Banker dominance
                return "B6"
        
        # Rule 3: If Banker has been dominant for a very long time (e.g., 10+ B's in last 12)
        # and no B6 has occurred in that period, it might be due. (Cautious)
        if main_history_pb[-12:].count("B") >= 10 and not any(b6_flags[-12:]):
            return "B6"
            
        # Rule 4: Very rare: B6 after a very long absence (e.g., 40+ rounds)
        if len(b6_flags) >= 40 and not any(b6_flags[-40:]):
            return "B6"

        # Rule 5: B6 after a specific Banker streak (e.g., exactly 6 or 7 Banker wins)
        if len(main_history_pb) >= 7:
            if main_history_pb[-7:].count("B") == 7 and not any(b6_flags[-7:]): 
                return "B6"
            if len(main_history_pb) >= 6 and main_history_pb[-6:].count("B") == 6 and not any(b6_flags[-6:]): 
                return "B6"
        
        # Rule 6: B6 after a series of "chop" Banker outcomes (e.g., B P B P B)
        if len(main_history_pb) >= 5:
            recent_main_5 = "".join(main_history_pb[-5:])
            if recent_main_5 == "BPBPB" and not any(b6_flags[-5:]):
                return "B6"

        return None


class AdaptiveScorer: # Renamed from ConfidenceScorer
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy, with adaptive weighting.
    This scorer is primarily for main P/B outcomes.
    """
    def score(self, 
              predictions: Dict[str, Optional[MainOutcome]], 
              module_accuracies_all_time: Dict[str, float], # All-time accuracy for baseline
              module_accuracies_recent: Dict[str, float], # Recent accuracy for adaptive weighting
              history: List[RoundResult]) -> Tuple[Optional[MainOutcome], Optional[str], Optional[int], Optional[str]]:
        
        total_score = {"P": 0.0, "B": 0.0}
        
        active_predictions = {name: pred for name, pred in predictions.items() if pred in ("P", "B")}

        if not active_predictions:
            return None, None, 0, None 

        for name, pred in active_predictions.items():
            # Adaptive weighting: combine all-time and recent accuracy
            # If accuracy is 0.0, treat it as 50% for initial weighting to allow prediction
            all_time_acc_val = module_accuracies_all_time.get(name, 0.0)
            recent_acc_val = module_accuracies_recent.get(name, 0.0)

            # Use 50% (0.5 weight) if accuracy is 0.0 or module hasn't made enough predictions yet
            all_time_weight = (all_time_acc_val if all_time_acc_val > 0.0 else 50.0) / 100.0
            recent_weight = (recent_acc_val if recent_acc_val > 0.0 else 50.0) / 100.0
            
            # Simple adaptive blend: 70% recent, 30% all-time (can be tuned)
            weight = (recent_weight * 0.7) + (all_time_weight * 0.3)
            
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
        self.history: List[RoundResult] = [] 
        self.prediction_log: List[Optional[MainOutcome]] = [] 
        self.result_log: List[MainOutcome] = [] 
        self.last_prediction: Optional[MainOutcome] = None 
        self.last_module: Optional[str] = None 

        self.modules_accuracy_log: Dict[str, List[bool]] = {} 
        self.individual_module_prediction_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": []
        }
        self.tie_module_prediction_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 
        self.pair_module_prediction_log: List[Tuple[Optional[Literal["PP", "BP"]], bool]] = [] 
        self.banker6_module_prediction_log: List[Tuple[Optional[Literal["B6"]], bool]] = [] 


        # Initialize all prediction modules (P/B)
        self.rule_engine = RuleEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_scanner = TrendScanner()
        self.two_two_pattern = TwoTwoPattern()
        self.sniper_pattern = SniperPattern() 
        self.fallback_module = FallbackModule() 

        # Initialize side bet prediction modules
        self.tie_predictor = TiePredictor()
        self.pair_predictor = PairPredictor()
        self.banker6_predictor = Banker6Predictor()

        self.scorer = AdaptiveScorer() # Changed to AdaptiveScorer
        self.show_initial_wait_message = True 

    def add_result(self, main_outcome: MainOutcome, is_player_pair: bool = False, is_banker_pair: bool = False, is_banker_6: bool = False):
        """
        Adds a new actual outcome to history and logs,
        and updates module accuracy based on the last prediction.
        """
        new_round_result = RoundResult(main_outcome, is_player_pair, is_banker_pair, is_banker_6)
        
        # --- Record individual main P/B module predictions *before* adding the new outcome ---
        current_predictions_from_modules_main = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history),
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history) 
        }
        
        for module_name, pred in current_predictions_from_modules_main.items():
            if pred in ("P", "B") and main_outcome in ("P", "B"):
                self.individual_module_prediction_log[module_name].append((pred, main_outcome))

        # --- Record individual side bet module predictions *before* adding the new outcome ---
        tie_pred_for_log = self.tie_predictor.predict(self.history)
        pair_pred_for_log = self.pair_predictor.predict(self.history)
        b6_pred_for_log = self.banker6_predictor.predict(self.history)

        self.tie_module_prediction_log.append((tie_pred_for_log, main_outcome == "T"))
        self.pair_module_prediction_log.append((pair_pred_for_log, is_player_pair or is_banker_pair)) 
        self.banker6_module_prediction_log.append((b6_pred_for_log, is_banker_6))


        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.prediction_log.append(self.last_prediction) 
        self.result_log.append(main_outcome) 

        # Update overall module accuracy log based on the system's final main prediction
        if self.last_prediction in ("P", "B") and main_outcome in ("P", "B"):
            correct = (self.last_prediction == main_outcome)
            module_name_to_log = self.last_module if self.last_module else "NoPrediction" 
            
            if module_name_to_log not in self.modules_accuracy_log:
                self.modules_accuracy_log[module_name_to_log] = []
            self.modules_accuracy_log[module_name_to_log].append(correct)
        
        self._trim_logs() 

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()
        
        if self.last_module and self.last_module in self.modules_accuracy_log:
            if self.modules_accuracy_log[self.last_module]:
                self.modules_accuracy_log[self.last_module].pop()

        for module_name in self.individual_module_prediction_log:
            if self.individual_module_prediction_log[module_name]:
                self.individual_module_prediction_log[module_name].pop()
        
        self.tie_module_prediction_log.pop() if self.tie_module_prediction_log else None
        self.pair_module_prediction_log.pop() if self.pair_module_prediction_log else None
        self.banker6_module_prediction_log.pop() if self.banker6_module_prediction_log else None


    def reset(self):
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        self.modules_accuracy_log.clear() 
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name].clear()
        
        self.tie_module_prediction_log.clear()
        self.pair_module_prediction_log.clear()
        self.banker6_module_prediction_log.clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True

    def _trim_logs(self, max_length=100):
        self.history = self.history[-max_length:]
        self.result_log = self.result_log[-max_length:]
        self.prediction_log = self.prediction_log[-max_length:]
        for module_name in self.modules_accuracy_log:
            self.modules_accuracy_log[module_name] = self.modules_accuracy_log[module_name][-max_length:]
        
        for module_name in self.individual_module_prediction_log:
            self.individual_module_prediction_log[module_name] = self.individual_module_prediction_log[module_name][-max_length:]
        
        self.tie_module_prediction_log = self.tie_module_prediction_log[-max_length:]
        self.pair_module_prediction_log = self.pair_module_prediction_log[-max_length:]
        self.banker6_module_prediction_log = self.banker6_module_prediction_log[-max_length:]


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
        results = self.modules_accuracy_log.get(module_name, [])
        
        if lookback is not None:
            results = results[-lookback:] 

        if results:
            wins = sum(results) 
            total = len(results)
            return (wins / total) * 100
        return 0.0

    def _calculate_individual_module_recent_accuracy(self, module_name: str, predictions_count: int) -> float:
        log = self.individual_module_prediction_log.get(module_name, [])
        
        recent_relevant_preds = []
        for pred, actual in reversed(log):
            if pred in ("P", "B") and actual in ("P", "B"): 
                recent_relevant_preds.append((pred, actual))
            if len(recent_relevant_preds) >= predictions_count:
                break
        
        if not recent_relevant_preds:
            return 0.0 
        
        wins = 0
        for pred, actual in recent_relevant_preds:
            if pred == actual:
                wins += 1
        
        return (wins / len(recent_relevant_preds)) * 100

    def _calculate_side_bet_module_accuracy(self, log: List[Tuple[Optional[Any], bool]], lookback: Optional[int] = None) -> float:
        relevant_log = log
        if lookback is not None:
            relevant_log = log[-lookback:]
        
        wins = 0
        total_predictions = 0
        
        for predicted_val, actual_flag in relevant_log:
            # Only count if the module actually made a prediction (predicted_val is not None)
            if predicted_val is not None:
                total_predictions += 1
                if actual_flag: 
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0


    def get_module_accuracy_all_time(self) -> Dict[str, float]:
        accuracy_results = {}
        all_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
        for module_name in all_modules:
            accuracy_results[module_name] = self._calculate_module_accuracy_for_period(module_name, lookback=None)
        
        if "NoPrediction" in self.modules_accuracy_log:
            accuracy_results["NoPrediction"] = self._calculate_module_accuracy_for_period("NoPrediction", lookback=None)

        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback=None)
        accuracy_results["Pair"] = self._calculate_side_bet_module_accuracy(self.pair_module_prediction_log, lookback=None)
        accuracy_results["Banker6"] = self._calculate_side_bet_module_accuracy(self.banker6_module_prediction_log, lookback=None)

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        accuracy_results = {}
        all_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback"]
        for module_name in all_modules:
            accuracy_results[module_name] = self._calculate_module_accuracy_for_period(module_name, lookback)
        
        if "NoPrediction" in self.modules_accuracy_log:
            accuracy_results["NoPrediction"] = self._calculate_module_accuracy_for_period("NoPrediction", lookback)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, lookback)
        accuracy_results["Pair"] = self._calculate_side_bet_module_accuracy(self.pair_module_prediction_log, lookback)
        accuracy_results["Banker6"] = self._calculate_side_bet_module_accuracy(self.banker6_module_prediction_log, lookback)

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        if not acc:
            all_known_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "Tie", "Pair", "Banker6"] 
            return {name: 0.5 for name in all_known_modules}
        
        active_accuracies = {k: v for k, v in acc.items() if v > 0 and k not in ["NoPrediction", "Fallback", "Tie", "Pair", "Banker6"]} 
        
        if not active_accuracies:
            all_known_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "Tie", "Pair", "Banker6"]
            return {name: 0.5 for name in all_known_modules}
            
        max_val = max(active_accuracies.values()) 
        if max_val == 0: 
            max_val = 1 
            
        normalized_acc = {}
        for k, v in acc.items():
            if k in ["NoPrediction", "Fallback", "Tie", "Pair", "Banker6"]: 
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
                
                if module_pred in ("P", "B") and self.history[j].main_outcome in ("P", "B"): 
                    total_preds += 1
                    if module_pred == self.history[j].main_outcome:
                        wins += 1
            
            if total_preds > 0:
                module_scores[name] = wins / total_preds
            else:
                module_scores[name] = 0.0 

        if not module_scores:
            return None
        
        return max(module_scores, key=module_scores.get)


    def predict_next(self) -> Tuple[
        Optional[MainOutcome], Optional[str], Optional[int], Optional[str], int, bool, # Main prediction
        Optional[Literal["T"]], # Tie prediction
        Optional[Literal["PP", "BP"]], # Pair prediction
        Optional[Literal["B6"]], # Banker 6 prediction
        bool, bool, bool # is_tie_sniper_opportunity, is_pair_sniper_opportunity, is_banker6_sniper_opportunity
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
        MIN_HISTORY_FOR_SIDE_BET_SNIPER = 40 

        final_prediction_main = None
        source_module_name_main = None
        confidence_main = None
        pattern_code_main = None
        is_sniper_opportunity_main = False 
        is_tie_sniper_opportunity = False
        is_pair_sniper_opportunity = False
        is_banker6_sniper_opportunity = False

        if (p_count + b_count) < MIN_HISTORY_FOR_PREDICTION or current_miss_streak >= 6:
            self.last_prediction = None
            self.last_module = None
            return None, None, None, None, current_miss_streak, False, None, None, None, False, False, False 

        predictions_from_modules = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history),
            "Trend": self.trend_scanner.predict(self.history),
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history) 
        }
        
        module_accuracies_all_time = self.get_module_accuracy_all_time()
        module_accuracies_recent_10 = self.get_module_accuracy_recent(10) 

        final_prediction_main, source_module_name_main, confidence_main, pattern_code_main = \
            self.scorer.score(predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history) 

        if current_miss_streak in [3, 4]:
            best_module_for_recovery = self.get_best_recent_module()
            if best_module_for_recovery and predictions_from_modules.get(best_module_for_recovery) in ("P", "B"):
                final_prediction_main = predictions_from_modules[best_module_for_recovery]
                source_module_name_main = f"{best_module_for_recovery}-Recovery"

        # --- Main Outcome Sniper Opportunity Logic ---
        if final_prediction_main in ("P", "B") and confidence_main is not None:
            if confidence_main == 95 and current_miss_streak == 0 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER:
                contributing_modules = [m.strip() for m in source_module_name_main.split(',')]
                all_contributing_modules_high_all_time_accuracy = True
                
                SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD = 90 

                if not contributing_modules or "NoPrediction" in contributing_modules or "Fallback" in contributing_modules:
                    all_contributing_modules_high_all_time_accuracy = False
                else:
                    for module_name in contributing_modules:
                        mod_acc = self._calculate_module_accuracy_for_period(module_name, lookback=None) 
                        if mod_acc < SNIPER_MODULE_ALL_TIME_ACCURACY_THRESHOLD:
                            all_contributing_modules_high_all_time_accuracy = False
                            break
                
                sniper_module_recent_accuracy_ok = True
                if "Sniper" in contributing_modules:
                    SNIPER_RECENT_PREDICTION_COUNT = 5 
                    SNIPER_RECENT_ACCURACY_THRESHOLD = 90 

                    sniper_recent_acc = self._calculate_individual_module_recent_accuracy("Sniper", SNIPER_RECENT_PREDICTION_COUNT)
                    
                    if sniper_recent_acc < SNIPER_RECENT_ACCURACY_THRESHOLD:
                        sniper_module_recent_accuracy_ok = False
                
                if all_contributing_modules_high_all_time_accuracy and sniper_module_recent_accuracy_ok:
                    is_sniper_opportunity_main = True
        # --- END Main Outcome Sniper Logic ---

        self.last_prediction = final_prediction_main
        self.last_module = source_module_name_main 

        # --- Side Bet Predictions (Now based on enhanced logic) ---
        tie_prediction = self.tie_predictor.predict(self.history)
        pair_prediction = self.pair_predictor.predict(self.history)
        banker6_prediction = self.banker6_predictor.predict(self.history)

        # --- Side Bet Sniper Opportunity Logic (NEW for V6.0) ---
        SIDE_BET_SNIPER_ACCURACY_THRESHOLD = 80 
        SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD = 90 
        SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT = 3 

        # Tie Sniper
        if tie_prediction == "T" and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER:
            tie_all_time_acc = module_accuracies_all_time.get("Tie", 0)
            tie_recent_acc = self._calculate_side_bet_module_accuracy(self.tie_module_prediction_log, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
            
            if tie_all_time_acc >= SIDE_BET_SNIPER_ACCURACY_THRESHOLD and tie_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                is_tie_sniper_opportunity = True

        # Pair Sniper
        if pair_prediction in ("PP", "BP") and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER:
            pair_all_time_acc = module_accuracies_all_time.get("Pair", 0)
            pair_recent_acc = self._calculate_side_bet_module_accuracy(self.pair_module_prediction_log, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
            
            if pair_all_time_acc >= SIDE_BET_SNIPER_ACCURACY_THRESHOLD and pair_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                is_pair_sniper_opportunity = True

        # Banker 6 Sniper (even more stringent, or higher history requirement)
        if banker6_prediction == "B6" and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER + 10: 
            b6_all_time_acc = module_accuracies_all_time.get("Banker6", 0)
            b6_recent_acc = self._calculate_side_bet_module_accuracy(self.banker6_module_prediction_log, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
            
            # B6 requires very high confidence due to rarity
            if b6_all_time_acc >= (SIDE_BET_SNIPER_ACCURACY_THRESHOLD + 5) and b6_recent_acc >= (SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD + 5):
                is_banker6_sniper_opportunity = True
        # --- END Side Bet Sniper Logic ---


        return (
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_miss_streak, is_sniper_opportunity_main,
            tie_prediction, pair_prediction, banker6_prediction,
            is_tie_sniper_opportunity, is_pair_sniper_opportunity, is_banker6_sniper_opportunity
        )

