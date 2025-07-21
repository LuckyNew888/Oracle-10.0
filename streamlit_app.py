# streamlit_app.py (Oracle V10.6.7 - Fix Module Accuracy Display)
import streamlit as st
import time 
from typing import List, Optional, Literal, Tuple, Dict, Any
import random
from dataclasses import dataclass, asdict # Import asdict for dataclass to dict conversion
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
    V10.5.3: Added more complex mixed patterns.
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
            "PBBP": "B", "BPPB": "P",
            # V10.5.3: Added complex mixed patterns based on user feedback
            "PBBPPP": "P", # P then BB then PPP, predicts P (continuation of P streak)
            "BPPBBB": "B", # B then PP then BBB, predicts B (continuation of B streak)
            # For PBPBPBPPPBBB, this is too long for a single pattern.
            # We focus on the immediate transition after a long ping-pong.
            # If PBPBPB is followed by P, it's a chop. If it's PBPBPB followed by B, it's also a chop.
            # The statistical analyzer is better for very long sequences.
        }

    def predict(self, history: List[RoundResult], choppiness_rate: float) -> Optional[MainOutcome]: # Added choppiness_rate
        filtered_history = _get_main_outcome_history(history)
        # Check for sufficient history for the longest patterns first
        max_pattern_length = max(len(p) for p in self.patterns_and_predictions.keys()) if self.patterns_and_predictions else 0
        
        if len(filtered_history) < max_pattern_length:
            return None

        joined_filtered = "".join(filtered_history)
        
        # V8.2.0: Dynamic pattern window - adjust iteration based on choppiness.
        # If very choppy, prioritize shorter patterns (e.g., 3-length patterns first).
        # If very streaky, prioritize longer patterns (e.g., 6-length patterns first).
        # V10.5.3: Adjusted range to include longer patterns if present
        
        # Get lengths of all patterns to check, sorted dynamically
        all_pattern_lengths = sorted(list(set(len(p) for p in self.patterns_and_predictions.keys())))
        
        if choppiness_rate > 0.7: 
            lengths_to_check = sorted([l for l in all_pattern_lengths if l >=3], reverse=False) # Check shorter first
        elif choppiness_rate < 0.3: 
            lengths_to_check = sorted([l for l in all_pattern_lengths if l >=3], reverse=True) # Check longer first
        else: 
            lengths_to_check = sorted([l for l in all_pattern_lengths if l >=3], reverse=True) # Default behavior (longer down to shorter)

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


# --- Derived Road Analyzer ---
class DerivedRoadAnalyzer:
    """
    Analyzes Big Road to derive Big Eye Boy, Small Road, and Cockroach Pig patterns
    and makes predictions based on their trends.
    """
    def _build_big_road_matrix(self, history_pb: List[MainOutcome]) -> List[List[Optional[MainOutcome]]]:
        """
        Builds a matrix representation of the Big Road.
        Each column represents a streak.
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
        
        # Max rows for Big Road is 6 as per user's request (แนวตั้ง 6 ตัว)
        max_rows = 6 
        padded_matrix = []
        for col in matrix:
            padded_col = col + [None] * (max_rows - len(col))
            padded_matrix.append(padded_col)

        return padded_matrix

    def _get_big_eye_boy_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Big Eye Boy value for a given cell (col_idx, row_idx) in the Big Road matrix.
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
        
        # Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 2 and len(matrix[col_idx-2]) == 1:
            return "P" # Blue (indicates a chop/alternation in the derived road)
        
        return None

    def _get_small_road_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Small Road value for a given cell (col_idx, row_idx) in the Big Road matrix.
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

        # Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 1 and len(matrix[col_idx-1]) == 1:
            return "P" # Blue (indicates a chop/alternation in the derived road)

        return None

    def _get_cockroach_pig_value(self, matrix: List[List[Optional[MainOutcome]]], col_idx: int, row_idx: int) -> Optional[MainOutcome]:
        """
        Calculates Cockroach Pig value for a given cell (col_idx, row_idx) in the Big Road matrix.
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

        # Additional check for very short columns (e.g., singletons)
        if row_idx == 0 and col_idx >= 1 and len(matrix[col_idx-1]) == 1: 
            return "P" # Blue (indicates a chop/alternation in the derived road)
        
        return None

    def predict(self, history: List[RoundResult]) -> Dict[str, Optional[MainOutcome]]:
        """
        Simulates predictions for the next P or B to determine derived road values.
        """
        predictions: Dict[str, Optional[MainOutcome]] = {"BigEyeBoy": None, "SmallRoad": None, "CockroachPig": None} # Initialize all to None
        
        history_pb = _get_main_outcome_history(history)
        
        if not history_pb: 
            return predictions # Return initialized None predictions

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

        max_rows = 6 # Standard height for derived road display (matched to Big Road)

        for col_idx in range(len(big_road_matrix)):
            beb_col: List[Optional[MainOutcome]] = []
            sr_col: List[Optional[MainOutcome]] = []
            cp_col: List[Optional[MainOutcome]] = [] # Corrected type hint
            
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
    
    def _flatten_derived_road_matrix(self, matrix: List[List[Optional[MainOutcome]]], lookback_cols: int = 10) -> List[MainOutcome]:
        """Flattens the last N columns of a derived road matrix into a single list of non-None outcomes."""
        flattened_list = []
        if not matrix:
            return []
        
        # Iterate through columns in reverse to get recent history
        # Ensure we don't go out of bounds
        start_col_idx = max(0, len(matrix) - lookback_cols)
        
        for col_idx in range(start_col_idx, len(matrix)):
            for row_idx in range(len(matrix[col_idx])):
                if matrix[col_idx][row_idx] is not None:
                    flattened_list.append(matrix[col_idx][row_idx]) # Append to maintain chronological order
        return flattened_list

    def analyze_derived_road_trends(self, history: List[RoundResult]) -> Dict[str, str]:
        """
        Analyzes the trends in Big Eye Boy, Small Road, and Cockroach Pig
        and returns textual descriptions.
        """
        trends = {
            "BigEyeBoy": "ไม่มีแนวโน้ม",
            "SmallRoad": "ไม่มีแนวโน้ม",
            "CockroachPig": "ไม่มีแนวโน้ม"
        }

        derived_matrices = self.get_full_derived_road_matrices(history)

        for road_key, matrix in derived_matrices.items():
            road_name = road_key.replace("Matrix", "") # e.g., "BigEyeBoy"
            
            if not matrix or len(matrix) < 2: # Need at least 2 columns in derived road matrix
                continue

            # Get the actual derived road values as a flat list
            road_values = self._flatten_derived_road_matrix(matrix, lookback_cols=10) # Look back last 10 columns

            if len(road_values) < 4: # Need at least 4 values for clear patterns
                continue

            # Check for Ping Pong (alternating)
            is_ping_pong = True
            for i in range(1, len(road_values)):
                if road_values[i] == road_values[i-1]:
                    is_ping_pong = False
                    break
            if is_ping_pong and len(road_values) >= 4:
                trends[road_name] = "ปิงปอง"
                continue

            # Check for Dragon (streak)
            is_dragon = True
            first_val = road_values[0]
            for i in range(1, len(road_values)):
                if road_values[i] != first_val:
                    is_dragon = False
                    break
            if is_dragon and len(road_values) >= 4:
                trends[road_name] = "มังกร"
                continue
            
            # Check for Two-in-a-row (สองตัวติด)
            if len(road_values) >= 4:
                last_four = "".join(road_values[-4:])
                if last_four in ["PPBB", "BBPP"]:
                    trends[road_name] = "สองตัวติด"
                    continue

            # Check for Chop-Two (สองตัวตัด)
            if len(road_values) >= 3:
                last_three = "".join(road_values[-3:])
                if last_three in ["PBB", "BPP"]:
                    trends[road_name] = "สองตัวตัด"
                    continue
            
            # Check for Pair-Alternating (คู่สลับ)
            if len(road_values) >= 4:
                last_four = "".join(road_values[-4:])
                if last_four in ["PBBP", "BPPB"]:
                    trends[road_name] = "คู่สลับ"
                    continue

        return trends


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
                
                if follow_up_outcome in self.sequence_outcomes[sequence]: # Corrected to check in self.sequence_outcomes[sequence]
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
    """
    def score(self, 
              predictions: Dict[str, Optional[MainOutcome]], 
              module_accuracies_all_time: Dict[str, float], 
              module_accuracies_recent: Dict[str, float], 
              history: List[RoundResult],
              current_miss_streak: int, # This is the *displayed* miss streak
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
            
            # Simplified weighting logic after module reduction
            if name in ["BigEyeBoy", "SmallRoad", "CockroachPig"] and predictions.get(name) is not None:
                base_derived_weight = 0.8 
                if choppiness_rate > 0.6: 
                    weight += base_derived_weight * 1.5 
                elif choppiness_rate < 0.4: 
                    weight += base_derived_weight * 1.0
                else: 
                    weight += base_derived_weight * 1.2
            
            # Dynamic module weighting based on choppiness
            if choppiness_rate > 0.6: # More choppy
                if name in ["BigEyeBoy", "SmallRoad", "CockroachPig"]: 
                    weight *= 1.3 
                elif name in ["Trend", "Rule", "Pattern", "Statistical"]: 
                    weight *= 0.8 
            elif choppiness_rate < 0.4: # More streaky
                if name in ["Trend", "Rule", "Pattern", "Statistical"]: 
                    weight *= 1.3 
                elif name in ["BigEyeBoy", "SmallRoad", "CockroachPig"]: 
                    weight *= 0.8 
            else: # Moderate choppiness
                if name in ["BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"]: 
                    weight *= 1.1 
                elif name == "Fallback":
                    weight *= 1.05 
                else:
                    weight *= 0.95 
            
            # Specific weighting for Statistical module
            if name == "Statistical" and predictions.get(name) is not None:
                if choppiness_rate > 0.5: # Give more weight in balanced/choppy scenarios
                    weight *= 1.2
                else:
                    weight *= 1.05 # Slight boost in streaky too

            # Miss streak penalty applies to internal confidence, not just displayed
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
        
        if consensus_count >= 4: # Adjusted consensus count for fewer modules
            raw_confidence *= 1.15 
        elif consensus_count >= 2:
            raw_confidence *= 1.08 
        elif consensus_count >= 1:
            raw_confidence *= 1.02 

        confidence = min(int(raw_confidence), 95)

        # Dynamic Confidence Threshold based on Choppiness Rate
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
            # Corrected: Use filtered_history for length check, and joined_filtered for string operations
            last_6 = "".join(filtered_history[-6:])
            if last_6 == "PBPBPB" or last_6 == "BPBPBP":
                return "ปิงปองยาว"

        # Other common patterns (simplified list)
        common_patterns = {
            "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
            "PBB": "สองตัวตัด", "BPP": "สองตัวตัด", 
            "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
            # V10.5.3: Added names for complex mixed patterns
            "PBBPPP": "สองตัดสาม", # P then BB then PPP
            "BPPBBB": "สองตัดสาม", # B then PP then BBB
        }
        for length in range(max(len(p) for p in common_patterns.keys()) if common_patterns else 2, 2, -1): 
            if len(joined_filtered) >= length:
                current_pattern_str = joined_filtered[-length:]
                if current_pattern_str in common_patterns:
                    return common_patterns[current_pattern_str]
        
        return None


class OracleBrain:
    def __init__(self):
        self.history: List[RoundResult] = [] 
        self.prediction_log: List[Optional[MainOutcome]] = [] # Now stores *displayed* predictions (P/B or None)
        self.result_log: List[MainOutcome] = [] 
        
        self.last_internal_prediction: Optional[MainOutcome] = None # Stores the internal prediction for the *next* round's recovery check
        self.last_module: Optional[str] = None 

        # Global logs for all-time accuracy (NOT persistent in this version by default, but can be saved/loaded)
        self.module_accuracy_global_log: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "Fallback": [], 
            "BigEyeBoy": [], "SmallRoad": [], "CockroachPig": [], "Statistical": [] 
        }
        self.tie_module_accuracy_global_log: List[Tuple[Optional[Literal["T"]], bool]] = [] 

        # Per-shoe logs for recent accuracy and current shoe display
        self.individual_module_prediction_log_current_shoe: Dict[str, List[Tuple[MainOutcome, MainOutcome]]] = {
            "Rule": [], "Pattern": [], "Trend": [], "Fallback": [], 
            "BigEyeBoy": [], "SmallRoad": [], "CockroachPig": [], "Statistical": [] 
        }
        self.tie_module_prediction_log_current_shoe: List[Tuple[Optional[Literal["T"]], bool]] = [] 

        # Initialize all prediction modules (P/B) - Simplified list
        self.rule_engine = RuleEngine()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_scanner = TrendScanner()
        self.fallback_module = FallbackModule() 
        self.derived_road_analyzer = DerivedRoadAnalyzer() 
        self.statistical_analyzer = StatisticalAnalyzer() 

        # Initialize side bet prediction modules
        self.tie_predictor = TiePredictor()

        self.scorer = AdaptiveScorer() 
        self.show_initial_wait_message = True
        
    def add_result(self, main_outcome: MainOutcome, is_any_natural: bool = False, displayed_prediction_for_prev_round: Optional[MainOutcome] = None, 
                   internal_module_predictions: Dict[str, Optional[MainOutcome]] = None, internal_tie_prediction: Optional[Literal["T"]] = None): # Added new parameters
        """
        Adds a new actual outcome to history and logs,
        and updates module accuracy based on the last prediction.
        `displayed_prediction_for_prev_round` is the P/B/None that was *shown* to the user for the round that just ended.
        `internal_module_predictions` are the raw predictions from each module for the round that just ended.
        `internal_tie_prediction` is the raw tie prediction for the round that just ended.
        """
        new_round_result = RoundResult(main_outcome, is_any_natural)
        
        # --- Record individual main P/B module predictions (internal accuracy) ---
        if internal_module_predictions:
            for module_name, pred_val in internal_module_predictions.items():
                if module_name in self.module_accuracy_global_log:
                    # Only log P/B predictions for P/B outcomes
                    if pred_val in ("P", "B") and main_outcome in ("P", "B"):
                        self.module_accuracy_global_log[module_name].append((pred_val, main_outcome))
                        self.individual_module_prediction_log_current_shoe[module_name].append((pred_val, main_outcome))
                elif module_name in ["BigEyeBoy", "SmallRoad", "CockroachPig"] and pred_val in ("P", "B") and main_outcome in ("P", "B"):
                    # Derived roads are also main outcomes
                    self.module_accuracy_global_log[module_name].append((pred_val, main_outcome))
                    self.individual_module_prediction_log_current_shoe[module_name].append((pred_val, main_outcome))


        # Record Tie module prediction
        if internal_tie_prediction is not None:
            is_actual_tie = (main_outcome == "T")
            self.tie_module_accuracy_global_log.append((internal_tie_prediction, is_actual_tie))
            self.tie_module_prediction_log_current_shoe.append((internal_tie_prediction, is_actual_tie))


        # Now, add the actual outcome to main history and logs
        self.history.append(new_round_result) 
        self.result_log.append(main_outcome) 
        
        # Store the *displayed* prediction for the previous round.
        # This is what the miss_streak should be based on.
        self.prediction_log.append(displayed_prediction_for_prev_round) 

        # Update StatisticalAnalyzer's internal history
        self.statistical_analyzer.update_sequence_history(_get_main_outcome_history(self.history))

        self._trim_global_logs() 

    def remove_last(self):
        if self.history: self.history.pop()
        if self.result_log: self.result_log.pop()
        if self.prediction_log: self.prediction_log.pop() # Pop from displayed predictions log
        
        # For internal module accuracy logs, we also need to pop the last entry
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
        
        # Re-initialize StatisticalAnalyzer to clear its history (simpler than reverse-updating)
        self.statistical_analyzer = StatisticalAnalyzer()
        self.statistical_analyzer.update_sequence_history(_get_main_outcome_history(self.history)) # Rebuild from current history

    def reset_all_data(self):
        """
        This method now explicitly resets ALL data, including global and current shoe accuracy logs.
        Use with caution, typically for a full system restart or debugging.
        """
        self.history.clear()
        self.prediction_log.clear() # Clear displayed predictions log
        self.result_log.clear()
        
        # Clear all accuracy logs
        for module_name in self.module_accuracy_global_log:
            self.module_accuracy_global_log[module_name].clear()
        self.tie_module_accuracy_global_log.clear()

        for module_name in self.individual_module_prediction_log_current_shoe:
            self.individual_module_prediction_log_current_shoe[module_name].clear()
        self.tie_module_prediction_log_current_shoe.clear()

        self.last_internal_prediction = None # Reset internal prediction
        self.last_module = None
        self.show_initial_wait_message = True
        
        # Reset StatisticalAnalyzer
        self.statistical_analyzer = StatisticalAnalyzer()

    def start_new_shoe(self):
        """
        This method resets the current shoe's history and prediction logs,
        but retains the global historical accuracy data of the modules.
        """
        self.history.clear()
        self.prediction_log.clear() # Clear displayed predictions log
        self.result_log.clear()
        
        # Clear only current shoe accuracy logs
        for module_name in self.individual_module_prediction_log_current_shoe:
            self.individual_module_prediction_log_current_shoe[module_name].clear()
        self.tie_module_prediction_log_current_shoe.clear()

        self.last_internal_prediction = None # Reset internal prediction
        self.last_module = None
        self.show_initial_wait_message = True
        
        # Reset StatisticalAnalyzer for new shoe
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

        # Import statistical analyzer data
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
        main_modules = ["Rule", "Pattern", "Trend", "Fallback", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] 
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
        main_modules = ["Rule", "Pattern", "Trend", "Fallback", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] 
        for module_name in main_modules:
            if module_name in self.individual_module_prediction_log_current_shoe:
                accuracy_results[module_name] = self._calculate_main_module_accuracy_from_log(self.individual_module_prediction_log_current_shoe[module_name], lookback)
            else:
                accuracy_results[module_name] = 0.0 
        
        accuracy_results["Tie"] = self._calculate_side_bet_module_accuracy_from_log(self.tie_module_prediction_log_current_shoe, lookback)

        return accuracy_results

    def get_module_accuracy_normalized(self) -> Dict[str, float]:
        acc = self.get_module_accuracy_all_time() 
        all_known_modules_for_norm = ["Rule", "Pattern", "Trend", "Fallback", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical", "Tie"] 
        
        if not acc:
            return {name: 0.5 for name in all_known_modules_for_norm}
        
        active_main_accuracies = {k: v for k, v in acc.items() if k in ["Rule", "Pattern", "Trend", "BigEyeBoy", "SmallRoad", "CockroachPig", "Statistical"] and v > 0} 
        
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
        Calculates the current consecutive miss streak for *displayed/recommended* P/B predictions.
        This is used for Martingale progression.
        """
        streak = 0
        # Iterate backwards through prediction_log (which now stores displayed predictions)
        # and result_log
        for displayed_pred, actual_result in zip(reversed(self.prediction_log), reversed(self.result_log)):
            if displayed_pred is None or actual_result == "T": # If no bet was recommended, or it was a Tie, it doesn't count as a miss or win for P/B streak
                continue
            
            if displayed_pred != actual_result:
                streak += 1
            else: # If the recommended bet was correct, the streak breaks
                break 
        return streak


    def predict_next(self) -> Tuple[ # Removed strict_mode parameter
        Optional[MainOutcome], Optional[str], Optional[int], Optional[str], int, bool, 
        Optional[Literal["T"]], Optional[int], 
        bool, str, Dict[str, str], Dict[str, Optional[MainOutcome]], Optional[Literal["T"]] # Added raw internal predictions
    ]:
        """
        Generates the next predictions for main outcome and side bets,
        along with main outcome's source, confidence, miss streak, and Sniper opportunity flag.
        Returns raw internal predictions for logging.
        """
        main_history_filtered_for_pb = _get_main_outcome_history(self.history)
        p_count = main_history_filtered_for_pb.count("P")
        b_count = main_history_filtered_for_pb.count("B")
        
        # Calculate miss streak based on *displayed* predictions
        current_displayed_miss_streak = self.calculate_miss_streak()

        MIN_HISTORY_FOR_PREDICTION = 15 
        
        MIN_HISTORY_FOR_SNIPER = 25 
        MIN_HISTORY_FOR_SIDE_BET_SNIPER = 25 
        
        RECOMMEND_BET_CONFIDENCE_THRESHOLD = 65 
        MIN_DISPLAY_CONFIDENCE_SIDE_BET = 55 

        # New constants for recovery logic
        RECOVERY_INTERNAL_WINS_TO_RE_ENABLE_BETTING = 1 # ทำนายภายในต้องถูก 1 ตา
        RECOVERY_NO_BET_ROUNDS = 2 # งดเดิมพัน 2 ตา

        derived_road_trends = self.derived_road_analyzer.analyze_derived_road_trends(self.history)

        # Calculate raw internal predictions for all modules first
        choppiness_rate = self._calculate_choppiness_rate(self.history, 20) 
        raw_predictions_from_modules = { # Renamed to raw_predictions_from_modules
            "Rule": self.rule_engine.predict(self.history),
            "Pattern": self.pattern_analyzer.predict(self.history, choppiness_rate), 
            "Trend": self.trend_scanner.predict(self.history, choppiness_rate), 
            "Fallback": self.fallback_module.predict(self.history, current_displayed_miss_streak), # Pass displayed miss streak to fallback
            "Statistical": self.statistical_analyzer.predict(self.history) 
        }
        
        derived_road_preds = self.derived_road_analyzer.predict(self.history)
        raw_predictions_from_modules.update(derived_road_preds)

        # Calculate raw tie prediction
        raw_tie_pred, raw_tie_conf = self.tie_predictor.predict(self.history)

        # --- High Priority: Game Break (6 consecutive misses on *displayed* bets) ---
        if current_displayed_miss_streak >= 6:
            st.session_state.in_recovery_mode = False # Exit recovery if game breaks completely
            st.session_state.consecutive_recovery_wins = 0
            st.session_state.rounds_in_recovery_no_bet = 0 # Reset no-bet counter
            self.last_internal_prediction = None # Clear internal prediction for next round
            self.last_module = None
            return None, None, None, None, current_displayed_miss_streak, False, None, None, False, \
                   "🚨 เกมแตก! (แพ้ 6 ไม้ติด) - แนะนำให้ 'เริ่มขอนใหม่' หรือ 'รีเซ็ตข้อมูลทั้งหมด' เพื่อเริ่มเกมใหม่", \
                   derived_road_trends, raw_predictions_from_modules, raw_tie_pred # Return raw predictions

        # --- Initial learning phase ---
        if (p_count + b_count) < MIN_HISTORY_FOR_PREDICTION:
            self.last_internal_prediction = None
            self.last_module = None
            st.session_state.in_recovery_mode = False # Ensure not in recovery during learning
            st.session_state.consecutive_recovery_wins = 0
            st.session_state.rounds_in_recovery_no_bet = 0 # Reset no-bet counter
            return None, None, None, None, current_displayed_miss_streak, False, None, None, False, \
                   "กำลังเรียนรู้... รอข้อมูลครบ 15 ตา (P/B) ก่อนเริ่มทำนาย", derived_road_trends, raw_predictions_from_modules, raw_tie_pred # Return raw predictions

        # Score the internal prediction
        internal_prediction_outcome, internal_source_module, internal_confidence, internal_pattern_code = \
            self.scorer.score(raw_predictions_from_modules, module_accuracies_all_time, module_accuracies_recent_10, self.history, current_displayed_miss_streak, choppiness_rate) 

        # --- IMPORTANT: Always store this internal prediction ---
        # This ensures that `st.session_state.last_internal_prediction_outcome` has a value
        # for the next `handle_click` call, even if the displayed recommendation is "No Bet".
        self.last_internal_prediction = internal_prediction_outcome
        self.last_module = internal_source_module

        # --- Recovery Mode Logic ---

        # Determine if we should ENTER recovery mode
        if current_displayed_miss_streak >= 3 and not st.session_state.in_recovery_mode:
            st.session_state.in_recovery_mode = True
            st.session_state.consecutive_recovery_wins = 0 # Reset when *entering* recovery
            st.session_state.rounds_in_recovery_no_bet = 0 # NEW: Initialize no-bet counter when entering recovery
            st.session_state.recommendation_text = f"🧪 เริ่มกระบวนการฟื้นฟู: งดเดิมพัน ({st.session_state.rounds_in_recovery_no_bet}/{RECOVERY_NO_BET_ROUNDS} ตา)"
            return None, None, None, None, current_displayed_miss_streak, False, None, None, False, \
                   st.session_state.recommendation_text, derived_road_trends, raw_predictions_from_modules, raw_tie_pred # Return raw predictions

        # If currently in recovery mode (triggered by miss streak)
        if st.session_state.in_recovery_mode:
            # Phase 1: Enforce "no bet" for the initial X rounds
            if st.session_state.rounds_in_recovery_no_bet < RECOVERY_NO_BET_ROUNDS:
                st.session_state.recommendation_text = f"🧪 อยู่ในช่วงฟื้นฟู: งดเดิมพัน ({st.session_state.rounds_in_recovery_no_bet}/{RECOVERY_NO_BET_ROUNDS} ตา)"
                return None, None, None, None, current_displayed_miss_streak, False, None, None, False, \
                       st.session_state.recommendation_text, derived_road_trends, raw_predictions_from_modules, raw_tie_pred # Return raw predictions
            
            # Phase 2: After initial no-bet rounds, check for internal wins to re-enable betting
            if st.session_state.consecutive_recovery_wins >= RECOVERY_INTERNAL_WINS_TO_RE_ENABLE_BETTING:
                # We are now confident enough to start recommending bets again.
                # The system will FALL THROUGH to the normal recommendation logic below.
                # miss_streak will reset when a *recommended* bet wins.
                pass # Continue to normal recommendation logic
            else:
                # Still in recovery, not met internal win conditions yet.
                # Explicitly recommend no bet.
                st.session_state.recommendation_text = f"🧪 อยู่ในช่วงฟื้นฟู: ทำนายภายในต้องถูก 1 ตา"
                return None, None, None, None, current_displayed_miss_streak, False, None, None, False, \
                       st.session_state.recommendation_text, derived_road_trends, raw_predictions_from_modules, raw_tie_pred # Return raw predictions

        # --- Normal Recommendation Logic (after exiting Recovery Phase 2 or if never in Recovery) ---
        # This part will now handle both "confident prediction" and "low confidence no bet"
        
        final_prediction_main = internal_prediction_outcome # Use the internally scored prediction
        source_module_name_main = internal_source_module
        confidence_main = internal_confidence
        pattern_code_main = internal_pattern_code

        # Determine the recommendation text and final_prediction_main for display
        if final_prediction_main is not None and confidence_main is not None and confidence_main >= RECOMMEND_BET_CONFIDENCE_THRESHOLD:
            color_style = "color: #007BFF;" if final_prediction_main == "P" else "color: #DC3545;"
            recommendation_text = f"✅ แนะนำ: <span style='{color_style}'>{final_prediction_main}</span>"
            
            # If miss_streak is 0 here, it means a previous recommended bet won.
            # This is the point where we fully exit recovery mode.
            if current_displayed_miss_streak == 0 and st.session_state.in_recovery_mode: # Only exit if *in* recovery
                st.session_state.in_recovery_mode = False
                st.session_state.consecutive_recovery_wins = 0 # Reset wins counter
                st.session_state.rounds_in_recovery_no_bet = 0 # NEW: Reset no-bet counter on full exit
                # No need to change recommendation_text here, it's already set to "✅ แนะนำ".
        else:
            # If confidence is below threshold, or no prediction, recommend no bet
            # This applies both outside recovery and *within* recovery (if internal wins threshold not met)
            if choppiness_rate > 0.65:
                recommendation_text = "🚫 งดเดิมพัน: เค้าไพ่ผันผวนสูง"
            else:
                recommendation_text = "🚫 งดเดิมพัน: ยังไม่พบแพทเทิร์นชัดเจน"
            
            final_prediction_main = None # Ensure no prediction is returned for display
            source_module_name_main = None
            confidence_main = None
            pattern_code_main = None

        # --- Main Outcome Sniper Opportunity Logic ---
        is_sniper_opportunity_main = False # Default to False
        if final_prediction_main in ("P", "B") and confidence_main is not None:
            if confidence_main >= 70 and current_displayed_miss_streak <= 2 and (p_count + b_count) >= MIN_HISTORY_FOR_SNIPER: 
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
                
                if high_accuracy_contributing_count >= 2: # Adjusted for fewer modules
                    is_sniper_opportunity_main = True
        # --- END Main Outcome Sniper Logic ---

        # --- Side Bet Predictions with Confidence ---
        tie_prediction = None
        tie_confidence = None
        is_tie_sniper_opportunity = False

        # Use raw_tie_pred, raw_tie_conf from earlier calculation
        tie_pred_raw, tie_conf_raw = raw_tie_pred, raw_tie_conf

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
            final_prediction_main, source_module_name_main, confidence_main, pattern_code_main, current_displayed_miss_streak, is_sniper_opportunity_main,
            tie_prediction, tie_confidence, 
            is_tie_sniper_opportunity, recommendation_text, derived_road_trends, raw_predictions_from_modules, raw_tie_pred
        )

# --- Streamlit UI Code ---

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle V10.6.7", layout="centered") # Updated version to V10.6.7

# --- Custom CSS for Styling ---
st.markdown("""
<style>
/* Import Sarabun font from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

html, body, [class*="st-emotion"] { /* Target Streamlit's main content div classes */
    font-family: 'Sarabun', sans-serif !important;
}
.header-container {
    text-align: center;
    margin-bottom: 0px; /* Further reduced margin */
}
.main-title {
    font-size: 38px; /* Same size as before */
    font-weight: bold;
    color: #FF4B4B; /* Streamlit's default primary color */
    display: inline-block; /* Allow version text next to it */
    margin-right: 5px; /* Space between Oracle and version */
}
.version-text {
    font-size: 12px; /* Same size as before */
    color: #BBBBBB; /* Lighter color */
    display: inline-block;
}

.predict-box {
    padding: 2px; /* Same as before */
    background-color: #262730; /* Darker background for the box */
    border-radius: 5px; /* Same as before */
    color: white;
    margin-bottom: 2px; /* Same as before */
    box-shadow: 0 1.5px 3px rgba(0, 0, 0, 0.2); /* Same as before */
    text-align: center; /* Center content inside prediction box */
    border: 1px solid #FFD700; /* Gold border for prediction box */
}
.predict-box h2 {
    margin: 0px 0; /* Same as before */
    font-size: 18px; /* Significantly increased for main recommendation */
    font-weight: bold;
    line-height: 1.2; /* Adjust line height for better spacing */
}
.predict-box b {
    color: #FFD700; /* Gold color for emphasis */
}
.predict-box .st-emotion-cache-1c7y2vl { /* Target Streamlit's caption */
    font-size: 8px; /* Slightly increased for readability */
    color: #BBBBBB;
    line-height: 1.2; /* Adjust line height for better spacing */
    margin-top: 0px; /* Ensure no extra margin */
    margin-bottom: 0px; /* Ensure no extra margin */
}

/* Miss Streak warning text */
.miss-streak-container {
    background-color: #333333; /* Darker background for the miss streak box */
    border: none !important; /* Removed all borders */
    border-radius: 0px; /* Removed border-radius for sharp edges */
    padding: 2px; /* Same as before */
    margin: 2px auto; /* Same as before */
    max-width: 60%; /* Same as before */
    text-align: center;
    box-shadow: none; /* Removed shadow */
}
.miss-streak-text p { /* Custom class for miss streak text */
    font-size: 9px !important; /* Same as before */
    margin-bottom: 0px !important; /* Same as before */
    color: #FFC107; /* Warning color for miss streak */
    font-weight: bold;
}
.st-emotion-cache-1f1d6zpt { /* Warning box */
    background-color: #FFC10720; 
    border-left: 2px solid #FFC107; 
    color: #FFC107;
    padding: 4px; /* Same as before */
    margin-bottom: 4px; /* Same as before */
    font-size: 9px; /* Same as before */
}
.st-emotion-cache-1s04v0m { /* Error box */
    background-color: #DC354520; 
    border-left: 2px solid #DC3545; 
    color: #DC3545;
    padding: 4px; /* Same as before */
    margin-bottom: 4px; /* Same as before */
    font-size: 9px; /* Same as before */
}
.st-emotion-cache-13ln4z2 { /* Info box */
    background-color: #17A2B820; 
    border-left: 2px solid #17A2B8; 
    color: #17A2B8;
    padding: 4px; /* Same as before */
    margin-bottom: 4px; /* Same as before */
    font-size: 9px; /* Same as before */
}


.big-road-container {
    width: 100%;
    overflow-x: auto; /* Allows horizontal scrolling if many columns */
    padding: 1px 0; /* Same as before */
    background: #1A1A1A; /* Same as before */
    border-radius: 3px; /* Same as before */
    white-space: nowrap; /* Keeps columns in a single line */
    display: flex; /* Use flexbox for columns */
    flex-direction: row; /* Display columns from left to right */
    align-items: flex-start; /* Align columns to the top */
    min-height: 132px; /* Adjusted minimum height for 6 rows with slightly smaller cells */
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.3); /* Same as before */
}
.big-road-column {
    display: inline-flex; /* Use inline-flex for vertical stacking within column */
    flex-direction: column;
    margin-right: 0.1px; /* Same as before */
    border-right: 1px solid rgba(255,255,255,0.01); /* Same as before */
    padding-right: 0.1px; /* Same as before */
}
.big-road-cell {
    width: 20px; /* Adjusted to be smaller by 1 level (from 22px) */
    height: 20px; /* Adjusted to be smaller by 1 level (from 22px) */
    text-align: center;
    line-height: 20px; /* Adjusted line-height for new size */
    font-size: 16px; /* Adjusted to be smaller by 1 level (from 18px) */
    margin-bottom: 0.5px; /* Same as before */
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
    font-size: 11px; /* Increased by 1 level (from 10px) */
    position: absolute;
    bottom: -4px; /* Adjusted position */
    right: -4px; /* Adjusted position */
    background-color: #FFD700; /* Gold background for prominence */
    color: #333; /* Dark text for contrast */
    border-radius: 50%;
    padding: 0px 4px; /* Adjusted padding */
    line-height: 1;
    min-width: 18px; /* Adjusted min-width for single digit */
    text-align: center;
    box-shadow: 0 0.25px 0.5px rgba(0,0,0,0.2); /* Same as before */
}
/* Styling for Natural indicator in Big Road (New for V6.5) */
.natural-indicator {
    position: absolute;
    font-size: 10px; /* Increased by 1 level (from 9px) */
    font-weight: bold;
    color: white;
    line-height: 1;
    padding: 0.6px 1.8px; /* Adjusted padding */
    border-radius: 1.8px; /* Adjusted border-radius */
    z-index: 10;
    background-color: #4CAF50; /* Green for Natural */
    top: -4px; /* Adjusted position */
    right: -4px; /* Adjusted position */
}

/* Derived Road Trend Box Styles (NEW) */
.derived-trend-box {
    background-color: #333333; /* Default background for no trend */
    color: white;
    padding: 6px 12px; /* Increased padding for oval shape */
    border-radius: 25px; /* High border-radius for oval shape */
    font-size: 12px; /* Adjusted font size */
    font-weight: bold;
    text-align: center;
    margin-bottom: 4px; /* Spacing between boxes */
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    display: inline-block; /* Make it inline-block to fit content */
    line-height: 1.2;
}
.derived-trend-box.clear-trend {
    background-color: #28A745; /* Green for clear trend (e.g., สองตัวติด, สองตัวตัด, คู่สลับ) */
}
.derived-trend-box.ping-pong {
    background-color: #007BFF; /* Blue for Ping Pong */
}
.derived-trend-box.dragon {
    background-color: #DC3545; /* Red for Dragon */
}
.derived-trend-box.no-trend { /* New class for "ไม่มีแนวโน้ม" */
    background-color: #6C757D; /* Grey for no trend */
}


/* Button styling */
.stButton>button {
    width: 100%;
    border-radius: 4px; /* Same as before */
    font-size: 10px; /* Same as before */
    font-weight: bold;
    padding: 4px 0; /* Same as before */
    margin-bottom: 2px; /* Same as before */
    transition: all 0.2s ease-in-out;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1); /* Same as before */
    background-color: #4CAF50; /* Green for general buttons */
    color: white;
    border: none;
}
.stButton>button:hover {
    transform: translateY(-0.25px); /* Same as before */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2); 
}
/* Specific button colors */
#btn_P button { background-color: #007BFF; color: white; border: none; }
#btn_B button { background-color: #DC3545; color: white; border: none; }
#btn_T button { background-color: #6C757D; color: white; border: none; }

/* Secondary buttons like download/upload */
.stButton button[kind="secondary"] { 
    background-color: #343A40;
    color: white;
    border: 1px solid #495057;
}
.stButton button[kind="secondary"]:hover {
    background-color: #495057;
}

/* Checkbox styling adjustments */
.stCheckbox > label {
    padding: 2px 4px; /* Same as before */
    border: 1px solid #495057;
    border-radius: 3px; /* Same as before */
    background-color: #343A40;
    color: white;
    font-size: 9px; /* Same as before */
    font-weight: bold;
    margin-bottom: 2px; /* Same as before */
    display: flex; 
    align-items: center;
    justify-content: flex-start; /* Align text to start */
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}
.stCheckbox > label:hover {
    background-color: #495057;
    transform: translateY(-0.25px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
.stCheckbox > label > div:first-child { 
    margin-right: 2px; /* Same as before */
}
/* Style for checked checkboxes */
.stCheckbox > label[data-checked="true"] {
    background-color: #007BFF; 
    border-color: #007BFF;
}


/* Sniper message styling */
.sniper-message {
    background-color: #4CAF50; 
    color: white;
    padding: 6px; /* Same as before */
    border-radius: 5px; /* Same as before */
    font-weight: bold;
    text-align: center;
    margin-top: 5px; /* Same as before */
    margin-bottom: 5px; /* Same as before */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4); /* Same as before */
    animation: pulse 1.5s infinite; 
    font-size: 14px; /* Same as before */
    line-height: 1.2;
}

/* NEW: Side Bet Sniper message styling */
.side-bet-sniper-message {
    background-color: #007bff; 
    color: white;
    padding: 6px; /* Same as before */
    border-radius: 5px; /* Same as before */
    font-weight: bold;
    text-align: center;
    margin-top: 5px; /* Same as before */
    margin-bottom: 5px; /* Same as before */
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3); /* Same as before */
    animation: pulse 1.5s infinite; 
    font-size: 14px; /* Same as before */
    line-height: 1.2;
}


@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.001); opacity: 0.995; } 
    100% { transform: scale(1); opacity: 1; }
}


/* Removed all hr tags and borders */
hr {
    display: none; /* Hide all hr elements */
}

/* General spacing for headers */
h3 { 
    font-size: 10px !important; /* Same as before */
    margin-top: 2px !important; /* Same as before */
    margin-bottom: 1px !important; /* Same as before */
}
h4 {
    font-size: 10px !important; /* Same as before */
    margin-top: 2px !important; /* Same as before */
    margin-bottom: 1px !important; /* Same as before */
}
h5 {
    font-size: 9px !important; /* Same as before */
    margin-top: 1px !important; /* Same as before */
    margin-bottom: 0px !important; /* Same as before */
}

/* General paragraph text for captions etc. */
p {
    margin-bottom: 0px !important; /* Same as before */
    font-size: 9px; /* Same as before */
}

/* Adjust Streamlit's default elements to reduce spacing */
.st-emotion-cache-1r6dm1s { /* This is often a container for columns, adjust its padding */
    padding-top: 0rem;
    padding-bottom: 0rem;
}
.st-emotion-cache-1v0mbdj { /* Another common container for elements */
    padding-top: 0rem;
    padding-bottom: 0rem;
}
.st-emotion-cache-1oe5f0g { /* Padding around elements */
    padding: 0.01rem 0.01rem; /* Drastically reduced padding */
}
.st-emotion-cache-1c7y2vl { /* Caption text */
    margin-top: 0px;
    margin-bottom: 0px;
    font-size: 8px; /* Same as before */
}
.st-emotion-cache-1g62nvv { /* General text element */
    margin-bottom: 0px;
}
.st-emotion-cache-1kyx06k { /* Column padding */
    padding-left: 0.01rem; /* Drastically reduced padding */
    padding-right: 0.01rem; /* Drastically reduced padding */
}
.st-emotion-cache-1av225b { /* Column padding */
    padding-left: 0.01rem; /* Drastically reduced padding */
    padding-right: 0.01rem; /* Drastically reduced padding */
}

/* Remove default Streamlit padding from main content area (if any) */
.st-emotion-cache-z5fcl4 { /* This class often controls the main content padding */
    padding-left: 0rem;
    padding-right: 0rem;
    padding-top: 0rem;
    padding-bottom: 0rem;
}
.st-emotion-cache-16txto3 { /* Another potential main container class */
    padding-left: 0rem;
    padding-right: 0rem;
    padding-top: 0rem;
    padding-bottom: 0rem;
}
.st-emotion-cache-1jmveps { /* Another potential container for columns */
    padding-left: 0rem;
    padding-right: 0rem;
}

/* Remove border from miss-streak-container */
.miss-streak-container {
    border: none !important;
}

</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'oracle' not in st.session_state:
    st.session_state.oracle = OracleBrain()
if 'prediction' not in st.session_state: 
    st.session_state.prediction = None # This now stores the *displayed* prediction for the current round
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
if 'show_accuracy_info' not in st.session_state: # New state for accuracy toggle
    st.session_state.show_accuracy_info = False
if 'debug_messages' not in st.session_state: # New state for storing debug messages
    st.session_state.debug_messages = []

if 'in_recovery_mode' not in st.session_state: # Recovery mode state
    st.session_state.in_recovery_mode = False
if 'consecutive_recovery_wins' not in st.session_state: # Counter for consecutive *internal* wins in recovery
    st.session_state.consecutive_recovery_wins = 0
if 'last_internal_prediction_outcome' not in st.session_state: # Stores internal prediction for recovery logic
    st.session_state.last_internal_prediction_outcome = None
if 'rounds_in_recovery_no_bet' not in st.session_state: # NEW: Counter for rounds in recovery where no bet is forced
    st.session_state.rounds_in_recovery_no_bet = 0
if 'last_raw_module_predictions' not in st.session_state: # NEW: Store raw module predictions for logging
    st.session_state.last_raw_module_predictions = {}
if 'last_raw_tie_prediction' not in st.session_state: # NEW: Store raw tie prediction for logging
    st.session_state.last_raw_tie_prediction = None


if 'tie_prediction' not in st.session_state:
    st.session_state.tie_prediction = None
if 'tie_confidence' not in st.session_state: 
    st.session_state.tie_confidence = None

if 'is_tie_sniper_opportunity' not in st.session_state:
    st.session_state.is_tie_sniper_opportunity = False
if 'recommendation_text' not in st.session_state: 
    st.session_state.recommendation_text = "กำลังวิเคราะห์ข้อมูล..." # Default message
if 'derived_road_trends' not in st.session_state:
    st.session_state.derived_road_trends = {
        "BigEyeBoy": "ไม่มีแนวโน้ม",
        "SmallRoad": "ไม่มีแนวโน้ม",
        "CockroachPig": "ไม่มีแนวโน้ม"
    }


# --- UI Callback Functions ---
def handle_click(main_outcome_str: MainOutcome): 
    """
    Handles button clicks for P, B, T outcomes.
    Adds the result to OracleBrain and updates all predictions.
    """
    # Clear previous debug messages
    st.session_state.debug_messages = []

    # This is the actual result of the round that just finished
    current_round_actual_result = main_outcome_str

    # Store the internal prediction from the *previous* round for recovery check
    # This value was set at the END of the *previous* handle_click call.
    prev_round_internal_prediction = st.session_state.last_internal_prediction_outcome

    # Log debug info to session state
    st.session_state.debug_messages.append(f"--- Debugging handle_click for recovery ---")
    st.session_state.debug_messages.append(f"  Actual Result (Current Round): {current_round_actual_result}")
    st.session_state.debug_messages.append(f"  Recovery Mode (before update): {st.session_state.in_recovery_mode}")
    st.session_state.debug_messages.append(f"  Internal Prediction (for previous round, used for check): {prev_round_internal_prediction}")
    st.session_state.debug_messages.append(f"  Consecutive Recovery Wins (before update): {st.session_state.consecutive_recovery_wins}")
    st.session_state.debug_messages.append(f"  Rounds in recovery (no bet phase) before update: {st.session_state.rounds_in_recovery_no_bet}")


    if st.session_state.in_recovery_mode:
        # Increment rounds_in_recovery_no_bet if we are still in the initial no-bet phase
        if st.session_state.rounds_in_recovery_no_bet < 2: # Check against the constant if needed
            st.session_state.rounds_in_recovery_no_bet += 1
            st.session_state.debug_messages.append(f"  Rounds in recovery (no bet phase) incremented to: {st.session_state.rounds_in_recovery_no_bet}")

        # Check if the *internal* prediction for the *just finished* round was correct
        if prev_round_internal_prediction is not None and \
           prev_round_internal_prediction in ("P", "B") and \
           prev_round_internal_prediction == current_round_actual_result:
            st.session_state.consecutive_recovery_wins += 1
            st.session_state.debug_messages.append(f"  Internal prediction CORRECT. consecutive_recovery_wins incremented to: {st.session_state.consecutive_recovery_wins}")
        else:
            st.session_state.consecutive_recovery_wins = 0 # Reset if internal prediction missed or was None
            st.session_state.debug_messages.append(f"  Internal prediction INCORRECT or NONE. consecutive_recovery_wins reset to: {st.session_state.consecutive_recovery_wins}")
    
    # Add the result to OracleBrain, passing the *displayed* prediction of the *just finished* round.
    # Also pass the raw internal predictions for logging module accuracies.
    st.session_state.oracle.add_result(
        current_round_actual_result, 
        is_any_natural=False, 
        displayed_prediction_for_prev_round=st.session_state.prediction,
        internal_module_predictions=st.session_state.last_raw_module_predictions, # Pass raw predictions from previous round
        internal_tie_prediction=st.session_state.last_raw_tie_prediction # Pass raw tie prediction from previous round
    )
    
    # Now, call predict_next for the *new* round to get its predictions and recommendations.
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity, recommendation_text, derived_road_trends,
     raw_module_preds_for_next_round, raw_tie_pred_for_next_round) = st.session_state.oracle.predict_next() 
    
    # Update session state with the *new* round's prediction and recommendation details
    st.session_state.prediction = prediction # This is the *new* round's displayed prediction
    st.session_state.source = source
    st.session_state.confidence = confidence 
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 
    
    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    st.session_state.recommendation_text = recommendation_text 
    st.session_state.derived_road_trends = derived_road_trends
    
    pattern_names = { # Simplified pattern names for display
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร", "BBBB": "มังกร", 
        "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว",
        "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว",
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
        "PBB": "สองตัวตัด", "BPP": "สองตัวตัด",
        "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PBBPPP": "สองตัดสาม", # New pattern name
        "BPPBBB": "สองตัดสาม", # New pattern name
        "มังกรตัด": "มังกรตัด", 
        "ปิงปองตัด": "ปิงปองตัด", 
        "ตัดสาม": "ตัดสาม" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) >= 15: 
        st.session_state.initial_shown = True 

    # Store the *internal* prediction for the *new* round's recovery check (for the *next* handle_click)
    st.session_state.last_internal_prediction_outcome = st.session_state.oracle.last_internal_prediction 
    st.session_state.last_raw_module_predictions = raw_module_preds_for_next_round # Store for next round's logging
    st.session_state.last_raw_tie_prediction = raw_tie_pred_for_next_round # Store for next round's logging

    st.query_params["_t"] = f"{time.time()}"


def handle_remove():
    """
    Handles removing the last added result.
    """
    st.session_state.oracle.remove_last()
    # Also need to adjust recovery states if removing a round
    # This is complex to do perfectly in reverse, so for simplicity, reset them
    st.session_state.in_recovery_mode = False
    st.session_state.consecutive_recovery_wins = 0
    st.session_state.last_internal_prediction_outcome = None # Reset internal prediction state
    st.session_state.rounds_in_recovery_no_bet = 0 # NEW: Reset no-bet counter on remove
    st.session_state.debug_messages = [] # Clear debug messages on remove
    st.session_state.last_raw_module_predictions = {} # Reset raw predictions
    st.session_state.last_raw_tie_prediction = None # Reset raw tie prediction

    # Call predict_next for the updated history
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity, recommendation_text, derived_road_trends,
     raw_module_preds_for_next_round, raw_tie_pred_for_next_round) = st.session_state.oracle.predict_next() 
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 

    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    st.session_state.recommendation_text = recommendation_text
    st.session_state.derived_road_trends = derived_road_trends
    
    pattern_names = { # Simplified pattern names for display
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร", "BBBB": "มังกร", 
        "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว",
        "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว",
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
        "PBB": "สองตัวตัด", "BPP": "สองตัวตัด",
        "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PBBPPP": "สองตัดสาม", # New pattern name
        "BPPBBB": "สองตัดสาม", # New pattern name
        "มังกรตัด": "มังกรตัด", 
        "ปิงปองตัด": "ปิงปองตัด", 
        "ตัดสาม": "ตัดสาม" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) < 15: 
        st.session_state.initial_shown = False
    
    # Update internal prediction for the *new* round's recovery check
    st.session_state.last_internal_prediction_outcome = st.session_state.oracle.last_internal_prediction
    st.session_state.last_raw_module_predictions = raw_module_preds_for_next_round # Store for next round's logging
    st.session_state.last_raw_tie_prediction = raw_tie_pred_for_next_round # Store for next round's logging
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
    st.session_state.derived_road_trends = {
        "BigEyeBoy": "ไม่มีแนวโน้ม",
        "SmallRoad": "ไม่มีแนวโน้ม",
        "CockroachPig": "ไม่มีแนวโน้ม"
    }
    # Reset recovery mode states when starting a new shoe
    st.session_state.in_recovery_mode = False
    st.session_state.consecutive_recovery_wins = 0
    st.session_state.last_internal_prediction_outcome = None
    st.session_state.rounds_in_recovery_no_bet = 0 # NEW: Reset no-bet counter on new shoe
    st.session_state.debug_messages = [] # Clear debug messages on new shoe
    st.session_state.last_raw_module_predictions = {} # Reset raw predictions
    st.session_state.last_raw_tie_prediction = None # Reset raw tie prediction

    st.query_params["_t"] = f"{time.time()}"

# --- Header ---
st.markdown('<div class="header-container"><span class="main-title">🔮 Oracle</span><span class="version-text">V10.6.7</span></div>', unsafe_allow_html=True) # Updated version to V10.6.7

# --- Prediction Output Box (Main Outcome) ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำแนะนำการเดิมพัน:</b>", unsafe_allow_html=True) 

# Display recommendation text directly
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

# --- Miss Streak Warning ---
miss = st.session_state.oracle.calculate_miss_streak() # This now reflects displayed bets
st.markdown(f"<div class='miss-streak-container'><p class='miss-streak-text'>❌ แพ้ติดกัน: {miss} ครั้ง</p></div>", unsafe_allow_html=True) # Smaller text
if miss == 3:
    st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
elif miss >= 6:
    st.error("🚨 เกมแตก! (แพ้ 6 ไม้ติด)")

# --- Big Road Display ---
st.markdown("<b>🕒 Big Road:</b>", unsafe_allow_html=True)

history_results = st.session_state.oracle.history 

if history_results:
    # Adjusted max_row to 6 as requested (6 rows vertically)
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

    MAX_DISPLAY_COLUMNS = 14 # Changed to 14 columns as requested (แนวนอน 14 แถว)
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:] 

    big_road_html = f"<div class='big-road-container' id='big-road-container-unique'>"
    for col in columns:
        big_road_html += "<div class='big-road-column'>"
        # Ensure that cells are always created up to max_row for consistent column height
        for row_idx in range(max_row):
            if row_idx < len(col):
                cell_result, tie_count, natural_flag = col[row_idx]
                emoji = "🔵" if cell_result == "P" else "🔴"
                tie_html = f"<span class='tie-count'>{tie_count}</span>" if tie_count > 0 else ""
                natural_indicator = f"<span class='natural-indicator'>N</span>" if natural_flag else ""
                big_road_html += f"<div class='big-road-cell {cell_result}'>{emoji}{tie_html}{natural_indicator}</div>" 
            else:
                big_road_html += f"<div class='big-road-cell'></div>" # Empty cell for padding
        big_road_html += "</div>" 
    big_road_html += "</div>" 
    
    st.markdown(big_road_html, unsafe_allow_html=True)

else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons (Main Outcomes) - MOVED TO BELOW BIG ROAD ---
st.markdown("<b>ป้อนผล:</b>", unsafe_allow_html=True) 

col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_P")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_B")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_T")

# --- Control Button: Remove Last (MOVED TO BELOW INPUT BUTTONS) ---
st.button("↩️ ลบรายการล่าสุด", on_click=handle_remove, key="remove_last_btn") # Added key for consistency
# Set background color for remove_last_btn to green
st.markdown("""
<style>
#remove_last_btn button {
    background-color: #4CAF50; /* Green */
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)


# --- Derived Roads Display - NOW AS TEXTUAL TRENDS ---
st.markdown("<b>📊 เค้าไพ่รอง (Derived Roads):</b>", unsafe_allow_html=True)

# Display derived road trends
col_beb, col_sr, col_cp = st.columns(3)

with col_beb:
    st.markdown("<h5>Big Eye Boy</h5>", unsafe_allow_html=True)
    trend_value = st.session_state.derived_road_trends["BigEyeBoy"]
    trend_class = "no-trend" # Default to grey
    if trend_value == "ปิงปอง":
        trend_class = "ping-pong"
    elif trend_value == "มังกร":
        trend_class = "dragon"
    elif trend_value in ["สองตัวติด", "สองตัวตัด", "คู่สลับ"]:
        trend_class = "clear-trend"
    st.markdown(f"<div class='derived-trend-box {trend_class}'>{trend_value} ⬅️</div>", unsafe_allow_html=True)

with col_sr:
    st.markdown("<h5>Small Road</h5>", unsafe_allow_html=True)
    trend_value = st.session_state.derived_road_trends["SmallRoad"]
    trend_class = "no-trend" # Default to grey
    if trend_value == "ปิงปอง":
        trend_class = "ping-pong"
    elif trend_value == "มังกร":
        trend_class = "dragon"
    elif trend_value in ["สองตัวติด", "สองตัวตัด", "คู่สลับ"]:
        trend_class = "clear-trend"
    st.markdown(f"<div class='derived-trend-box {trend_class}'>{trend_value} ⬅️</div>", unsafe_allow_html=True)

with col_cp:
    st.markdown("<h5>Cockroach Pig</h5>", unsafe_allow_html=True)
    trend_value = st.session_state.derived_road_trends["CockroachPig"]
    trend_class = "no-trend" # Default to grey
    if trend_value == "ปิงปอง":
        trend_class = "ping-pong"
    elif trend_value == "มังกร":
        trend_class = "dragon"
    elif trend_value in ["สองตัวติด", "สองตัวตัด", "คู่สลับ"]:
        trend_class = "clear-trend"
    st.markdown(f"<div class='derived-trend-box {trend_class}'>{trend_value} ⬅️</div>", unsafe_allow_html=True)


# --- Control Button: Start New Shoe (MOVED TO BELOW DERIVED ROADS) ---
st.button("▶️ เริ่มขอนใหม่", on_click=handle_start_new_shoe, key="start_new_shoe_btn") # Added key for consistency
# Set background color for start_new_shoe_btn to green
st.markdown("""
<style>
#start_new_shoe_btn button {
    background-color: #4CAF50; /* Green */
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)


# --- Data Management ---
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
             is_tie_sniper_opportunity, recommendation_text, derived_road_trends,
             raw_module_preds_for_next_round, raw_tie_pred_for_next_round) = st.session_state.oracle.predict_next()

            st.session_state.prediction = prediction
            st.session_state.source = source
            st.session_state.confidence = confidence
            st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main
            st.session_state.tie_prediction = tie_pred
            st.session_state.tie_confidence = tie_conf
            st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
            st.session_state.recommendation_text = recommendation_text
            st.session_state.derived_road_trends = derived_road_trends
            
            pattern_names = { # Simplified pattern names for display
                "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
                "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
                "PPPP": "มังกร", "BBBB": "มังกร", 
                "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว",
                "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว",
                "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
                "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
                "PBB": "สองตัวตัด", "BPP": "สองตัวตัด",
                "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
                "PBBPPP": "สองตัดสาม", # New pattern name
                "BPPBBB": "สองตัดสาม", # New pattern name
                "มังกรตัด": "มังกรตัด",
                "ปิงปองตัด": "ปิงปองตัด",
                "ตัดสาม": "ตัดสาม"
            }
            st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)

            st.session_state.last_raw_module_predictions = raw_module_preds_for_next_round # Store for next round's logging
            st.session_state.last_raw_tie_prediction = raw_tie_pred_for_next_round # Store for next round's logging
            st.query_params["_t"] = f"{time.time()}" # Force UI refresh
            
        except json.JSONDecodeError:
            st.error("ไฟล์ที่อัปโหลดไม่ใช่ไฟล์ JSON ที่ถูกต้อง")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

# --- Debugging Toggle ---
st.session_state.show_debug_info = st.checkbox("⚙️ แสดงข้อมูล Debugging") # Updated emoji and text

# --- Conditional Debugging Output ---
if st.session_state.show_debug_info:
    st.markdown("<h3>⚙️ ข้อมูล Debugging (สำหรับนักพัฒนา)</h3>", unsafe_allow_html=True)
    # Display messages from handle_click
    for msg in st.session_state.debug_messages:
        st.write(msg)
    
    st.write("---") 
    st.write(f"ความยาวประวัติ P/B: {len(_get_main_outcome_history(st.session_state.oracle.history))}") 
    st.write(f"ผลทำนายหลัก (prediction - displayed): {st.session_state.prediction}") # This is the displayed prediction for the *current* round
    st.write(f"โมดูลที่ใช้ (source): {st.session_state.source}")
    st.write(f"ความมั่นใจ (confidence): {st.session_state.confidence}")
    st.write(f"แพ้ติดกัน (miss streak - displayed): {st.session_state.oracle.calculate_miss_streak()}") # Displayed miss streak
    st.write(f"อัตราความผันผวน (Choppiness Rate): {st.session_state.oracle._calculate_choppiness_rate(st.session_state.oracle.history, 20):.2f}") 
    st.write(f"Sniper หลัก: {st.session_state.is_sniper_opportunity_main}")
    st.write(f"ทำนายเสมอ: {st.session_state.tie_prediction}, ความมั่นใจเสมอ: {st.session_state.tie_confidence}, Sniper เสมอ: {st.session_state.is_tie_sniper_opportunity}") 
    st.write(f"โหมดฟื้นฟู (Recovery Mode): {st.session_state.in_recovery_mode}") 
    st.write(f"ชนะติดกันในโหมดฟื้นฟู (Consecutive Recovery Wins - internal): {st.session_state.consecutive_recovery_wins}") 
    st.write(f"ผลทำนายภายในล่าสุด (Last Internal Prediction - for NEXT round's check): {st.session_state.last_internal_prediction_outcome}") # Internal prediction for the *next* round
    st.write(f"จำนวนตางดเดิมพันในโหมดฟื้นฟู (Rounds in Recovery No Bet): {st.session_state.rounds_in_recovery_no_bet}") # NEW: Display new counter
    st.write("---") 

    st.markdown("<h4>⚙️ การทำนายจากเค้าไพ่รอง (Derived Road Predictions)</h4>", unsafe_allow_html=True)
    # Display the raw predictions that were used for logging
    st.write(f"  - Raw Module Predictions (for current round): {st.session_state.last_raw_module_predictions}")
    st.write(f"  - Raw Tie Prediction (for current round): {st.session_state.last_raw_tie_prediction}")
    st.write("---")

    st.markdown("<h4>⚙️ การทำนายจากสถิติ (Statistical Predictions)</h4>", unsafe_allow_html=True)
    # To show the statistical prediction, we need to call predict() again for debug purposes
    # Or, we can expose the internal state of StatisticalAnalyzer if needed for deeper debug
    stat_pred_debug = st.session_state.oracle.statistical_analyzer.predict(st.session_state.oracle.history)
    st.write(f"  - Statistical Prediction: {stat_pred_debug if stat_pred_debug else 'None'}")
    st.write(f"  - Statistical Analyzer Sequence Outcomes: {st.session_state.oracle.statistical_analyzer.sequence_outcomes}")
    st.write("---")


# --- Accuracy by Module ---
st.session_state.show_accuracy_info = st.checkbox("📈 แสดงความแม่นยำรายโมดูล") # Checkbox to toggle visibility

if st.session_state.show_accuracy_info: # Conditional rendering based on checkbox
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
