# streamlit_app.py (Oracle V10.2.0 - Smart Recommendation Engine with Advanced Statistical & Professional Road Analysis - Ultra Compact UI)
import streamlit as st
import time 
from typing import List, Optional, Literal, Tuple, Dict, Any
import random
from dataclasses import dataclass
import json 

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

def _opposite_outcome(outcome: MainOutcome) -> MainOutcome:
    """Returns the opposite of a P or B outcome."""
    if outcome == "P":
        return "B"
    elif outcome == "B":
        return "P"
    return outcome # Should not happen for P/B inputs

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
        
        # V8.2.0: Dynamic pattern window - adjust iteration based on choppiness.
        # If very choppy, prioritize shorter patterns (e.g., 3-length patterns first).
        # If very streaky, prioritize longer patterns (e.g., 6-length patterns first).
        if choppiness_rate > 0.7: 
            lengths_to_check = range(3, 7) # Check 3-length first, then 4, 5, 6
        # If very streaky, prioritize longer patterns (e.g., 6-length patterns first).
        elif choppiness_rate < 0.3: 
            lengths_to_check = range(6, 2, -1) # Check 6-length first, then 5, 4, 3
        # Moderate choppiness, default to checking longer patterns first.
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
    Provides a more strategic prediction if no other module can make a prediction,
    especially during a miss streak.
    V8.8.0: Enhanced to be more adaptive during high miss streaks.
    """
    def predict(self, history: List[RoundResult], miss_streak: int) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 2:
            return random.choice(["P", "B"]) # Fallback to random if not enough history

        last_outcome = filtered_history[-1]
        second_last_outcome = filtered_history[-2]

        if miss_streak >= 4: # More aggressive fallback when miss streak is high
            # If it's a streak (e.g., PP or BB), try to chop it more aggressively
            if last_outcome == second_last_outcome:
                return _opposite_outcome(last_outcome)
            # If it's alternating (e.g., PB or BP), try to continue the alternation
            else:
                return last_outcome
        
        # Default behavior for lower miss streaks
        if last_outcome == second_last_outcome: # It's a streak (e.g., PP or BB)
            return _opposite_outcome(last_outcome) # Predict to chop the streak (e.g., for PP, predict B)
        else: # It's alternating (e.g., PB or BP)
            return last_outcome # Predict to continue the alternating pattern (e.g., for PB, predict P)

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

class ThreeChopPredictor:
    """
    V8.3.3: Dedicated module for "Three-Chop" pattern (XXX YYY).
    Predicts the opposite outcome after 3 consecutive identical outcomes.
    """
    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 3:
            return None
        
        last_three = filtered_history[-3:]
        if last_three[0] == last_three[1] == last_three[2]:
            return _opposite_outcome(last_three[0]) # Predict the chop
        return None

# --- Derived Road Analyzer (V8.8.0 Robustness, V8.9.0 Enhanced for Visualization) ---
class DerivedRoadAnalyzer:
    """
    Analyzes Big Road to derive Big Eye Boy, Small Road, and Cockroach Pig patterns
    and makes predictions based on their trends.
    V8.8.0: Further robustness improvements for derived road calculation.
    V8.9.0: Enhanced to provide the full derived road matrix for visualization,
            and more consistent "simulated" predictions.
    """
    def _build_big_road_matrix(self, history_pb: List[MainOutcome]) -> List[List[Optional[MainOutcome]]]:
        """
        Builds a matrix representation of the Big Road.
        Each column represents a streak.
        V8.8.0: Ensures matrix is built correctly for all valid histories.
        """
        if not history_pb:
            return []

        matrix: List[List[Optional[MainOutcome]]] = []
        current_col: List[Optional[MainOutcome]] = []
        last_outcome = None

        for outcome in history_pb:
            if outcome != last_outcome and last_outcome is not None:
                matrix.append(current_col)
                current_col = []
            
            current_col.append(outcome)
            last_outcome = outcome
        
        if current_col:
            matrix.append(current_col)
        
        # Pad columns to a minimum height for consistent indexing (6 rows standard)
        max_rows = 6 
        padded_matrix = []
        for col in matrix:
            padded_col = col + [None] * (max_rows - len(col))
            padded_matrix.append(padded_col)

        return padded_matrix

    def _get_big_eye_boy_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Big Eye Boy value for a given cell (col_idx, row_idx) in the Big Road matrix.
        V8.8.0: Refined logic for more consistent predictions.
        """
        # Ensure the current cell (col_idx, row_idx) itself is valid and not None
        if col_idx >= len(matrix) or row_idx >= len(matrix[col_idx]) or matrix[col_idx][row_idx] is None:
            return None
        
        # Big Eye Boy starts from the 2nd column (index 1) of the Big Road.
        if col_idx < 1:
            return None

        # Rule 1: Horizontal comparison (two columns back in the same row)
        if (col_idx - 2) >= 0 and row_idx < len(matrix[col_idx-2]) and matrix[col_idx-2][row_idx] is not None:
            if matrix[col_idx-2][row_idx] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)
        
        # Rule 2: Vertical comparison (one cell up in the same column)
        elif row_idx >= 1 and row_idx - 1 < len(matrix[col_idx]) and matrix[col_idx][row_idx-1] is not None:
            if matrix[col_idx][row_idx-1] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)
        
        # V8.8.0: Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 2 and len(matrix[col_idx-2]) == 1:
            return "P" # Blue (indicates a chop/alternation in the derived road)
        
        return None

    def _get_small_road_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Small Road value for a given cell (col_idx, row_idx) in the Big Road matrix.
        V8.8.0: Refined logic for more consistent predictions.
        """
        # Ensure the current cell (col_idx, row_idx) itself is valid and not None
        if col_idx >= len(matrix) or row_idx >= len(matrix[col_idx]) or matrix[col_idx][row_idx] is None:
            return None

        # Small Road starts from 3rd column (index 2) of Big Road.
        if col_idx < 2:
            return None
        
        # Rule 1: Horizontal comparison (one column back in the same row)
        if (col_idx - 1) >= 0 and row_idx < len(matrix[col_idx-1]) and matrix[col_idx-1][row_idx] is not None:
            if matrix[col_idx-1][row_idx] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)
        
        # Rule 2: Vertical comparison (one cell up in the column two back)
        elif row_idx >= 1 and (col_idx - 2) >= 0 and row_idx - 1 < len(matrix[col_idx-2]) and matrix[col_idx-2][row_idx-1] is not None:
            if matrix[col_idx-2][row_idx-1] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)

        # V8.8.0: Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 1 and len(matrix[col_idx-1]) == 1:
            return "P" # Blue (indicates a chop/alternation in the derived road)

        return None

    def _get_cockroach_pig_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Cockroach Pig value for a given cell (col_idx, row_idx) in the Big Road matrix.
        V8.8.0: Refined logic for more consistent predictions.
        """
        # Ensure the current cell (col_idx, row_idx) itself is valid and not None
        if col_idx >= len(matrix) or row_idx >= len(matrix[col_idx]) or matrix[col_idx][row_idx] is None:
            return None

        # Cockroach Pig starts from 4th column (index 3) of Big Road.
        if col_idx < 3:
            return None
        
        # Rule 1: Horizontal comparison (three columns back in the same row)
        if (col_idx - 3) >= 0 and row_idx < len(matrix[col_idx-3]) and matrix[col_idx-3][row_idx] is not None:
            if matrix[col_idx-3][row_idx] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)
        
        # Rule 2: Vertical comparison (one cell up in the column one back)
        elif row_idx >= 1 and (col_idx - 1) >= 0 and row_idx - 1 < len(matrix[col_idx-1]) and matrix[col_idx-1][row_idx-1] is not None:
            if matrix[col_idx-1][row_idx-1] == matrix[col_idx][row_idx]:
                return "B" # Red (Follows pattern)
            else:
                return "P" # Blue (Chops pattern)

        # V8.8.0: Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 1 and len(matrix[col_idx-1]) == 1: 
            return "P" # Blue (indicates a chop/alternation in the derived road)
        
        return None

    def predict(self, history: List[RoundResult]) -> Dict[str, Optional[MainOutcome]]:
        """
        Simulates predictions for the next P or B to determine derived road values.
        """
        predictions: Dict[str, Optional[MainOutcome]] = {}
        
        history_pb = _get_main_outcome_history(history)
        
        if not history_pb: 
            return {"BigEyeBoy": None, "SmallRoad": None, "CockroachPig": None}

        matrix = self._build_big_road_matrix(history_pb)
        
        # Simulate the next outcome (P or B) to see what the derived roads would predict.
        
        # Scenario 1: Next is Player (P)
        simulated_history_p = history_pb + ["P"]
        simulated_matrix_p = self._build_big_road_matrix(simulated_history_p)
        
        sim_last_col_idx_p = len(simulated_matrix_p) - 1
        sim_last_row_idx_p = len(simulated_matrix_p[sim_last_col_idx_p]) - 1
        
        big_eye_p = self._get_big_eye_boy_value(simulated_matrix_p, sim_last_col_idx_p, sim_last_row_idx_p)
        small_road_p = self._get_small_road_value(simulated_matrix_p, sim_last_col_idx_p, sim_last_row_idx_p)
        cockroach_p = self._get_cockroach_pig_value(simulated_matrix_p, sim_last_col_idx_p, sim_last_row_idx_p)

        # Scenario 2: Next is Banker (B)
        simulated_history_b = history_pb + ["B"]
        simulated_matrix_b = self._build_big_road_matrix(simulated_history_b)

        sim_last_col_idx_b = len(simulated_matrix_b) - 1
        sim_last_row_idx_b = len(simulated_matrix_b[sim_last_col_idx_b]) - 1

        big_eye_b = self._get_big_eye_boy_value(simulated_matrix_b, sim_last_col_idx_b, sim_last_row_idx_b)
        small_road_b = self._get_small_road_value(simulated_matrix_b, sim_last_col_idx_b, sim_last_row_idx_b)
        cockroach_b = self._get_cockroach_pig_value(simulated_matrix_b, sim_last_col_idx_b, sim_last_row_idx_b)

        if big_eye_p == "B" and big_eye_b == "P": 
            predictions["BigEyeBoy"] = "P"
        elif big_eye_p == "P" and big_eye_b == "B": 
            predictions["BigEyeBoy"] = "B"
        else:
            predictions["BigEyeBoy"] = None 

        if small_road_p == "B" and small_road_b == "P": 
            predictions["SmallRoad"] = "P"
        elif small_road_p == "P" and small_road_b == "B": 
            predictions["SmallRoad"] = "B"
        else:
            predictions["SmallRoad"] = None

        if cockroach_p == "B" and cockroach_b == "P": 
            predictions["CockroachPig"] = "P"
        elif cockroach_p == "P" and cockroach_b == "B": 
            predictions["CockroachPig"] = "B"
        else:
            predictions["CockroachPig"] = None

        return predictions
    
    def get_full_derived_road_matrices(self, history: List[RoundResult]) -> Dict[str, List[List[Optional[MainOutcome]]]]:
        """
        Generates the full derived road matrices for visualization.
        V8.9.0: New method to get the actual derived road values, not just predictions.
        """
        history_pb = _get_main_outcome_history(history)
        if len(history_pb) < 4: # Need enough history to start drawing derived roads
            return {"BigEyeBoyMatrix": [], "SmallRoadMatrix": [], "CockroachPigMatrix": []}

        big_road_matrix = self._build_big_road_matrix(history_pb)
        
        big_eye_boy_matrix: List[List[Optional[MainOutcome]]] = []
        small_road_matrix: List[List[Optional[MainOutcome]]] = []
        cockroach_pig_matrix: List[List[Optional[MainOutcome]]] = []

        # Iterate through the big_road_matrix to build derived road matrices
        # Note: Derived roads are offset from Big Road.
        # Big Eye Boy starts from (1,0) of Big Road.
        # Small Road starts from (2,0) of Big Road.
        # Cockroach Pig starts from (3,0) of Big Road.

        max_rows = 6 # Standard height for derived road display

        for col_idx in range(len(big_road_matrix)):
            beb_col: List[Optional[MainOutcome]] = []
            sr_col: List[Optional[MainOutcome]] = []
            cp_col: List[Optional[MainOutcome]] = []
            
            for row_idx in range(max_rows): # Iterate through rows
                beb_val = self._get_big_eye_boy_value(big_road_matrix, col_idx, row_idx)
                sr_val = self._get_small_road_value(big_road_matrix, col_idx, row_idx)
                cp_val = self._get_cockroach_pig_value(big_road_matrix, col_idx, row_idx)
                
                beb_col.append(beb_val)
                sr_col.append(sr_val)
                cp_col.append(cp_val)
            
            big_eye_boy_matrix.append(beb_col)
            small_road_matrix.append(sr_col)
            cockroach_pig_matrix.append(cp_col)

        return {
            "BigEyeBoyMatrix": big_eye_boy_matrix,
            "SmallRoadMatrix": small_road_matrix,
            "CockroachPigMatrix": cockroach_pig_matrix
        }

# --- NEW: Statistical Analyzer (V10.0.0) ---
class StatisticalAnalyzer:
    """
    Analyzes sequences of past outcomes to predict the next outcome based on conditional probabilities.
    Learns from the global history log.
    """
    def __init__(self):
        # Stores counts of sequences and their follow-up outcomes
        # Format: { "PBP": {"P": 5, "B": 2}, ... } meaning "PBP" was followed by P 5 times, B 2 times
        self.sequence_outcomes: Dict[str, Dict[MainOutcome, int]] = {}

    def update_sequence_history(self, history_pb: List[MainOutcome]):
        """
        Updates the internal sequence history based on the latest outcome.
        Considers sequences of length 2 to 5.
        """
        if len(history_pb) < 2: # Need at least 2 outcomes to form a 1-length sequence + 1 follow-up
            return

        for length in range(2, min(len(history_pb), 6)): # Sequences from length 2 up to 5
            if len(history_pb) >= length + 1:
                sequence = "".join(history_pb[-(length + 1):-1]) # e.g., for length 2, PBP -> PB
                follow_up_outcome = history_pb[-1] # PBP -> P

                if sequence not in self.sequence_outcomes:
                    self.sequence_outcomes[sequence] = {"P": 0, "B": 0}
                
                if follow_up_outcome in self.sequence_outcomes[sequence]:
                    self.sequence_outcomes[sequence][follow_up_outcome] += 1
                
                # Trim sequence_outcomes to prevent infinite growth (e.g., max 5000 unique sequences)
                if len(self.sequence_outcomes) > 5000:
                    # Simple trimming: remove oldest/least frequent (can be improved)
                    keys_to_remove = list(self.sequence_outcomes.keys())[:100] # Remove 100 oldest
                    for key in keys_to_remove:
                        del self.sequence_outcomes[key]


    def predict(self, history: List[RoundResult]) -> Optional[MainOutcome]:
        """
        Predicts based on the most recent sequence's conditional probability.
        Returns the outcome with the highest probability if it meets a minimum threshold.
        """
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 2: # Need at least 2 outcomes to form a 1-length sequence for prediction
            return None

        best_pred = None
        highest_prob = 0.0

        # Check from longest relevant sequence to shortest
        for length in range(5, 1, -1): # Sequence lengths from 5 down to 2
            if len(filtered_history) >= length:
                current_sequence = "".join(filtered_history[-length:])
                
                if current_sequence in self.sequence_outcomes:
                    outcomes_counts = self.sequence_outcomes[current_sequence]
                    total_follows = outcomes_counts["P"] + outcomes_counts["B"]
                    
                    if total_follows > 5: # Only consider if sequence has occurred enough times
                        prob_p = outcomes_counts["P"] / total_follows
                        prob_b = outcomes_counts["B"] / total_follows

                        if prob_p > prob_b and prob_p > highest_prob:
                            best_pred = "P"
                            highest_prob = prob_p
                        elif prob_b > prob_p and prob_b > highest_prob:
                            best_pred = "B"
                            highest_prob = prob_b
        
        # Minimum probability threshold for statistical prediction
        if highest_prob > 0.60: # If the best probability is > 60%
            return best_pred
        
        return None


class TiePredictor:
    """
    Predicts Tie outcomes with confidence.
    """
    THEORETICAL_PROB = 0.0952 # Approx. 9.52% for 8 decks

    def predict(self, history: List[RoundResult]) -> Tuple[Optional[Literal["T"]], Optional[int]]:
        tie_flags = _get_side_bet_history_flags(history, "T")
        main_history_pb = _get_main_outcome_history(history) 
        
        tie_confidence = 0

        if len(tie_flags) < 20: 
            return None, None
        
        long_lookback_for_prob = min(len(tie_flags), 60) 
        short_lookback_for_prob = min(len(tie_flags), 25) 

        actual_tie_count_long = tie_flags[-long_lookback_for_prob:].count(True)
        actual_tie_count_short = tie_flags[-short_lookback_for_prob:].count(True)

        expected_tie_count_long = long_lookback_for_prob * self.THEORETICAL_PROB
        expected_tie_count_short = short_lookback_for_prob * self.THEORETICAL_PROB

        # Rule 1: Ties are "due" based on long-term underperformance
        if actual_tie_count_long < expected_tie_count_long * 0.85: 
            due_factor = (expected_tie_count_long * 0.85 - actual_tie_count_long) / expected_tie_count_long
            tie_confidence = min(95, 70 + int(due_factor * 100 * 0.9)) 
            if tie_confidence >= 60: return "T", tie_confidence 

        # Rule 2: Ties are "due" based on short-term underperformance, even if long-term is okay
        if actual_tie_count_short < expected_tie_count_short * 0.75: 
            due_factor_short = (expected_tie_count_short * 0.75 - actual_tie_count_short) / expected_tie_count_short
            tie_confidence = min(90, 65 + int(due_factor_short * 100 * 0.8)) 
            if tie_confidence >= 60: return "T", tie_confidence 

        # Rule 3: Tie Clustering - predict if a tie was *recently* seen, but not the immediate last round.
        if len(tie_flags) >= 2 and tie_flags[-2] == True and not tie_flags[-1]: 
            return "T", 65 
        if len(tie_flags) >= 3 and tie_flags[-3] == True and not tie_flags[-2] and not tie_flags[-1]: 
            return "T", 60 
        if len(tie_flags) >= 4 and tie_flags[-4] == True and not any(tie_flags[-3:]): 
            return "T", 58 

        # Rule 4: Tie after a long streak of P/B (e.g., 10+ non-tie outcomes)
        if len(main_history_pb) >= 10 and not any(tie_flags[-10:]):
            return "T", 78 

        # Rule 5: Tie after specific alternating patterns in main outcomes (e.g., PBPBPB, then T)
        if len(main_history_pb) >= 6:
            recent_main = "".join(main_history_pb[-6:])
            if recent_main in ["PBPBPB", "BPBPBP"]: 
                return "T", 75 
        
        # Rule 6: Tie after a long streak of one side winning (e.g., 6+ P's or 6+ B's)
        if len(main_history_pb) >= 6:
            if main_history_pb[-6:].count("P") == 6 or main_history_pb[-6:].count("B") == 6:
                return "T", 70 

        # Rule 7: Positional/Interval-based Tie prediction
        current_round_count = len(history) 
        if current_round_count >= 20: 
            if (current_round_count % 8 == 0 or current_round_count % 9 == 0 or current_round_count % 10 == 0):
                if actual_tie_count_long < expected_tie_count_long * 1.0: 
                    return "T", 70 

        # Rule 8: Tie after a very short streak of Banker/Player (2 consecutive)
        if len(main_history_pb) >= 2:
            last_two_pb = "".join(main_history_pb[-2:])
            if last_two_pb == "BB" and not tie_flags[-1]: 
                return "T", 65 
            if last_two_pb == "PP" and not tie_flags[-1]: 
                return "T", 65 
        
        # Rule 9: Tie after a specific alternating pattern (e.g., PBP, BPB)
        if len(main_history_pb) >= 3:
            last_three_pb = "".join(main_history_pb[-3:])
            if last_three_pb == "PBP" and not tie_flags[-1]: 
                return "T", 62 
            if last_three_pb == "BPB" and not tie_flags[-1]: 
                return "T", 62 

        # Rule 10: Trigger Point - Tie return after 4 rounds
        if True in tie_flags: 
            last_tie_index = len(tie_flags) - 1 - tie_flags[::-1].index(True)
            rounds_since_last_tie = len(tie_flags) - 1 - last_tie_index
            
            if rounds_since_last_tie == 4: 
                if actual_tie_count_long < expected_tie_count_long * 1.0: 
                    return "T", 75 

        # Rule 11: Trigger Point - Tie after B-B-P pattern
        if len(main_history_pb) >= 3:
            if "".join(main_history_pb[-3:]) == "BBP" and not tie_flags[-1]: 
                return "T", 70 

        # Rule 12: Tie after a long alternating pattern (e.g., PBPBP or BPBPB)
        if len(main_history_pb) >= 5:
            last_five_pb = "".join(main_history_pb[-5:])
            if last_five_pb == "PBPBP" or last_five_pb == "BPBPB":
                if actual_tie_count_short < expected_tie_count_short * 1.2: 
                    return "T", 78 

        # Rule 13: Tie after a 2-2 pattern (PPBB or BBPP)
        if len(main_history_pb) >= 4:
            last_four_pb = "".join(main_history_pb[-4:])
            if last_four_pb == "PPBB" or last_four_pb == "BBPP":
                if not tie_flags[-1]: 
                    return "T", 72 

        # Rule 14: Tie after a 3-2 pattern (PPPBB or BBBPP)
        if len(main_history_pb) >= 5:
            last_five_pb = "".join(main_history_pb[-5:])
            if last_five_pb == "PPPBB" or last_five_pb == "BBBPP":
                if not tie_flags[-1]: 
                    return "T", 75 

        # Rule 15: Tie after a "near balance" in short history
        if len(main_history_pb) >= 10:
            short_balance_history = main_history_pb[-15:] 
            p_count_balance = short_balance_history.count("P")
            b_count_balance = short_balance_history.count("B")
            
            if abs(p_count_balance - b_count_balance) <= 2:
                if actual_tie_count_long < expected_tie_count_long * 1.0:
                    return "T", 68 

        # Tie Drought - Predict if ties have been absent for a long period
        if len(tie_flags) >= 25: 
            drought_threshold = 20 
            rounds_since_last_tie = -1
            if True in tie_flags: 
                last_tie_index = len(tie_flags) - 1 - tie_flags[::-1].index(True)
                rounds_since_last_tie = len(tie_flags) - 1 - last_tie_index
            
            if rounds_since_last_tie >= drought_threshold or rounds_since_last_tie == -1: 
                drought_factor = min(1.0, (max(0, rounds_since_last_tie - drought_threshold + 1)) / 15) 
                tie_confidence = min(95, 80 + int(drought_factor * 15)) 
                return "T", tie_confidence

        if actual_tie_count_long > expected_tie_count_long * 1.1: 
            return None, None 

        return None, None 

class AdaptiveScorer:
    """
    Calculates the final prediction and its confidence based on module predictions
    and their historical accuracy, with adaptive weighting.
    This scorer is primarily for main P/B outcomes.
    V9.0.0: Re-calibrated for direct "Smart Recommendation" output.
    V10.0.0: Incorporates StatisticalAnalyzer predictions.
    """
    def score(self, 
              predictions: Dict[str, Optional[MainOutcome]], 
              module_accuracies_all_time: Dict[str, float], 
              module_accuracies_recent: Dict[str, float], 
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

            all_time_norm = all_time_acc_val / 100.0 if all_time_acc_val > 0 else 0.5
            recent_norm = recent_acc_val / 100.0 if recent_acc_val > 0 else 0.5

            diff = max(-0.2, min(0.2, recent_norm - all_time_norm)) 
            blend_recent_ratio = 0.74 + (diff * 1.2) 
            blend_recent_ratio = max(0.5, min(0.98, blend_recent_ratio)) 

            weight = (recent_norm * blend_recent_ratio) + (all_time_norm * (1 - blend_recent_ratio))
            
            if name == "AdvancedChop" and predictions.get(name) is not None:
                filtered_history = _get_main_outcome_history(history)
                if len(filtered_history) >= 6:
                    last_6 = filtered_history[-6:]
                    if last_6 == ["P", "P", "P", "B", "B", "B"] or last_6 == ["B", "B", "B", "P", "P", "P"]:
                        weight += 0.2 
                    else:
                        weight += 0.1 
            elif name == "ChopDetector" and predictions.get(name) is not None:
                weight += 0.1 
            
            if name == "ThreeChop" and predictions.get(name) is not None:
                if choppiness_rate > 0.4: 
                    weight *= 1.5 
                else:
                    weight *= 1.2 
            
            if name in ["BigEyeBoy", "SmallRoad", "CockroachPig"] and predictions.get(name) is not None:
                base_derived_weight = 0.8 
                if choppiness_rate > 0.6: 
                    weight += base_derived_weight * 1.5 
                elif choppiness_rate < 0.4: 
                    weight += base_derived_weight * 1.0
                else: 
                    weight += base_derived_weight * 1.2
            
            # V8.8.0: Further refined Dynamic module weighting based on choppiness
            if choppiness_rate > 0.7: 
                if name in ["ChopDetector", "AdvancedChop", "ThreeChop", "BigEyeBoy", "SmallRoad", "CockroachPig"]: 
                    weight *= 1.3 
                elif name in ["Trend", "Rule", "Pattern", "Sniper", "Statistical"]: 
                    weight *= 0.6 
            elif choppiness_rate < 0.3: 
                if name in ["Trend", "Rule", "Pattern", "Sniper", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"]: 
                    weight *= 1.3 
                elif name in ["ChopDetector", "AdvancedChop", "ThreeChop"]: 
                    weight *= 0.6 
            elif choppiness_rate >= 0.3 and choppiness_rate <= 0.7: 
                if name in ["BigEyeBoy", "SmallRoad", "CockroachPig", "ChopDetector", "AdvancedChop", "ThreeChop", "Statistical"]: 
                    weight *= 1.1 
                elif name == "Fallback":
                    weight *= 1.05 
                else:
                    weight *= 0.95 
            
            # V10.0.0: Specific weighting for Statistical module
            if name == "Statistical" and predictions.get(name) is not None:
                if choppiness_rate > 0.5: # Give more weight in balanced/choppy scenarios
                    weight *= 1.2
                else:
                    weight *= 1.05 # Slight boost in streaky too

            if current_miss_streak > 0:
                penalty_factor = 1.0 - (current_miss_streak * 0.22) 
                weight *= max(0.05, penalty_factor) 
            
            if name == "Fallback" and current_miss_streak >= 4:
                weight *= 1.5 

            total_score[pred] += weight

        if not any(total_score.values()):
            return None, None, 0, None 

        best_prediction_outcome = max(total_score, key=total_score.get)
        
        sum_of_scores = sum(total_score.values())
        raw_confidence = (total_score[best_prediction_outcome] / sum_of_scores) * 100
        
        consensus_count = 0
        for name, pred in active_predictions.items():
            if pred == best_prediction_outcome and name != "Fallback":
                consensus_count += 1
        
        if consensus_count >= 7:
            raw_confidence *= 1.15 
        elif consensus_count >= 4:
            raw_confidence *= 1.08 
        elif consensus_count >= 1:
            raw_confidence *= 1.02 

        confidence = min(int(raw_confidence), 95)

        # V8.7.0: Dynamic Confidence Threshold based on Choppiness Rate
        if choppiness_rate > 0.75: 
            confidence = max(50, int(confidence * 0.70)) 
        elif choppiness_rate > 0.6: 
            confidence = max(50, int(confidence * 0.80)) 
        elif choppiness_rate < 0.25: 
            confidence = min(95, int(confidence * 1.08)) 
        
        source_modules = [name for name, pred in active_predictions.items() if pred == best_prediction_outcome]
        source_name = ", ".join(source_modules) if source_modules else "Combined"

        pattern = self._extract_relevant_pattern(history, predictions)
        
        return best_prediction_outcome, source_name, confidence, pattern

    def _extract_relevant_pattern(self, history: List[RoundResult], predictions: Dict[str, Optional[MainOutcome]]) -> Optional[str]:
        filtered_history = _get_main_outcome_history(history)
        if len(filtered_history) < 4:
            return None
        
        joined_filtered = "".join(filtered_history)

        # Prioritize pattern names based on common understanding and clarity
        # Check for long streaks (Dragon) first
        if len(filtered_history) >= 4:
            last_4 = filtered_history[-4:]
            if last_4.count("P") == 4:
                return "มังกร"
            if last_4.count("B") == 4:
                return "มังกร"
        
        if len(filtered_history) >= 5:
            last_5 = filtered_history[-5:]
            if last_5.count("P") == 5:
                return "มังกรยาว"
            if last_5.count("B") == 5:
                return "มังกรยาว"
        
        if len(filtered_history) >= 6:
            last_6 = filtered_history[-6:]
            if last_6.count("P") == 6:
                return "มังกรยาว"
            if last_6.count("B") == 6:
                return "มังกรยาว"

        # Check for Ping Pong (alternating) patterns
        if len(filtered_history) >= 4:
            last_4 = "".join(filtered_history[-4:])
            if last_4 == "PBPB" or last_4 == "BPBP":
                return "ปิงปอง"
        if len(filtered_history) >= 5:
            last_5 = "".join(filtered_history[-5:])
            if last_5 == "PBPBP" or last_5 == "BPBPB":
                return "ปิงปองยาว"
        if len(filtered_history) >= 6:
            last_6 = "".join(filtered_history[-6:])
            if last_6 == "PBPBPB" or last_6 == "BPBPBP":
                return "ปิงปองยาว"

        # Check for specific chop patterns (สามตัวตัด, มังกรตัด, ปิงปองตัด)
        if "AdvancedChop" in predictions and predictions["AdvancedChop"] is not None:
            if len(filtered_history) >= 6:
                last_6 = filtered_history[-6:]
                if last_6 == ["P", "P", "P", "B", "B", "B"] or last_6 == ["B", "B", "B", "P", "P", "P"]:
                    return "สามตัวตัด"
            if len(filtered_history) >= 5:
                # Check for Dragon Chop pattern: XXXXXY
                if all(x == filtered_history[-6] for x in filtered_history[-6:-1]) and filtered_history[-1] != filtered_history[-6]:
                    return "มังกรตัด"
            if len(filtered_history) >= 4:
                # Check for Ping-Pong Chop pattern: XYX X
                if filtered_history[-4] != filtered_history[-3] and filtered_history[-3] == filtered_history[-2] and filtered_history[-2] == filtered_history[-1]:
                    return "ปิงปองตัด"

        # Check for "Three-Chop" specifically (PPP -> B or BBB -> P)
        if "ThreeChop" in predictions and predictions["ThreeChop"] is not None:
            if len(filtered_history) >= 3:
                last_three = "".join(filtered_history[-3:])
                if last_three == "PPP" or last_three == "BBB":
                    return "ตัดสาม"

        # Other common patterns
        common_patterns = {
            "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
            "PBB": "สองตัวตัด", "BPP": "สองตัวตัด", 
            "PPBP": "สองตัวตัด", "BBPA": "สองตัวตัด", 
            "PBPP": "คู่สลับ", "BPPB": "คู่สลับ",
            "PBBPP": "สองตัวตัด", "BPBB": "สองตัวติด", 
            "PBBP": "คู่สลับ", "BPPB": "คู่สลับ" 
        }
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

        # Global logs for all-time accuracy (NOT persistent in this version by default, but can be saved/loaded)
        self.module_accuracy_global_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [], "DragonTail": [], "AdvancedChop": [], "ThreeChop": [], 
            "BigEyeBoy": [], "SmallRoad": [], "CockroachPig": [], "Statistical": [] 
        }
        self.tie_module_accuracy_global_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 

        # Per-shoe logs for recent accuracy and current shoe display
        self.individual_module_prediction_log_current_shoe: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "2-2 Pattern": [], "Sniper": [], "Fallback": [], "ChopDetector": [], "DragonTail": [], "AdvancedChop": [], "ThreeChop": [], 
            "BigEyeBoy": [], "SmallRoad": [], "CockroachPig": [], "Statistical": [] 
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
        self.three_chop_predictor = ThreeChopPredictor() 
        self.derived_road_analyzer = DerivedRoadAnalyzer() 
        self.statistical_analyzer = StatisticalAnalyzer() 

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
        current_miss_streak = self.calculate_miss_streak() # Get current miss streak for fallback

        current_predictions_from_modules_main = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history, choppiness_rate_for_trend), 
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate_for_trend), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history, current_miss_streak), 
            "ChopDetector": self.chop_detector.predict(self.history),
            "DragonTail": self.dragon_tail_detector.predict(self.history),
            "AdvancedChop": self.advanced_chop_predictor.predict(self.history),
            "ThreeChop": self.three_chop_predictor.predict(self.history),
            "Statistical": self.statistical_analyzer.predict(self.history) 
        }
        
        derived_road_preds = self.derived_road_analyzer.predict(self.history)
        current_predictions_from_modules_main.update(derived_road_preds)

        for module_name, pred in current_predictions_from_modules_main.items():
            if pred is not None and pred in ("P", "B") and main_outcome in ("P", "B"):
                if module_name not in self.module_accuracy_global_log:
                    self.module_accuracy_global_log[module_name] = []
                if module_name not in self.individual_module_prediction_log_current_shoe:
                    self.individual_module_prediction_log_current_shoe[module_name] = []

                self.module_accuracy_global_log[module_name].append((pred, main_outcome))
                self.individual_module_prediction_log_current_shoe[module_name].append((pred, main_outcome))

        # --- Record individual side bet module predictions *before* adding the new outcome ---
        tie_pred_for_log, _ = self.tie_predictor.predict(self.history)

        if tie_pred_for_log is not None:
            self.tie_module_accuracy_global_log.append((tie_pred_for_log, main_outcome == "T"))
            self.tie_module_prediction_log_current_shoe.append((tie_pred_for_log, main_outcome == "T"))

        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.prediction_log.append(self.last_prediction) 
        self.result_log.append(main_outcome) 
        
        # V10.0.0: Update StatisticalAnalyzer's internal history
        self.statistical_analyzer.update_sequence_history(_get_main_outcome_history(self.history))

        self._trim_global_logs() 

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
        
        # V10.0.0: Re-initialize StatisticalAnalyzer to clear its history (simpler than reverse-updating)
        self.statistical_analyzer = StatisticalAnalyzer()
        self.statistical_analyzer.update_sequence_history(_get_main_outcome_history(self.history)) # Rebuild from current history

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
        
        # V10.0.0: Reset StatisticalAnalyzer
        self.statistical_analyzer = StatisticalAnalyzer()

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
        
        # V10.0.0: Reset StatisticalAnalyzer for new shoe
        self.statistical_analyzer = StatisticalAnalyzer()


    def export_all_time_data(self) -> Dict[str, Any]:
        """
        Exports the global accuracy logs and statistical analyzer data for persistence.
        """
        export_data = {
            "module_accuracy_global_log": {},
            "tie_module_accuracy_global_log": [],
            "statistical_analyzer_sequence_outcomes": self.statistical_analyzer.sequence_outcomes 
        }
        
        # Convert tuples to lists for JSON serialization
        for module_name, log_list in self.module_accuracy_global_log.items():
            export_data["module_accuracy_global_log"][module_name] = [list(item) for item in log_list]
        
        export_data["tie_module_accuracy_global_log"] = [list(item) for item in self.tie_module_accuracy_global_log]
        
        return export_data

    def import_all_time_data(self, imported_data: Dict[str, Any]):
        """
        Imports global accuracy logs and statistical analyzer data from a dictionary.
        """
        if not isinstance(imported_data, dict):
            raise ValueError("Imported data must be a dictionary.")
        
        if "module_accuracy_global_log" in imported_data and isinstance(imported_data["module_accuracy_global_log"], dict):
            for module_name, log_list in imported_data["module_accuracy_global_log"].items():
                if module_name in self.module_accuracy_global_log and isinstance(log_list, list):
                    # Convert lists back to tuples
                    self.module_accuracy_global_log[module_name] = [tuple(item) for item in log_list if isinstance(item, list) and len(item) == 2]
                else:
                    st.warning(f"Skipping import for unknown or invalid module: {module_name}")
        
        if "tie_module_accuracy_global_log" in imported_data and isinstance(imported_data["tie_module_accuracy_global_log"], list):
            self.tie_module_accuracy_global_log = [tuple(item) for item in imported_data["tie_module_accuracy_global_log"] if isinstance(item, list) and len(item) == 2]
        else:
            st.warning("Skipping import for invalid tie module accuracy log.")

        # V10.0.0: Import statistical analyzer data
        if "statistical_analyzer_sequence_outcomes" in imported_data and isinstance(imported_data["statistical_analyzer_sequence_outcomes"], dict):
            self.statistical_analyzer.sequence_outcomes = imported_data["statistical_analyzer_sequence_outcomes"]
            st.success("ข้อมูลสถิติ All-Time ถูกอัปโหลดเรียบร้อยแล้ว!")
        else:
            st.warning("Skipping import for invalid statistical analyzer data.")

        st.success("ข้อมูล All-Time ถูกอัปโหลดเรียบร้อยแล้ว!")


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
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop", "ThreeChop", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] 
        for module_name in main_modules:
            if module_name in self.module_accuracy_global_log:
                accuracy_results[module_name] = self._calculate_main_module_accuracy_from_log(self.module_accuracy_global_log[module_name], lookback=None)
            else:
                accuracy_results[module_name] = 0.0 
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_accuracy_global_log, lookback=None)

        return accuracy_results

    def get_module_accuracy_recent(self, lookback: int) -> Dict[str, float]:
        """
        Calculates recent accuracy from current shoe logs.
        """
        accuracy_results = {}
        main_modules = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop", "ThreeChop", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] 
        for module_name in main_modules:
            if module_name in self.individual_module_prediction_log_current_shoe:
                accuracy_results[module_name] = self._calculate_main_module_accuracy_from_log(self.individual_module_prediction_log_current_shoe[module_name], lookback)
            else:
                accuracy_results[module_name] = 0.0 
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_prediction_log_current_shoe, lookback)

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        all_known_modules_for_norm = ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "Fallback", "ChopDetector", "DragonTail", "AdvancedChop", "ThreeChop", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical", "Tie"] 
        
        if not acc:
            return {name: 0.5 for name in all_known_modules_for_norm}
        
        active_main_accuracies = {k: v for k, v in acc.items() if k in ["Rule", "Pattern", "Trend", "2-2 Pattern", "Sniper", "ChopDetector", "DragonTail", "AdvancedChop", "ThreeChop", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] and v > 0} 
        
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
            "AdvancedChop": self.advanced_chop_predictor,
            "ThreeChop": self.three_chop_predictor,
            "BigEyeBoy": self.derived_road_analyzer, 
            "SmallRoad": self.derived_road_analyzer,
            "CockroachPig": self.derived_road_analyzer,
            "Statistical": self.statistical_analyzer 
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
        bool, str # recommendation_text
    ]:
        """
        Generates the next predictions for main outcome and side bets,
        along with main outcome's source, confidence, miss streak, and Sniper opportunity flag.
        V10.0.0: Returns a direct recommendation text, incorporating statistical analysis.
        """
        main_history_filtered_for_pb = _get_main_outcome_history(self.history)
        p_count = main_history_filtered_for_pb.count("P")
        b_count = main_history_filtered_for_pb.count("B")
        
        current_miss_streak = self.calculate_miss_streak()

        MIN_HISTORY_FOR_PREDICTION = 15 
        
        MIN_HISTORY_FOR_SNIPER = 25 
        MIN_HISTORY_FOR_SIDE_BET_SNIPER = 25 
        
        RECOMMEND_BET_CONFIDENCE_THRESHOLD = 65 
        MIN_DISPLAY_CONFIDENCE_SIDE_BET = 55 

        final_prediction_main = None
        source_module_name_main = None
        confidence_main = None 
        pattern_code_main = None
        is_sniper_opportunity_main = False 
        
        tie_prediction = None
        tie_confidence = None

        is_tie_sniper_opportunity = False
        recommendation_text = "กำลังวิเคราะห์ข้อมูล..." 

        if (p_count + b_count) < MIN_HISTORY_FOR_PREDICTION:
            self.last_prediction = None
            self.last_module = None
            return None, None, None, None, current_miss_streak, False, None, None, False, "กำลังเรียนรู้... รอข้อมูลครบ 15 ตา (P/B) ก่อนเริ่มทำนาย" 
        
        choppiness_rate = self._calculate_choppiness_rate(self.history, 20) 

        predictions_from_modules = {
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history, choppiness_rate), 
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate), 
            "2-2 Pattern": self.two_two_pattern.predict(self.history),
            "Sniper": self.sniper_pattern.predict(self.history), 
            "Fallback": self.fallback_module.predict(self.history, current_miss_streak), 
            "ChopDetector": self.chop_detector.predict(self.history),
            "DragonTail": self.dragon_tail_detector.predict(self.history),
            "AdvancedChop": self.advanced_chop_predictor.predict(self.history),
            "ThreeChop": self.three_chop_predictor.predict(self.history),
            "Statistical": self.statistical_analyzer.predict(self.history) 
        }
        
        derived_road_preds = self.derived_road_analyzer.predict(self.history)
        predictions_from_modules.update(derived_road_preds)

        module_accuracies_all_time = self.get_module_accuracy_all_time()
        module_accuracies_recent_10 = self.get_module_accuracy_recent(10) 
        module_accuracies_recent_20 = self.get_module_accuracy_recent(20) 

        final_prediction_main, source_module_name_main, confidence_main, pattern_code_main = \
            self.scorer.score(predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history, current_miss_streak, choppiness_rate) 

        if self.history and self.history[-1].main_outcome == "T":
            if final_prediction_main is not None and confidence_main is not None:
                confidence_main = max(RECOMMEND_BET_CONFIDENCE_THRESHOLD, int(confidence_main * 0.85)) 

        # V10.0.0: Logic to determine recommendation text
        if current_miss_streak >= 6:
            recommendation_text = "🚨 เกมแตก! (แพ้ 6 ไม้ติด) - แนะนำให้ 'เริ่มขอนใหม่' หรือ 'รีเซ็ตข้อมูลทั้งหมด' เพื่อเริ่มเกมใหม่"
            final_prediction_main = None 
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None
        elif final_prediction_main is not None and confidence_main is not None and confidence_main >= RECOMMEND_BET_CONFIDENCE_THRESHOLD: 
            recommendation_text = f"✅ แนะนำ: {final_prediction_main}"
        else:
            if choppiness_rate > 0.65:
                recommendation_text = "🚫 งดเดิมพัน: เค้าไพ่ผันผวนสูง"
            else:
                recommendation_text = "🚫 งดเดิมพัน: ยังไม่พบแพทเทิร์นชัดเจน"
            
            final_prediction_main = None
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None 
        
        # --- Main Outcome Sniper Opportunity Logic ---
        if final_prediction_main in ("P", "B") and confidence_main is not None:
            if confidence_main >= 70 and current_miss_streak <= 2 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER: 
                contributing_modules = [m.strip() for m in source_module_name_main.split(',')]
                
                relevant_contributing_modules = [m for m in contributing_modules if m not in ["Fallback", "NoPrediction"]]

                high_accuracy_contributing_count = 0
                
                CONTRIBUTING_MODULE_RECENT_ACCURACY_THRESHOLD = 65 

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
            if tie_confidence >= 60 and (p_count + b_count) >= MIN_HISTORY_FOR_SIDE_BET_SNIPER: 
                if len(self.tie_module_prediction_log_current_shoe) >= SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT:
                    tie_recent_acc = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_prediction_log_current_shoe, SIDE_BET_SNIPER_RECENT_PREDICTION_COUNT)
                else:
                    tie_recent_acc = 0 
                
                if tie_recent_acc >= SIDE_BET_SNIPER_RECENT_ACCURACY_THRESHOLD:
                    is_tie_sniper_opportunity = True

        return (
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_miss_streak, is_sniper_opportunity_main,
            tie_prediction, tie_confidence, 
            is_tie_sniper_opportunity, recommendation_text 
        )

# --- Streamlit UI Code ---

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle V10.2.0", layout="centered") # Updated version to V10.2.0

# --- Custom CSS for Styling ---
st.markdown("""
<style>
/* Import Sarabun font from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

html, body, [class*="st-emotion"] { /* Target Streamlit's main content div classes */
    font-family: 'Sarabun', sans-serif !important;
}
.big-title {
    font-size: 20px; /* Further reduced from 24px */
    text-align: center;
    font-weight: bold;
    color: #FF4B4B; /* Streamlit's default primary color */
    margin-bottom: 10px; /* Further reduced margin */
}
.predict-box {
    padding: 10px; /* Further reduced from 12px */
    background-color: #262730; /* Darker background for the box */
    border-radius: 8px; /* Further reduced border-radius */
    color: white;
    margin-bottom: 10px; /* Further reduced margin */
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2); /* Slightly smaller shadow */
    text-align: center; /* Center content inside prediction box */
}
.predict-box h2 {
    margin: 6px 0; /* Further reduced margin */
    font-size: 26px; /* Further reduced from 32px */
    font-weight: bold;
}
.predict-box b {
    color: #FFD700; /* Gold color for emphasis */
}
.predict-box .st-emotion-cache-1c7y2vl { /* Target Streamlit's caption */
    font-size: 11px; /* Further reduced from 12px */
    color: #BBBBBB;
}

/* Miss Streak warning text */
.st-emotion-cache-1f1d6zpt p, .st-emotion-cache-1s04v0m p { /* Target text inside warning/error boxes */
    font-size: 11px; /* Further reduced from 12px */
}


.big-road-container {
    width: 100%;
    overflow-x: auto; /* Allows horizontal scrolling if many columns */
    padding: 5px 0; /* Further reduced padding */
    background: #1A1A1A; /* Slightly darker background for the road */
    border-radius: 5px; /* Further reduced border-radius */
    white-space: nowrap; /* Keeps columns in a single line */
    display: flex; /* Use flexbox for columns */
    flex-direction: row; /* Display columns from left to right */
    align-items: flex-start; /* Align columns to the top */
    min-height: 100px; /* Further adjusted minimum height for the road */
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3); /* Slightly smaller shadow */
}
.big-road-column {
    display: inline-flex; /* Use inline-flex for vertical stacking within column */
    flex-direction: column;
    margin-right: 0.5px; /* Further reduced margin */
    border-right: 1px solid rgba(255,255,255,0.05); /* Slightly lighter border */
    padding-right: 0.5px; /* Further reduced padding */
}
.big-road-cell {
    width: 16px; /* Further reduced from 18px */
    height: 16px; /* Further reduced from 18px */
    text-align: center;
    line-height: 16px; /* Adjusted line-height for new size */
    font-size: 11px; /* Further reduced from 12px */
    margin-bottom: 0.25px; /* Further reduced margin */
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
    font-size: 7px; /* Further reduced from 8px */
    position: absolute;
    bottom: -1px; /* Adjusted position */
    right: -1px; /* Adjusted position */
    background-color: #FFD700; /* Gold background for prominence */
    color: #333; /* Dark text for contrast */
    border-radius: 50%;
    padding: 0px 1.5px; /* Further reduced padding */
    line-height: 1;
    min-width: 10px; /* Ensure minimum width for single digit */
    text-align: center;
    box-shadow: 0 0.5px 1px rgba(0,0,0,0.2); /* Slightly smaller shadow */
}
/* Styling for Natural indicator in Big Road (New for V6.5) */
.natural-indicator {
    position: absolute;
    font-size: 6px; /* Further reduced from 7px */
    font-weight: bold;
    color: white;
    line-height: 1;
    padding: 0.5px 1.5px; /* Further reduced padding */
    border-radius: 2px; /* Further reduced border-radius */
    z-index: 10;
    background-color: #4CAF50; /* Green for Natural */
    top: -1.5px; /* Adjusted position */
    right: -1.5px; /* Adjusted position */
}

/* Derived Road Styles */
.derived-road-container {
    width: 100%;
    overflow-x: auto;
    padding: 3px 0; /* Further reduced padding */
    background: #1A1A1A;
    border-radius: 5px; /* Further reduced border-radius */
    white-space: nowrap;
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    min-height: 50px; /* Further reduced height for derived roads */
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.2); 
    margin-top: 6px; /* Further reduced margin */
}
.derived-road-column {
    display: inline-flex;
    flex-direction: column;
    margin-right: 0.25px; /* Further reduced margin */
    border-right: 1px solid rgba(255,255,255,0.02); /* Lighter border */
    padding-right: 0.25px; /* Further reduced padding */
}
.derived-road-cell {
    width: 9px; /* Further reduced from 10px */
    height: 9px; /* Further reduced from 10px */
    text-align: center;
    line-height: 9px; /* Adjusted line-height */
    font-size: 6px; /* Further reduced from 7px */
    margin-bottom: 0.125px; /* Further reduced margin */
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
    color: white;
}
.derived-road-cell.P { background-color: #007BFF; } /* Blue for Player (Chop) */
.derived-road-cell.B { background-color: #DC3545; } /* Red for Banker (Follow) */


/* Button styling */
.stButton>button {
    width: 100%;
    border-radius: 6px; /* Further reduced border-radius */
    font-size: 14px; /* Further reduced from 16px */
    font-weight: bold;
    padding: 7px 0; /* Further reduced padding */
    margin-bottom: 7px; /* Further reduced margin */
    transition: all 0.2s ease-in-out;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Slightly smaller shadow */
}
.stButton>button:hover {
    transform: translateY(-1px); 
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2); 
}
/* Specific button colors */
#btn_P button { background-color: #007BFF; color: white; border: none; }
#btn_B button { background-color: #DC3545; color: white; border: none; }
#btn_T button { background-color: #6C757D; color: white; border: none; }
/* Checkbox styling adjustments */
.stCheckbox > label {
    padding: 5px 7px; /* Further reduced padding */
    border: 1px solid #495057;
    border-radius: 6px; /* Further reduced border-radius */
    background-color: #343A40;
    color: white;
    font-size: 12px; /* Further reduced from 13px */
    font-weight: bold;
    margin-bottom: 7px; /* Further reduced margin */
    display: flex; 
    align-items: center;
    justify-content: center; 
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}
.stCheckbox > label:hover {
    background-color: #495057;
    transform: translateY(-1px);
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
}
.stCheckbox > label > div:first-child { 
    margin-right: 5px; /* Further reduced margin */
}
/* Style for checked checkboxes */
.stCheckbox > label[data-checked="true"] {
    background-color: #007BFF; 
    border-color: #007BFF;
}


.stButton button[kind="secondary"] { 
    background-color: #343A40;
    color: white;
    border: 1px solid #495057;
}
.stButton button[kind="secondary"]:hover {
    background-color: #495057;
}

/* Warning/Error messages */
.st-emotion-cache-1f1d6zpt { 
    background-color: #FFC10720; 
    border-left: 4px solid #FFC107; /* Reduced border thickness */
    color: #FFC107;
    padding: 7px; /* Further reduced padding */
    margin-bottom: 8px; /* Further reduced margin */
}

.st-emotion-cache-1s04v0m { 
    background-color: #DC354520; 
    border-left: 4px solid #DC3545; /* Reduced border thickness */
    color: #DC3545;
    padding: 7px; /* Further reduced padding */
    margin-bottom: 8px; /* Further reduced margin */
}

.st-emotion-cache-13ln4z2 { 
    background-color: #17A2B820; 
    border-left: 4px solid #17A2B8; /* Reduced border thickness */
    color: #17A2B8;
    padding: 7px; /* Further reduced padding */
    margin-bottom: 8px; /* Further reduced margin */
}

/* Accuracy by Module section */
h3 { 
    font-size: 10px !important; /* Further reduced from 11px */
    margin-top: 7px !important; /* Further reduced margin */
    margin-bottom: 1px !important; /* Further reduced margin */
}
/* Target for the custom class used for accuracy items */
.accuracy-item { 
    font-size: 8px !important; /* Further reduced from 9px */
    margin-bottom: 0.25px !important; /* Further reduced margin */
}

/* Sniper message styling */
.sniper-message {
    background-color: #4CAF50; 
    color: white;
    padding: 7px; /* Further reduced padding */
    border-radius: 6px; /* Further reduced border-radius */
    font-weight: bold;
    text-align: center;
    margin-top: 10px; /* Further reduced margin */
    margin-bottom: 10px; /* Further reduced margin */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    animation: pulse 1.5s infinite; 
    font-size: 13px; /* Further reduced from 15px */
}

/* NEW: Side Bet Sniper message styling */
.side-bet-sniper-message {
    background-color: #007bff; 
    color: white;
    padding: 5px; /* Further reduced padding */
    border-radius: 4px; /* Further reduced border-radius */
    font-weight: bold;
    text-align: center;
    margin-top: 7px; /* Further reduced margin */
    margin-bottom: 7px; /* Further reduced margin */
    box-shadow: 0 1.5px 3px rgba(0, 0, 0, 0.2);
    animation: pulse 1.5s infinite; 
    font-size: 11px; /* Further reduced from 12px */
}


@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.005); opacity: 0.98; } /* Even less aggressive pulse */
    100% { transform: scale(1); opacity: 1; }
}


hr {
    border-top: 1px solid rgba(255,255,255,0.05); /* Even lighter border */
    margin: 15px 0; /* Further reduced margin */
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
if 'recommendation_text' not in st.session_state: 
    st.session_state.recommendation_text = "กำลังวิเคราะห์ข้อมูล..." # Default message


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
     is_tie_sniper_opportunity, recommendation_text) = st.session_state.oracle.predict_next() 
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence 
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 
    
    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    st.session_state.recommendation_text = recommendation_text 
    
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
        "มังกรตัด": "มังกรตัด", 
        "ปิงปองตัด": "ปิงปองตัด", 
        "ตัดสาม": "ตัดสาม" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) >= 15: 
        st.session_state.initial_shown = True 

    st.query_params["_t"] = f"{time.time()}"


def handle_remove():
    """
    Handles removing the last added result.
    """
    st.session_state.oracle.remove_last()
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity, recommendation_text) = st.session_state.oracle.predict_next() 
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 

    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    st.session_state.recommendation_text = recommendation_text
    
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
        "มังกรตัด": "มังกรตัด", 
        "ปิงปองตัด": "ปิงปองตัด", 
        "ตัดสาม": "ตัดสาม" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) < 15: 
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
    st.session_state.recommendation_text = "กำลังเรียนรู้... รอข้อมูลครบ 15 ตา (P/B) ก่อนเริ่มทำนาย"

    st.query_params["_t"] = f"{time.time()}"

# --- Header ---
st.markdown('<div class="big-title">🔮 Oracle V10.2.0</div>', unsafe_allow_html=True) # Updated version to V10.2.0

# --- Prediction Output Box (Main Outcome) ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำแนะนำการเดิมพัน:</b>", unsafe_allow_html=True) 

# V9.0.0: Display recommendation text directly
st.markdown(f"<h2>{st.session_state.recommendation_text}</h2>", unsafe_allow_html=True)

# Only show supporting details if there's a direct prediction (not "No Bet" or "Learning")
if st.session_state.prediction and st.session_state.prediction in ("P", "B"):
    if st.session_state.source:
        st.caption(f"🧠 โมดูลที่สนับสนุน: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่ที่ตรวจพบ: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจภายใน: {st.session_state.confidence:.1f}%") # Show internal confidence for transparency
else:
    # If no prediction, remove source/pattern name captions
    st.session_state.source = None
    st.session_state.pattern_name = None
    st.session_state.confidence = None # Clear confidence if no prediction

st.markdown("</div>", unsafe_allow_html=True)

# --- Sniper Opportunity Message (Main Outcome) ---
if st.session_state.is_sniper_opportunity_main: 
    st.markdown("""
        <div class="sniper-message">
            🎯 SNIPER! โอกาสเดิมพันสูง!
        </div>
    """, unsafe_allow_html=True)

# --- Side Bet Prediction Display ---
if st.session_state.tie_prediction and st.session_state.tie_confidence is not None:
    st.markdown("<b>📍 คำแนะนำเสริม:</b>", unsafe_allow_html=True) 
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
    st.error("🚨 เกมแตก! (แพ้ 6 ไม้ติด)")

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

# --- Derived Roads Display (New for V8.9.0) ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<b>📊 เค้าไพ่รอง (Derived Roads):</b>", unsafe_allow_html=True)

derived_road_matrices = st.session_state.oracle.derived_road_analyzer.get_full_derived_road_matrices(st.session_state.oracle.history)

if derived_road_matrices["BigEyeBoyMatrix"]:
    st.markdown("<h5>Big Eye Boy (บิ๊กอายบอย)</h5>", unsafe_allow_html=True)
    beb_html = "<div class='derived-road-container'>"
    # Only display the last few columns to match Big Road display
    beb_matrix_display = derived_road_matrices["BigEyeBoyMatrix"][-MAX_DISPLAY_COLUMNS:]
    for col in beb_matrix_display:
        beb_html += "<div class='derived-road-column'>"
        for cell_val in col:
            if cell_val:
                emoji = "🔵" if cell_val == "P" else "🔴"
                beb_html += f"<div class='derived-road-cell {cell_val}'>{emoji}</div>"
            else:
                beb_html += f"<div class='derived-road-cell'></div>" # Empty cell for padding
        beb_html += "</div>"
    beb_html += "</div>"
    st.markdown(beb_html, unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลเค้าไพ่รอง Big Eye Boy")

if derived_road_matrices["SmallRoadMatrix"]:
    st.markdown("<h5>Small Road (ซาลาเปา)</h5>", unsafe_allow_html=True)
    sr_html = "<div class='derived-road-container'>"
    sr_matrix_display = derived_road_matrices["SmallRoadMatrix"][-MAX_DISPLAY_COLUMNS:]
    for col in sr_matrix_display:
        sr_html += "<div class='derived-road-column'>"
        for cell_val in col:
            if cell_val:
                emoji = "🔵" if cell_val == "P" else "🔴"
                sr_html += f"<div class='derived-road-cell {cell_val}'>{emoji}</div>"
            else:
                sr_html += f"<div class='derived-road-cell'></div>"
        sr_html += "</div>"
    sr_html += "</div>"
    st.markdown(sr_html, unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลเค้าไพ่รอง Small Road")

if derived_road_matrices["CockroachPigMatrix"]:
    st.markdown("<h5>Cockroach Pig (ไม้ขีด)</h5>", unsafe_allow_html=True)
    cp_html = "<div class='derived-road-container'>"
    cp_matrix_display = derived_road_matrices["CockroachPigMatrix"][-MAX_DISPLAY_COLUMNS:]
    for col in cp_matrix_display:
        cp_html += "<div class='derived-road-column'>"
        for cell_val in col:
            if cell_val:
                emoji = "🔵" if cell_val == "P" else "🔴"
                cp_html += f"<div class='derived-road-cell {cell_val}'>{emoji}</div>"
            else:
                cp_html += f"<div class='derived-road-cell'></div>"
        cp_html += "</div>"
    cp_html += "</div>"
    st.markdown(cp_html, unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลเค้าไพ่รอง Cockroach Pig")


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
    st.button("▶️ เริ่มขอนใหม่", on_click=handle_start_new_shoe)

# --- Data Management ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<b>💾 จัดการข้อมูล All-Time:</b>", unsafe_allow_html=True)

col_dl, col_ul = st.columns(2)

with col_dl:
    # Prepare data for download
    data_to_export = st.session_state.oracle.export_all_time_data()
    json_data = json.dumps(data_to_export, indent=4)
    
    st.download_button(
        label="⬇️ ดาวน์โหลดข้อมูล All-Time",
        data=json_data,
        file_name="oracle_all_time_data.json",
        mime="application/json",
        key="download_all_time_data_btn",
        help="ดาวน์โหลดข้อมูลความแม่นยำ All-Time เพื่อสำรองไว้"
    )

with col_ul:
    uploaded_file = st.file_uploader("⬆️ อัปโหลดข้อมูล All-Time", type="json", key="upload_all_time_data_uploader", help="อัปโหลดไฟล์ JSON ที่มีข้อมูลความแม่นยำ All-Time")
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            decoded_data = bytes_data.decode("utf-8")
            loaded_data = json.loads(decoded_data)
            st.session_state.oracle.import_all_time_data(loaded_data)
            # Re-run prediction to update UI with new data
            (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
             tie_pred, tie_conf,
             is_tie_sniper_opportunity, recommendation_text) = st.session_state.oracle.predict_next()

            st.session_state.prediction = prediction
            st.session_state.source = source
            st.session_state.confidence = confidence
            st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main
            st.session_state.tie_prediction = tie_pred
            st.session_state.tie_confidence = tie_conf
            st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
            st.session_state.recommendation_text = recommendation_text
            
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
                "มังกรตัด": "มังกรตัด",
                "ปิงปองตัด": "ปิงปองตัด",
                "ตัดสาม": "ตัดสาม"
            }
            st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)

            st.query_params["_t"] = f"{time.time()}" # Force UI refresh
            
        except json.JSONDecodeError:
            st.error("ไฟล์ที่อัปโหลดไม่ใช่ไฟล์ JSON ที่ถูกต้อง")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

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

    st.markdown("<h4>⚙️ การทำนายจากเค้าไพ่รอง (Derived Road Predictions)</h4>", unsafe_allow_html=True)
    derived_preds_debug = st.session_state.oracle.derived_road_analyzer.predict(st.session_state.oracle.history)
    for road_name, pred_val in derived_preds_debug.items():
        st.write(f"  - {road_name}: {pred_val if pred_val else 'None'}") 
    st.write("---")

    st.markdown("<h4>⚙️ การทำนายจากสถิติ (Statistical Predictions)</h4>", unsafe_allow_html=True)
    # To show the statistical prediction, we need to call predict() again for debug purposes
    # Or, we can expose the internal state of StatisticalAnalyzer if needed for deeper debug
    stat_pred_debug = st.session_state.oracle.statistical_analyzer.predict(st.session_state.oracle.history)
    st.write(f"  - Statistical Prediction: {stat_pred_debug if stat_pred_debug else 'None'}")
    st.write(f"  - Statistical Analyzer Sequence Outcomes: {st.session_state.oracle.statistical_analyzer.sequence_outcomes}")
    st.write("---")


# --- Accuracy by Module ---
st.markdown("<h3>📈 ความแม่นยำรายโมดูล</h3>", unsafe_allow_html=True) 

all_time_accuracies = st.session_state.oracle.get_module_accuracy_all_time()
recent_10_accuracies = st.session_state.oracle.get_module_accuracy_recent(10)
recent_20_accuracies = st.session_state.oracle.get_module_accuracy_recent(20)

if all_time_accuracies:
    st.markdown("<h4>ความแม่นยำ (All-Time)</h4>", unsafe_allow_html=True)
    sorted_module_names = sorted(all_time_accuracies.keys(), key=lambda x: (x in ["Tie"], x in ["BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"], x)) 
    for name in sorted_module_names:
        acc = all_time_accuracies[name]
        st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    main_history_len = p_count + b_count

    if main_history_len >= 10: 
        st.markdown("<h4>ความแม่นยำ (10 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_10 = sorted(recent_10_accuracies.keys(), key=lambda x: (x in ["Tie"], x in ["BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"], x)) 
        for name in sorted_module_names_recent_10:
            acc = recent_10_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)

    if main_history_len >= 20: 
        st.markdown("<h4>ความแม่นยำ (20 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_20 = sorted(recent_20_accuracies.keys(), key=lambda x: (x in ["Tie"], x in ["BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"], x)) 
        for name in sorted_module_names_recent_20:
            acc = recent_20_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลความแม่นยำ")

