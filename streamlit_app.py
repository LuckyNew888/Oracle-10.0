# streamlit_app.py (Oracle V8.2.1 - Improve Tie Prediction)
import streamlit as st
import time 
from typing import List, Optional, Literal, Tuple, Dict, Any
import random
from dataclasses import dataclass
import json # For handling JSON string for Firebase config (though not used for persistence in this version)

# --- Define main outcomes ---
MainOutcome = Literal["P", "B", "T"]

# --- Define additional outcomes (side bets) ---
@dataclass
class RoundResult:
    main_outcome: MainOutcome
    is_any_natural: bool = False # True if Player or Banker gets a Natural 8/9

# --- Helper functions ---
def _get_main_outcome_history(history: List[RoundResult]) -> List[MainOutcome]:
    """Extracts P/B outcomes from a list of RoundResult objects."""
    return [r.main_outcome for r in history if r.main_outcome in ("P", "B")]

def _get_side_bet_history_flags(history: List[RoundResult], bet_type: str) -> List[bool]:
    """Extracts boolean flags for specific side bet occurrences."""
    if bet_type == "T":
        return [r.main_outcome == "T" for r in history]
    return []

# --- Prediction Modules ---

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
    V8.2.0: Dynamically adjusts pattern checking priority based on choppiness.
    """
    def __init__(self):
        self.patterns_and_predictions = { # Moved to init for clarity
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

    def predict(self, history: List[RoundResult], choppiness_rate: float) -> Optional[MainOutcome]: # Added choppiness_rate
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None

        joined_filtered = "".join(filtered_history)
        
        # V8.2.0: Dynamic pattern window - adjust iteration based on choppiness
        # If very choppy, prioritize shorter patterns (e.g., 3-length patterns first)
        if choppiness_rate > 0.7: 
            lengths_to_check = range(3, 7) # Check 3-length first, then 4, 5, 6
        # If very streaky, prioritize longer patterns (e.g., 6-length patterns first)
        elif choppiness_rate < 0.3: 
            lengths_to_check = range(6, 2, -1) # Check 6-length first, then 5, 4, 3
        # Moderate choppiness, default to checking longer patterns first
        else: 
            lengths_to_check = range(6, 2, -1) # Default behavior (6 down to 3)

        for length in lengths_to_check: 
            if len(joined_filtered) >= length:
                current_pattern = joined_filtered[-length:]
                if current_pattern in self.patterns_and_predictions:
                    return self.patterns_and_predictions[current_pattern]
        return None

class TrendScanner:
    """
    Predicts based on the dominant outcome in the recent history.
    V8.0.0: Refined dynamic lookback for smoother scaling and improved trend detection.
    V8.2.0: Explicitly noted as part of Dynamic Pattern Window concept.
    """
    def predict(self, history: List[RoundResult], choppiness_rate: float) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        # V8.2.0: Dynamic lookback - adjusts based on choppiness.
        # If choppy, lookback is shorter (focus on recent volatility).
        # If streaky, lookback is longer (focus on sustained trend).
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

class DragonTailDetector:
    """
    Detects a 'Dragon Tail' pattern (e.g., PPPPBP -> P or BBBBPB -> B)
    where a long streak is broken by one opposite, then resumes.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 6: # Need at least 5 for streak + 1 opposite
            return None

        # Check for PPPPBP (4 P's, then B, then P)
        if filtered_history[-6:] == ["P", "P", "P", "P", "B", "P"]:
            return "P"
        # Check for BBBBPB (4 B's, then P, then B)
        if filtered_history[-6:] == ["B", "B", "B", "B", "P", "B"]:
            return "B"
        
        # Consider shorter versions too, like PPPBP or BBBPB
        if len(filtered_history) >= 5:
            # Check for PPPBP (3 P's, then B, then P)
            if filtered_history[-5:] == ["P", "P", "P", "B", "P"]:
                return "P"
            # Check for BBBPB (3 B's, then P, then B)
            if filtered_history[-5:] == ["B", "B", "B", "P", "B"]:
                return "B"

        return None

class AdvancedChopPredictor:
    """
    Predicts a 'chop' (break) after established long streaks (Dragon) or alternating patterns (Ping-Pong).
    V8.1.5: Enhanced to specifically handle PPPBBB/BBBPPP ("สามตัวตัด") patterns.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        
        # V8.1.5: Specific handling for PPPBBB / BBBPPP ("สามตัวตัด")
        if len(filtered_history) >= 6:
            last_6 = filtered_history[-6:]
            if last_6 == ["P", "P", "P", "B", "B", "B"]:
                return "B" # Predict B after PPPBBB
            if last_6 == ["B", "B", "B", "P", "P", "P"]:
                return "P" # Predict P after BBBPPP

        # --- Dragon Chop Detection ---
        # Look for a streak of at least 4, followed by an opposite, and predict that opposite
        # Example: PPPPP B -> Predict B
        for streak_len in range(6, 3, -1): # Check for streaks of 6 down to 4
            if len(filtered_history) >= streak_len + 1:
                recent_segment = filtered_history[-(streak_len + 1):]
                
                # Check if the first 'streak_len' elements are the same
                if all(x == recent_segment[0] for x in recent_segment[:streak_len]):
                    # Check if the last element is different from the streak
                    if recent_segment[-1] != recent_segment[0]:
                        # This means a streak was broken by the last outcome.
                        # We predict that the *next* outcome will be the same as the one that broke the streak.
                        # Example: P P P P P B. The streak was P, broken by B. We predict B for the next one.
                        return recent_segment[-1] 

        # --- Ping-Pong Chop Detection ---
        # Look for a ping-pong pattern of at least 5, followed by a repeat, and predict the repeat
        # Example: P B P B P P -> Predict P
        # Example: B P B P B B -> Predict B
        if len(filtered_history) >= 6: # Need at least 6 for PBPBP P or BPBPB B
            last_6 = filtered_history[-6:]
            # Check for PBPBP P
            if last_6 == ["P", "B", "P", "B", "P", "P"]:
                return "P"
            # Check for BPBPB B
            if last_6 == ["B", "P", "B", "P", "B", "B"]:
                return "B"
        
        if len(filtered_history) >= 5: # Check for shorter ping-pong chop
            last_5 = filtered_history[-5:]
            # Check for PBP P (Ping-pong of 4, then a repeat)
            if last_5 == ["P", "B", "P", "B", "P"]: # This is a ping-pong, not a chop
                pass # Do nothing, let other modules handle
            elif last_5 == ["B", "P", "B", "P", "B"]: # This is a ping-pong, not a chop
                pass # Do nothing, let other modules handle
            elif len(filtered_history) >= 4: # Check for PBP P or BPB B
                last_4 = filtered_history[-4:]
                if last_4 == ["P", "B", "P", "P"]: # PBPP -> Predict P (Chop from ping-pong)
                    return "P"
                if last_4 == ["B", "P", "B", "B"]: # BPBB -> Predict B (Chop from ping-pong)
                    return "B"


        return None


# --- ENHANCED PREDICTION MODULES FOR SIDE BETS (V8.0.0, V8.0.1, V8.0.2, V8.0.3, V8.0.4, V8.0.5) ---

class TiePredictor:
    """
    Predicts Tie outcomes with confidence.
    V8.0.0: Significantly enhanced logic for better accuracy and more proactive predictions.
    V8.0.1: Adjusted long_lookback_for_prob to be more realistic for a Baccarat shoe.
    V8.0.3: Further adjusted long_lookback_for_prob to 50 for faster responsiveness within a shoe.
    V8.0.4: Added min_tie_occurrences and enhanced cooldown logic for more reliable predictions.
    V8.2.1: Refined Tie Clustering rule to prevent immediate re-prediction after a Tie result.
    """
    THEORETICAL_PROB = 0.0952 # Approx. 9.52% for 8 decks

    def predict(self, history: List[RoundResult]) -> Tuple[Optional[Literal["T"]], Optional[int]]:
        tie_flags = _get_side_bet_history_flags(history, "T")
        main_history_pb = _get_main_outcome_history(history) 
        
        tie_confidence = 0

        # V8.0.4: Minimum history for any Tie prediction
        if len(tie_flags) < 25: 
            return None, None
        
        long_lookback_for_prob = min(len(tie_flags), 50) 
        short_lookback_for_prob = min(len(tie_flags), 20) 

        actual_tie_count_long = tie_flags[-long_lookback_for_prob:].count(True)
        actual_tie_count_short = tie_flags[-short_lookback_for_prob:].count(True)

        expected_tie_count_long = long_lookback_for_prob * self.THEORETICAL_PROB
        expected_tie_count_short = short_lookback_for_prob * self.THEORETICAL_PROB

        # V8.0.4: New rule - require at least one tie occurrence in the long lookback for "due" prediction
        MIN_TIE_OCCURRENCES_FOR_DUE = 1 
        if actual_tie_count_long < MIN_TIE_OCCURRENCES_FOR_DUE and len(tie_flags) >= long_lookback_for_prob:
            # If no ties have occurred in the long lookback, and we have enough history, don't predict "due"
            pass # Skip due rules, proceed to pattern rules
        else:
            # Rule 1: Ties are "due" based on long-term underperformance
            if actual_tie_count_long < expected_tie_count_long * 0.9: 
                due_factor = (expected_tie_count_long * 0.9 - actual_tie_count_long) / expected_tie_count_long
                tie_confidence = min(90, 60 + int(due_factor * 100 * 0.7)) 
                if tie_confidence >= 55: return "T", tie_confidence

            # Rule 2: Ties are "due" based on short-term underperformance, even if long-term is okay
            if actual_tie_count_short < expected_tie_count_short * 0.8: 
                due_factor_short = (expected_tie_count_short * 0.8 - actual_tie_count_short) / expected_tie_count_short
                tie_confidence = min(85, 55 + int(due_factor_short * 100 * 0.6)) 
                if tie_confidence >= 55: return "T", tie_confidence

        # V8.2.1: Refined Rule 3: Tie Clustering - predict if a tie was *recently* seen, but not the immediate last round.
        # This prevents immediate re-prediction of Tie right after a Tie result is entered.
        if len(tie_flags) >= 2 and tie_flags[-2] == True and not tie_flags[-1]: # Tie two rounds ago, and last round was not a tie
            return "T", 60 # Moderate confidence for a potential cluster after a non-tie
        if len(tie_flags) >= 3 and tie_flags[-3] == True and not tie_flags[-2] and not tie_flags[-1]: # Tie three rounds ago, and last two rounds were non-ties
            return "T", 55 # Lower confidence, but still a potential cluster

        # Rule 4: Tie after a long streak of P/B (e.g., 10+ non-tie outcomes)
        if len(main_history_pb) >= 10 and not any(tie_flags[-10:]):
            return "T", 75 

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

        return None, None 

class AdaptiveScorer:
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy, with adaptive weighting.
    This scorer is primarily for main P/B outcomes.
    V8.0.0: Enhanced dynamic blending ratio for more accurate weighting.
    V8.1.1: More aggressive blending towards recent performance for faster adaptation.
    V8.1.2: Improved miss streak penalty logic.
    V8.1.3: Even more aggressive blending for real-time adaptation and confidence adjustment based on volatility.
    V8.1.5: Further refined weighting for AdvancedChopPredictor on specific patterns.
    V8.2.0: Ensures choppiness_rate is used for confidence adjustment.
    """
    def score(self, 
              predictions: Dict[str, Optional[MainOutcome]], 
              module_accuracies_all_time: Dict[str, float], # All-time accuracy for baseline
              module_accuracies_recent: Dict[str, float], # Recent accuracy for adaptive weighting (last 10)
              history: List[RoundResult],
              current_miss_streak: int,
              choppiness_rate: float) -> Tuple[Optional[MainOutcome], Optional[str], Optional[int], Optional[str]]: 
        
        total_score = {"P": 0.0, "B": 0.0}
        
        active_predictions = {name: pred for name, pred in predictions.items() if pred in ("P", "B")}

        if not active_predictions:
            return None, None, 0, None 

        for name, pred in active_predictions.items():
            all_time_acc_val = module_accuracies_all_time.get(name, 0.0)
            recent_acc_val = module_accuracies_recent.get(name, 0.0)

            # V8.1.3: Even more aggressive dynamic blend ratio for faster adaptation
            # Normalize accuracies to a 0-1 scale for ratio calculation
            all_time_norm = all_time_acc_val / 100.0 if all_time_acc_val > 0 else 0.5
            recent_norm = recent_acc_val / 100.0 if recent_acc_val > 0 else 0.5

            # Calculate a dynamic blend_recent_ratio (e.g., from 0.5 to 0.98)
            # Map difference from -0.2 to 0.2 (approx) to blend_recent_ratio from 0.5 to 0.98
            diff = max(-0.2, min(0.2, recent_norm - all_time_norm)) # Clamp diff to -0.2 to 0.2
            
            # Linear mapping: if diff is -0.2, ratio is 0.5. If diff is 0.2, ratio is 0.98.
            blend_recent_ratio = 0.74 + (diff * 1.2) 
            blend_recent_ratio = max(0.5, min(0.98, blend_recent_ratio)) # Ensure bounds

            weight = (recent_norm * blend_recent_ratio) + (all_time_norm * (1 - blend_recent_ratio))
            
            # V8.1.5: Give AdvancedChopPredictor a higher base weight if it makes a prediction, especially for "สามตัวตัด"
            if name == "AdvancedChop" and predictions.get(name) is not None:
                filtered_history = _get_main_outcome_history(history)
                if len(filtered_history) >= 6:
                    last_6 = filtered_history[-6:]
                    if last_6 == ["P", "P", "P", "B", "B", "B"] or last_6 == ["B", "B", "B", "P", "P", "P"]:
                        weight += 0.2 # Extra weight for "สามตัวตัด" pattern
                    else:
                        weight += 0.1 # Standard extra weight for other AdvancedChop patterns
            elif name == "ChopDetector" and predictions.get(name) is not None:
                weight += 0.1 # Standard extra weight for ChopDetector
            
            # V8.1.2: Apply miss streak penalty to module weights
            if current_miss_streak > 0:
                penalty_factor = 1.0 - (current_miss_streak * 0.05) # 5% penalty per miss
                weight *= max(0.1, penalty_factor) # Don't let weight drop below 10%
            
            total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None 

        best_prediction_outcome = max(total_score, key=total_score.get)
        
        sum_of_scores = sum(total_score.values())
        raw_confidence = (total_score[best_prediction_outcome] / sum_of_scores) * 100
        
        # Confidence capped at 95% to avoid overconfidence
        confidence = min(int(raw_confidence), 95)

        # V8.1.3: Adjust confidence based on choppiness
        # If choppiness is high (e.g., > 0.6), reduce confidence slightly
        if choppiness_rate > 0.6:
            confidence = max(50, int(confidence * (1 - (choppiness_rate - 0.6) * 0.5))) # Reduce by up to 20% if very choppy
        
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

        if len(filtered_history) >= 6: # V8.1.5: Check for "สามตัวตัด" pattern name
            last_6 = filtered_history[-6:]
            if last_6 == ["P", "P", "P", "B", "B", "B"] or last_6 == ["B", "B", "B", "P", "P", "P"]:
                return "สามตัวตัด"
        
        if len(filtered_history) >= 5:
            if filtered_history[-5] == filtered_history[-4] == filtered_history[-3] == filtered_history[-2] and filtered_history[-2] != filtered_history[-1]:
                return "มังกรตัด" 
        
        # Check for AdvancedChopPredictor patterns
        if "AdvancedChop" in predictions and predictions["AdvancedChop"] is not None:
            # If AdvancedChopPredictor made a prediction, it's likely a chop pattern
            # We can try to infer the pattern type from the recent history
            if len(filtered_history) >= 5:
                # Check for Dragon Chop pattern: XXXXXY
                if all(x == filtered_history[-6] for x in filtered_history[-6:-1]) and filtered_history[-1] != filtered_history[-6]:
                    return "มังกรตัด"
            if len(filtered_history) >= 4:
                # Check for Ping-Pong Chop pattern: XYX X
                if filtered_history[-4] != filtered_history[-3] and filtered_history[-3] == filtered_history[-2] and filtered_history[-2] == filtered_history[-1]:
                    return "ปิงปองตัด"


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

        # Global logs for all-time accuracy (NOT persistent in this version)
        # These will reset on every app redeploy/restart.
        self.module_accuracy_global_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [], "DragonTail": [], "AdvancedChop": [] 
        }
        self.tie_module_accuracy_global_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 

        # Per-shoe logs for recent accuracy and current shoe display
        self.individual_module_prediction_log_current_shoe: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [], "DragonTail": [], "AdvancedChop": [] 
        }
        self.tie_module_prediction_log_current_shoe: List[Tuple[Optional[Literal["T"]], bool]] = [] 

        # Initialize all prediction modules (P/B)
        self.rule_engine = RuleEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_scanner = TrendScanner()
        self.two_two_pattern = TwoTwoPattern()
        self.sniper_pattern = SniperPattern() 
        self.fallback_module = FallbackModule() 
        self.chop_detector = ChopDetector() 
        self.dragon_tail_detector = DragonTailDetector() 
        self.advanced_chop_predictor = AdvancedChopPredictor() 

        # Initialize side bet prediction modules
        self.tie_predictor = TiePredictor()

        self.scorer = AdaptiveScorer() 
        self.show_initial_wait_message = True
        
        # No Firestore loading/saving in this version. Data is volatile.

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
            "Pattern": self.pattern_analyzer.predict(self.history, choppiness_rate_for_trend), 
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate_for_trend), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history),
            "ChopDetector": self.chop_detector.predict(self.history),
            "DragonTail": self.dragon_tail_detector.predict(self.history),
            "AdvancedChop": self.advanced_chop_predictor.predict(self.history) 
        }
        
        for module_name, pred in current_predictions_from_modules_main.items():
            if pred is not None and pred in ("P", "B") and main_outcome in ("P", "B"):
                self.module_accuracy_global_log[module_name].append((pred, main_outcome))
                self.individual_module_prediction_log_current_shoe[module_name].append((pred, main_outcome))

        # --- Record individual side bet module predictions *before* adding the new outcome ---
        # The Tie predictor should predict based on history *before* the current round's result
        # However, due to the current UI flow, add_result happens first.
        # So, we need to make sure the TiePredictor's logic doesn't react to the *just added* result.
        # This is handled by refining Rule 3 in TiePredictor.predict()
        tie_pred_for_log, _ = self.tie_predictor.predict(self.history)

        if tie_pred_for_log is not None:
            self.tie_module_accuracy_global_log.append((tie_pred_for_log, main_outcome == "T"))
            self.tie_module_prediction_log_current_shoe.append((tie_pred_for_log, main_outcome == "T"))

        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.prediction_log.append(self.last_prediction) 
        self.result_log.append(main_outcome) 
        
        self._trim_global_logs() 
        # No Firestore saving in this version.

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop()
        
        for module_name in self.module_accuracy_global_log:
            if self.module_accuracy_global_log[module_name]:
                self.module_accuracy_global_log[module_name].pop()
        for module_name in self.individual_module_prediction_log_current_shoe:
            if self.individual_module_prediction_log_current_shoe[module_name]:
                self.individual_module_prediction_log_current_shoe[module_name].pop()
        
        if self.tie_module_accuracy_global_log:
            self.tie_module_accuracy_global_log.pop()
        if self.tie_module_prediction_log_current_shoe:
            self.tie_module_prediction_log_current_shoe.pop()
        
        # No Firestore saving in this version.


    def reset_all_data(self):
        """
        This method now explicitly resets ALL data, including global and current shoe accuracy logs.
        Use with caution, typically for a full system restart or debugging.
        """
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        
        for module_name in self.module_accuracy_global_log:
            self.module_accuracy_global_log[module_name].clear()
        self.tie_module_accuracy_global_log.clear()

        for module_name in self.individual_module_prediction_log_current_shoe:
            self.individual_module_prediction_log_current_shoe[module_name].clear()
        self.tie_module_prediction_log_current_shoe.clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True
        
        # No Firestore saving in this version.

    def start_new_shoe(self):
        """
        This method resets the current shoe's history and prediction logs,
        but retains the global historical accuracy data of the modules.
        """
        self.history.clear()
        self.prediction_log.clear()
        self.result_log.clear()
        
        for module_name in self.individual_module_prediction_log_current_shoe:
            self.individual_module_prediction_log_current_shoe[module_name].clear()
        self.tie_module_prediction_log_current_shoe.clear()

        self.last_prediction = None
        self.last_module = None
        self.show_initial_wait_message = True
        # No Firestore saving in this version.


    def _trim_global_logs(self, max_length=1000): 
        """
        Trims global accuracy logs to prevent indefinite growth.
        """
        for module_name in self.module_accuracy_global_log:
            self.module_accuracy_global_log[module_name] = self.module_accuracy_global_log[module_name][-max_length:]
        
        self.tie_module_accuracy_global_log = self.tie_module_accuracy_global_log[-max_length:]

    def _calculate_main_module_accuracy_from_log(self, log_data: List[Tuple[MainOutcome, MainOutcome]], lookback: Optional[int] = None) -> float:
        relevant_preds = log_data
        if lookback is not None:
            relevant_preds = log_data[-lookback:]
        
        wins = 0
        total_predictions = 0
        
        for predicted_val, actual_val in relevant_preds:
            if predicted_val is not None and predicted_val in ("P", "B") and actual_val in ("P", "B"):
                total_predictions += 1
                if predicted_val == actual_val:
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0

    def _calculate_side_bet_module_accuracy_from_log(self, log_data: List[Tuple[Optional[Any], bool]], lookback: Optional[int] = None) -> float:
        relevant_log = log_data
        if lookback is not None:
            relevant_log = log_data[-lookback:]
        
        wins = 0
        total_predictions = 0
        
        for predicted_val, actual_flag in relevant_log:
            if predicted_val is not None: 
                total_predictions += 1
                if predicted_val == "T" and actual_flag: 
                    wins += 1
        
        return (wins / total_predictions) * 100 if total_predictions > 0 else 0.0


    def get_module_accuracy_all_time(self) -> Dict[str, float]:
        """
        Calculates all-time accuracy from global logs.
        """
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy_from_log(self.module_accuracy_global_log[module_name], lookback=None)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_accuracy_global_log, lookback=None)

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        """
        Calculates recent accuracy from current shoe logs.
        """
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop"] 
        for module_name in main_modules:
            accuracy_results[module_name] = self._calculate_main_module_accuracy_from_log(self.individual_module_prediction_log_current_shoe[module_name], lookback)
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_prediction_log_current_shoe, lookback)

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        all_known_modules_for_norm = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop", "Tie"] 
        
        if not acc:
            return {name: 0.5 for name in all_known_modules_for_norm}
        
        active_main_accuracies = {k: v for k, v in acc.items() if k in ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "ChopDetector", "DragonTail", "AdvancedChop"] and v > 0} 
        
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
            "ChopDetector": self.chop_detector,
            "DragonTail": self.dragon_tail_detector, 
            "AdvancedChop": self.advanced_chop_predictor 
        }
        
        module_scores: Dict[str, float] = {}

        min_history_for_module = 4 
        
        for name in modules_to_check.keys():
            if name == "Fallback": continue 
            
            log_for_module = self.individual_module_prediction_log_current_shoe.get(name, [])
            
            relevant_preds = log_for_module
            if lookback is not None:
                relevant_preds = log_for_module[-lookback:]
            
            wins = 0
            total_predictions = 0
            
            for predicted_val, actual_val in relevant_preds:
                if predicted_val is not None and predicted_val in ("P", "B") and actual_val in ("P", "B"):
                    total_predictions += 1
                    if predicted_val == actual_val:
                        wins += 1
            
            if total_predictions > 0:
                module_scores[name] = wins / total_predictions
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


    def calculate_miss_streak(self) -> int:
        """
        Calculates the current consecutive miss streak for main P/B predictions.
        """
        streak = 0
        
        for pred, actual in zip(reversed(self.prediction_log), reversed(self.result_log)):
            if pred is None or actual not in ("P", "B") or pred not in ("P", "B"):
                continue 
            
            if pred != actual:
                streak += 1
            else:
                break 
        return streak


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

        # V8.1.1: Lowered MIN_HISTORY_FOR_PREDICTION for earlier predictions
        MIN_HISTORY_FOR_PREDICTION = 15 
        
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
            "Pattern": self.pattern_analyzer.predict(self.history, choppiness_rate), 
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history),
            "ChopDetector": self.chop_detector.predict(self.history),
            "DragonTail": self.dragon_tail_detector.predict(self.history),
            "AdvancedChop": self.advanced_chop_predictor.predict(self.history) 
        }
        
        module_accuracies_all_time = self.get_module_accuracy_all_time()
        module_accuracies_recent_10 = self.get_module_accuracy_recent(10) 
        module_accuracies_recent_20 = self.get_module_accuracy_recent(20) 

        final_prediction_main, source_module_name_main, confidence_main, pattern_code_main = \
            self.scorer.score(predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history, current_miss_streak, choppiness_rate) 

        if final_prediction_main is not None and confidence_main is not None and confidence_main < MIN_DISPLAY_CONFIDENCE:
            final_prediction_main = None
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None

        # V8.1.3: Enhanced Miss Streak Recovery Logic
        if current_miss_streak >= 3:
            # If the main prediction is not confident enough OR it's None
            if final_prediction_main is None or (confidence_main is not None and confidence_main < MIN_DISPLAY_CONFIDENCE):
                filtered_history_pb = _get_main_outcome_history(self.history)
                
                if len(filtered_history_pb) >= 2 and len(self.prediction_log) >= 1:
                    last_actual_outcome = filtered_history_pb[-1]
                    # Check if the last actual outcome was a miss and if it started a new mini-streak
                    # This means the previous prediction was wrong, and the last two actual outcomes are the same
                    if self.prediction_log[-1] is not None and last_actual_outcome != self.prediction_log[-1] and filtered_history_pb[-1] == filtered_history_pb[-2]:
                        final_prediction_main = last_actual_outcome # Predict continuation of this new mini-streak
                        source_module_name_main = "Recovery-NewStreak"
                        confidence_main = 70 # Higher confidence for detected new streak after a miss
                    else:
                        # If no clear new streak, try to find the best recent module
                        best_module_for_recovery = self.get_best_recent_module()
                        if best_module_for_recovery and predictions_from_modules.get(best_module_for_recovery) in ("P", "B"):
                            final_prediction_main = predictions_from_modules[best_module_for_recovery]
                            source_module_name_main = f"{best_module_for_recovery}-Recovery"
                            confidence_main = 60 # Moderate confidence for module-based recovery
                        else:
                            # As a last resort, use Fallback if nothing else is confident
                            final_prediction_main = self.fallback_module.predict(self.history)
                            source_module_name_main = "Fallback-Recovery"
                            confidence_main = 50 # Base confidence for pure fallback


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

        if self.tie_module_prediction_log_current_shoe: 
            # V8.2.1: This logic is now primarily for adjusting confidence *down* if previous Tie prediction was wrong
            last_logged_tie_pred, last_actual_is_tie = self.tie_module_prediction_log_current_shoe[-1]
            if last_logged_tie_pred == "T" and not last_actual_is_tie:
                if tie_conf_raw is not None:
                    tie_conf_raw = max(0, tie_conf_raw - 30) 
                
                if len(self.tie_module_prediction_log_current_shoe) >= 2:
                    prev_logged_tie_pred, prev_actual_is_tie = self.tie_module_prediction_log_current_shoe[-2]
                    if prev_logged_tie_pred == "T" and not prev_actual_is_tie:
                        tie_conf_raw = 0 
        
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
                if len(self.tie_module_prediction_log_current_shoe) >= SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT:
                    tie_recent_acc = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_prediction_log_current_shoe, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
                else:
                    tie_recent_acc = 0 
                
                if tie_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                    is_tie_sniper_opportunity = True

        return (
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_miss_streak, is_sniper_opportunity_main,
            tie_prediction, tie_confidence, 
            is_tie_sniper_opportunity 
        )

# --- Streamlit UI Code ---

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle V8.2.1", layout="centered") # Updated version to V8.2.1

# --- Custom CSS for Styling ---
st.markdown("""
<style>
/* Import Sarabun font from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

html, body, [class*="st-emotion"] { /* Target Streamlit's main content div classes */
    font-family: 'Sarabun', sans-serif !important;
}
.big-title {
    font-size: 28px;
    text-align: center;
    font-weight: bold;
    color: #FF4B4B; /* Streamlit's default primary color */
    margin-bottom: 20px;
}
.predict-box {
    padding: 15px;
    background-color: #262730; /* Darker background for the box */
    border-radius: 12px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    text-align: center; /* Center content inside prediction box */
}
.predict-box h2 {
    margin: 10px 0;
    font-size: 40px;
    font-weight: bold;
}
.predict-box b {
    color: #FFD700; /* Gold color for emphasis */
}
.predict-box .st-emotion-cache-1c7y2vl { /* Target Streamlit's caption */
    font-size: 14px; /* This is the target size for module/pattern/confidence */
    color: #BBBBBB;
}

/* Miss Streak warning text */
.st-emotion-cache-1f1d6zpt p, .st-emotion-cache-1s04v0m p { /* Target text inside warning/error boxes */
    font-size: 14px; /* Reduced font size for miss streak text */
}


.big-road-container {
    width: 100%;
    overflow-x: auto; /* Allows horizontal scrolling if many columns */
    padding: 8px 0;
    background: #1A1A1A; /* Slightly darker background for the road */
    border-radius: 8px;
    white-space: nowrap; /* Keeps columns in a single line */
    display: flex; /* Use flexbox for columns */
    flex-direction: row; /* Display columns from left to right */
    align-items: flex-start; /* Align columns to the top */
    min-height: 140px; /* Adjusted minimum height for the road */
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.3);
}
.big-road-column {
    display: inline-flex; /* Use inline-flex for vertical stacking within column */
    flex-direction: column;
    margin-right: 2px; 
    border-right: 1px solid rgba(255,255,255,0.1); 
    padding-right: 2px; 
}
.big-road-cell {
    width: 20px; /* Further reduced size for smaller emoji */
    height: 20px; /* Further reduced size for smaller emoji */
    text-align: center;
    line-height: 20px; /* Adjusted line-height for new size */
    font-size: 14px; /* Smaller font for emojis */
    margin-bottom: 1px; /* Reduced margin between cells */
    border-radius: 50%; /* Make cells round */
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
    color: white; /* Default text color for ties */
    position: relative; /* For positioning tie count */
}
/* Specific colors for P, B, T */
.big-road-cell.P { background-color: #007BFF; } /* Blue for Player */
.big-road-cell.B { background-color: #DC3545; } /* Red for Banker */
.big-road-cell.T { background-color: #6C757D; } /* Gray for Tie (though not directly used for main cells) */
.big-road-cell .tie-count {
    font-size: 9px; /* Slightly smaller font for tie count */
    position: absolute;
    bottom: -1px; /* Adjusted position */
    right: -1px; /* Adjusted position */
    background-color: #FFD700; /* Gold background for prominence */
    color: #333; /* Dark text for contrast */
    border-radius: 50%;
    padding: 1px 3px; /* Reduced padding */
    line-height: 1;
    min-width: 14px; /* Ensure minimum width for single digit */
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2); /* Slightly smaller shadow */
}
/* Styling for Natural indicator in Big Road (New for V6.5) */
.natural-indicator {
    position: absolute;
    font-size: 8px; /* Smaller font for indicators */
    font-weight: bold;
    color: white;
    line-height: 1;
    padding: 1px 2px;
    border-radius: 3px;
    z-index: 10;
    background-color: #4CAF50; /* Green for Natural */
    top: -2px;
    right: -2px;
}


/* Button styling */
.stButton>button {
    width: 100%;
    border-radius: 8px;
    font-size: 18px;
    font-weight: bold;
    padding: 10px 0;
    margin-bottom: 10px;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
}
/* Specific button colors */
#btn_P button { background-color: #007BFF; color: white; border: none; }
#btn_B button { background-color: #DC3545; color: white; border: none; }
#btn_T button { background-color: #6C757D; color: white; border: none; }
/* Checkbox styling adjustments */
.stCheckbox > label {
    padding: 8px 10px; /* Adjust padding for better click area */
    border: 1px solid #495057;
    border-radius: 8px;
    background-color: #343A40;
    color: white;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 10px;
    display: flex; /* Use flex to align checkbox and text */
    align-items: center;
    justify-content: center; /* Center content horizontally */
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}
.stCheckbox > label:hover {
    background-color: #495057;
    transform: translateY(-2px);
    box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
}
.stCheckbox > label > div:first-child { /* The actual checkbox input */
    margin-right: 8px; /* Space between checkbox and text */
}
/* Style for checked checkboxes */
.stCheckbox > label[data-checked="true"] {
    background-color: #007BFF; /* Example color for checked */
    border-color: #007BFF;
}


.stButton button[kind="secondary"] { /* For control buttons */
    background-color: #343A40;
    color: white;
    border: 1px solid #495057;
}
.stButton button[kind="secondary"]:hover {
    background-color: #495057;
}

/* Warning/Error messages */
.st-emotion-cache-1f1d6zpt { /* Target Streamlit warning box */
    background-color: #FFC10720; /* Light yellow with transparency */
    border-left: 5px solid #FFC107;
    color: #FFC107;
}

.st-emotion-cache-1s04v0m { /* Target Streamlit error box */
    background-color: #DC354520; /* Light red with transparency */
    border-left: 5px solid #DC3545;
    color: #DC3545;
}

.st-emotion-cache-13ln4z2 { /* Target Streamlit info box */
    background-color: #17A2B820; /* Light blue with transparency */
    border-left: 5px solid #17A2B8;
    color: #17A2B8;
}

/* Accuracy by Module section */
h3 { /* Target h3 for "ความแม่นยำรายโมดูล" */
    font-size: 12px !important; /* Force this size */
    margin-top: 10px !important; 
    margin-bottom: 3px !important; 
}
/* Target for the custom class used for accuracy items */
.accuracy-item { 
    font-size: 10px !important; /* Force this size */
    margin-bottom: 1px !important; 
}

/* Sniper message styling */
.sniper-message {
    background-color: #4CAF50; /* Green background */
    color: white;
    padding: 10px;
    border-radius: 8px;
    font-weight: bold;
    text-align: center;
    margin-top: 15px;
    margin-bottom: 15px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    animation: pulse 1.5s infinite; /* Add a subtle pulse animation */
}

/* NEW: Side Bet Sniper message styling */
.side-bet-sniper-message {
    background-color: #007bff; /* Blue background for side bet sniper */
    color: white;
    padding: 8px;
    border-radius: 6px;
    font-weight: bold;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 10px;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
    animation: pulse 1.5s infinite; /* Keep pulse animation */
    font-size: 14px; /* Smaller font than main sniper */
}


@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.02); opacity: 0.9; }
    100% { transform: scale(1); opacity: 1; }
}


hr {
    border-top: 1px solid rgba(255,255,255,0.1);
    margin: 25px 0;
}
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'oracle' not in st.session_state:
    st.session_state.oracle = OracleBrain()
if 'prediction' not in st.session_state: 
    st.session_state.prediction = None
if 'source' not in st.session_state:
    st.session_state.source = None
if 'confidence' not in st.session_state:
    st.session_state.confidence = None
if 'pattern_name' not in st.session_state:
    st.session_state.pattern_name = None
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = False
if 'is_sniper_opportunity_main' not in st.session_state: 
    st.session_state.is_sniper_opportunity_main = False
if 'show_debug_info' not in st.session_state: 
    st.session_state.show_debug_info = False

if 'tie_prediction' not in st.session_state:
    st.session_state.tie_prediction = None
if 'tie_confidence' not in st.session_state: 
    st.session_state.tie_confidence = None

if 'is_tie_sniper_opportunity' not in st.session_state:
    st.session_state.is_tie_sniper_opportunity = False


# --- UI Callback Functions ---
def handle_click(main_outcome_str: MainOutcome): 
    """
    Handles button clicks for P, B, T outcomes.
    Adds the result to OracleBrain and updates all predictions.
    """
    is_any_natural = False 

    st.session_state.oracle.add_result(main_outcome_str, is_any_natural)
    
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity) = st.session_state.oracle.predict_next() 
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 
    
    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf

    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    
    pattern_names = {
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
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "มังกรตัด": "มังกรตัด", # Existing pattern for chop after streak
        "ปิงปองตัด": "ปิงปองตัด" # New pattern for chop after ping-pong
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) >= 15: # V8.1.1: Lowered for earlier predictions
        st.session_state.initial_shown = True 

    st.query_params["_t"] = f"{time.time()}"


def handle_remove():
    """
    Handles removing the last added result.
    """
    st.session_state.oracle.remove_last()
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity) = st.session_state.oracle.predict_next() 
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 

    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    
    pattern_names = {
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
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "มังกรตัด": "มังกรตัด", # Existing pattern for chop after streak
        "ปิงปองตัด": "ปิงปองตัด" # New pattern for chop after ping-pong
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) < 15: # V8.1.1: Lowered for earlier predictions
        st.session_state.initial_shown = False
    
    st.query_params["_t"] = f"{time.time()}"


def handle_start_new_shoe():
    """
    Handles starting a new shoe, resetting only the current shoe's history.
    """
    st.session_state.oracle.start_new_shoe()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.initial_shown = False 
    st.session_state.is_sniper_opportunity_main = False 
    
    st.session_state.tie_prediction = None
    st.session_state.tie_confidence = None

    st.session_state.is_tie_sniper_opportunity = False

    st.query_params["_t"] = f"{time.time()}"

# --- Header ---
st.markdown('<div class="big-title">🔮 Oracle V8.2.1</div>', unsafe_allow_html=True) # Updated version to V8.2.1

# --- Prediction Output Box (Main Outcome) ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำทำนายหลัก:</b>", unsafe_allow_html=True) 

if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(st.session_state.prediction, "❓")
    st.markdown(f"<h2>{emoji} <b>{st.session_state.prediction}</b></h2>", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence:.1f}%") 
else:
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    main_history_len = p_count + b_count
    miss = st.session_state.oracle.calculate_miss_streak()

    if main_history_len < 15 and not st.session_state.initial_shown: # V8.1.1: Lowered for earlier predictions
        st.warning(f"⚠️ กำลังเรียนรู้... รอข้อมูลครบ 15 ตา (P/B) ก่อนเริ่มทำนาย (ปัจจุบัน {main_history_len} ตา)") # V8.1.1: Updated message
    elif miss >= 6:
        st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด) - โปรดป้อนข้อมูลต่อเพื่อให้ระบบเรียนรู้และฟื้นตัว") # V8.1.1: Updated message
    else:
        st.info("⏳ กำลังวิเคราะห์ข้อมูล... ความมั่นใจยังไม่สูงพอที่จะทำนาย - โปรดป้อนข้อมูลต่อ") # V8.1.1: Updated message

st.markdown("</div>", unsafe_allow_html=True)

# --- Sniper Opportunity Message (Main Outcome) ---
if st.session_state.is_sniper_opportunity_main: 
    st.markdown("""
        <div class="sniper-message">
            🎯 SNIPER! มั่นใจเป็นพิเศษ
        </div>
    """, unsafe_allow_html=True)

# --- Side Bet Prediction Display ---
if st.session_state.tie_prediction and st.session_state.tie_confidence is not None:
    st.markdown("<b>📍 คำทำนายเสริม:</b>", unsafe_allow_html=True) 
    col_side1, col_side_empty = st.columns(2) 
    with col_side1:
        st.markdown(f"<p style='text-align:center; color:#6C757D; font-weight:bold;'>⚪ เสมอ</p>", unsafe_allow_html=True)
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.tie_confidence:.1f}%")
        if st.session_state.is_tie_sniper_opportunity:
            st.markdown("""
                <div class="side-bet-sniper-message">
                    🎯 SNIPER เสมอ!
                </div>
            """, unsafe_allow_html=True)
    with col_side_empty:
        pass 

st.markdown("<hr>", unsafe_allow_html=True)

# --- Miss Streak Warning ---
miss = st.session_state.oracle.calculate_miss_streak()
st.warning(f"❌ แพ้ติดกัน: {miss} ครั้ง")
if miss == 3:
    st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
elif miss >= 6:
    st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")

# --- Big Road Display ---
st.markdown("<hr>", unsafe_allow_html=True) 
st.markdown("<b>🕒 Big Road:</b>", unsafe_allow_html=True)

history_results = st.session_state.oracle.history 

if history_results:
    max_row = 6
    columns = []
    current_col = []
    last_non_tie_result = None
    
    for i, round_result in enumerate(history_results): 
        main_outcome = round_result.main_outcome
        is_any_natural = round_result.is_any_natural 

        if main_outcome == "T":
            if current_col:
                last_cell_idx = len(current_col) - 1
                current_col[last_cell_idx] = (current_col[last_cell_idx][0], current_col[last_cell_idx][1] + 1,
                                               current_col[last_cell_idx][2]) 
            elif columns:
                last_col_idx = len(columns) - 1
                if columns[last_col_idx]:
                    last_cell_in_prev_col_idx = len(columns[last_col_idx]) - 1
                    columns[last_col_idx][last_cell_in_prev_col_idx] = (
                        columns[last_col_idx][last_cell_in_prev_col_idx][0],
                        columns[last_col_idx][last_cell_in_prev_col_idx][1] + 1,
                        columns[last_col_idx][last_cell_in_prev_col_idx][2]
                    )
            continue
        
        if main_outcome == last_non_tie_result:
            if len(current_col) < max_row:
                current_col.append((main_outcome, 0, is_any_natural)) 
            else:
                columns.append(current_col)
                current_col = [(main_outcome, 0, is_any_natural)] 
        else:
            if current_col:
                columns.append(current_col)
            current_col = [(main_outcome, 0, is_any_natural)] 
            last_non_tie_result = main_outcome
            
    if current_col:
        columns.append(current_col)

    MAX_DISPLAY_COLUMNS = 14 
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:] 

    big_road_html = f"<div class='big-road-container' id='big-road-container-unique'>"
    for col in columns:
        big_road_html += "<div class='big-road-column'>"
        for cell_result, tie_count, natural_flag in col: 
            emoji = "🔵" if cell_result == "P" else "🔴"
            tie_html = f"<span class='tie-count'>{tie_count}</span>" if tie_count > 0 else ""
            
            natural_indicator = f"<span class='natural-indicator'>N</span>" if natural_flag else ""

            big_road_html += f"<div class='big-road-cell {cell_result}'>{emoji}{tie_html}{natural_indicator}</div>" 
        big_road_html += "</div>" 
    big_road_html += "</div>" 
    
    st.markdown(big_road_html, unsafe_allow_html=True)

else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons (Main Outcomes) ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<b>ป้อนผล:</b>", unsafe_allow_html=True) 

col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_P")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_B")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_T")

# --- Control Buttons ---
st.markdown("<hr>", unsafe_allow_html=True)
col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ลบรายการล่าสุด", on_click=handle_remove)
with col5:
    st.button("▶️ เริ่มขอนใหม่", on_click=handle_start_new_shoe) # Changed button label and function call

# --- Debugging Toggle ---
st.markdown("<hr>", unsafe_allow_html=True)
st.session_state.show_debug_info = st.checkbox("แสดงข้อมูล Debugging")

# --- Conditional Debugging Output ---
if st.session_state.show_debug_info:
    st.markdown("<h3>⚙️ ข้อมูล Debugging (สำหรับนักพัฒนา)</h3>", unsafe_allow_html=True)
    st.write(f"ความยาวประวัติ P/B: {len(_get_main_outcome_history(st.session_state.oracle.history))}") 
    st.write(f"ผลทำนายหลัก (prediction): {st.session_state.prediction}")
    st.write(f"โมดูลที่ใช้ (source): {st.session_state.source}")
    st.write(f"ความมั่นใจ (confidence): {st.session_state.confidence}")
    st.write(f"แพ้ติดกัน (miss streak): {st.session_state.oracle.calculate_miss_streak()}")
    st.write(f"อัตราความผันผวน (Choppiness Rate): {st.session_state.oracle._calculate_choppiness_rate(st.session_state.oracle.history, 20):.2f}") 
    st.write(f"Sniper หลัก: {st.session_state.is_sniper_opportunity_main}")
    st.write(f"ทำนายเสมอ: {st.session_state.tie_prediction}, ความมั่นใจเสมอ: {st.session_state.tie_confidence}, Sniper เสมอ: {st.session_state.is_tie_sniper_opportunity}") 
    st.write("---") 


# --- Accuracy by Module ---
st.markdown("<h3>📈 ความแม่นยำรายโมดูล</h3>", unsafe_allow_html=True) 

all_time_accuracies = st.session_state.oracle.get_module_accuracy_all_time()
recent_10_accuracies = st.session_state.oracle.get_module_accuracy_recent(10)
recent_20_accuracies = st.session_state.oracle.get_module_accuracy_recent(20)

if all_time_accuracies:
    st.markdown("<h4>ความแม่นยำ (All-Time)</h4>", unsafe_allow_html=True)
    sorted_module_names = sorted(all_time_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) 
    for name in sorted_module_names:
        acc = all_time_accuracies[name]
        st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    main_history_len = p_count + b_count

    if main_history_len >= 10: 
        st.markdown("<h4>ความแม่นยำ (10 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_10 = sorted(recent_10_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) 
        for name in sorted_module_names_recent_10:
            acc = recent_10_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)

    if main_history_len >= 20: 
        st.markdown("<h4>ความแม่นยำ (20 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_20 = sorted(recent_20_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) 
        for name in sorted_module_names_recent_20:
            acc = recent_20_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลความแม่นยำ")

