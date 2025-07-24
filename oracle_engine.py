import streamlit as st # Keep for cache decorator
import math
import random
from collections import Counter

class OracleEngine:
    __version__ = "1.11" # Engine version for compatibility check

    def __init__(self):
        self.history = []  # Stores P, B, T, S6 results as list of dicts: [{'main_outcome': 'P', 'ties': 0, 'is_any_natural': False}, ...]
        
        # Learning States (Dynamic)
        self.pattern_stats = {} # {('PatternName', 'PBPB_tuple'): {'total_hits': N, 'total_attempts': M}}
        self.momentum_stats = {} # {('MomentumName', 'BBBP_tuple'): {'total_hits': N, 'total_attempts': M}}
        self.sequence_memory_stats = {} # {('P', 'B', 'P'): {'predict_P': {'hits': N, 'attempts': M}, 'predict_B': {...}, ...}}
        self.tie_stats = {} # {'pattern_name': {'hits': N, 'attempts': M}}
        self.super6_stats = {} # {'pattern_name': {'hits': N, 'attempts': M}}

        # Static Weights (Can be fine-tuned)
        self.base_confidence_score = 75 # Starting point for confidence
        self.min_history_for_prediction = 20 # Minimum P/B hands required for prediction
        self.min_history_for_empirical_tie_super6 = 20 # Minimum P/B hands for empirical Tie/Super6 prob

        # These are used to calculate the Confidence Score
        self.pattern_weights = {
            'Dragon': 1.0, # Highest weight for strong trends
            'FollowStreak': 0.9,
            'Pingpong': 0.8,
            'Two-Cut': 0.7,
            'Triple-Cut': 0.7,
            'One-Two Pattern': 0.6,
            'Two-One Pattern': 0.6,
            'Broken Pattern': 0.2, # Lower weight for chaotic patterns
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9,
            'P3+ Momentum': 0.9,
            'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7,
            'Ladder Momentum (X-Y-XX-Y)': 0.6,
            'Choppy': -0.5, # Negative weight for choppy
        }
        self.sequence_weights = { # Weights for N-bit sequence matching
            3: 0.3,
            4: 0.4,
            5: 0.5,
            6: 0.6,
            7: 0.7,
            8: 0.8,
        }

        # Thresholds for making specific recommendations
        self.confidence_threshold_play = 60 # Min confidence to recommend 'Play'
        self.tie_recommendation_threshold = 50 # Min confidence for Tie prediction
        self.super6_recommendation_threshold = 60 # Min confidence for Super6 prediction

        # Theoretical probabilities for Tie/Super6 (when empirical data is low)
        self.theoretical_tie_prob = 0.0951 # ~9.51%
        self.theoretical_super6_prob = 0.0128 # ~1.28% (of total hands)
        self.theoretical_banker_prob = 0.4586
        self.theoretical_player_prob = 0.4462


    def reset_history(self):
        self.history = []
        self.reset_learning_states_on_undo() # Full reset includes learning states

    def reset_learning_states_on_undo(self): # Use for partial reset (e.g., undo, compatibility check)
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.tie_stats = {}
        self.super6_stats = {}

    def _get_pb_history(self, current_history):
        """Extracts only P and B outcomes from the history, ignoring T and S6 for pattern detection."""
        pb_history = []
        for item in current_history:
            if item and 'main_outcome' in item:
                if item['main_outcome'] == 'S6': # Treat S6 as B for PB pattern analysis
                    pb_history.append('B')
                elif item['main_outcome'] in ['P', 'B']:
                    pb_history.append(item['main_outcome'])
        return pb_history

    def _get_streaks(self, history_list):
        """
        Converts a list of results (P, B) into streaks.
        Returns a list of tuples: [(outcome, count)]
        Example: ['P', 'P', 'B', 'P', 'P', 'P'] -> [('P', 2), ('B', 1), ('P', 3)]
        """
        if not history_list:
            return []

        streaks = []
        current_streak_outcome = history_list[0]
        current_streak_count = 0

        for outcome in history_list:
            if outcome == current_streak_outcome:
                current_streak_count += 1
            else:
                streaks.append((current_streak_outcome, current_streak_count))
                current_streak_outcome = outcome
                current_streak_count = 1
        streaks.append((current_streak_outcome, current_streak_count)) # Add the last streak
        return streaks

    def _detect_sequences(self, history):
        """
        Detects common N-bit sequences (3-8 bits) and their next outcomes.
        Returns a list of (sequence_tuple, next_outcome)
        """
        pb_history = self._get_pb_history(history)
        detected_sequences = []
        
        # Sequence lengths to check
        sequence_lengths = range(3, 9) # Check 3-bit up to 8-bit sequences

        for length in sequence_lengths:
            if len(pb_history) >= length + 1:
                for i in range(len(pb_history) - length):
                    sequence = tuple(pb_history[i : i + length])
                    next_outcome = pb_history[i + length]
                    detected_sequences.append((sequence, next_outcome))
        return detected_sequences


    def detect_patterns(self, history, big_road_data):
        """
        Detects various patterns in the game history.
        history: Full history including T and S6.
        big_road_data: The 2D structure of the big road.
        """
        pb_history = self._get_pb_history(history)
        streaks = self._get_streaks(pb_history)
        patterns_detected = []

        # Ensure enough history for pattern detection
        if len(pb_history) < 4: # Most patterns need at least 4 P/B
            return patterns_detected

        # --- 1. Pingpong (Alternating P/B pattern) ---
        # Checks for P-B-P-B or B-P-B-P in various lengths from the end
        for length in [4, 6, 8, 10]: # Check for 4x, 6x, 8x, 10x alternating
            if len(pb_history) >= length:
                last_n = pb_history[-length:]
                is_pingpong = True
                for i in range(length - 1):
                    if last_n[i] == last_n[i+1]:
                        is_pingpong = False
                        break
                if is_pingpong:
                    patterns_detected.append((f'Pingpong ({length}x)', tuple(last_n)))
        
        # --- 2. Dragon (Long consecutive streak) ---
        # Already handled by Momentum Tracker for streaks 3+
        
        # --- 3. Two-Cut (BB-PP-BB-PP) ---
        if len(streaks) >= 4:
            last_streaks = streaks[-4:]
            if (last_streaks[0][1] == 2 and last_streaks[1][1] == 2 and
                last_streaks[2][1] == 2 and last_streaks[3][1] == 2 and
                last_streaks[0][0] != last_streaks[1][0] and
                last_streaks[1][0] != last_streaks[2][0] and # Check A != B, B != C (A=C)
                last_streaks[0][0] == last_streaks[2][0]):
                patterns_detected.append(('Two-Cut', tuple(pb_history[-sum(s[1] for s in last_streaks):])))

        # --- 4. Triple-Cut (BBB-PPP-BBB-PPP) ---
        if len(streaks) >= 4:
            last_streaks = streaks[-4:]
            if (last_streaks[0][1] == 3 and last_streaks[1][1] == 3 and
                last_streaks[2][1] == 3 and last_streaks[3][1] == 3 and
                last_streaks[0][0] != last_streaks[1][0] and
                last_streaks[1][0] != last_streaks[2][0] and # Check A != B, B != C (A=C)
                last_streaks[0][0] == last_streaks[2][0]):
                patterns_detected.append(('Triple-Cut', tuple(pb_history[-sum(s[1] for s in last_streaks):])))

        # --- 5. One-Two Pattern (B-PP-B-PP) ---
        if len(streaks) >= 4:
            last_streaks = streaks[-4:]
            # Example: (B,1), (P,2), (B,1), (P,2)
            if (last_streaks[0][1] == 1 and last_streaks[1][1] == 2 and
                last_streaks[2][1] == 1 and last_streaks[3][1] == 2 and
                last_streaks[0][0] == last_streaks[2][0] and # B1 == B3
                last_streaks[1][0] == last_streaks[3][0] and # P2 == P4
                last_streaks[0][0] != last_streaks[1][0]): # B1 != P2
                patterns_detected.append(('One-Two Pattern', tuple(pb_history[-sum(s[1] for s in last_streaks):])))
        
        # --- 6. Two-One Pattern (BB-P-BB-P) ---
        if len(streaks) >= 4:
            last_streaks = streaks[-4:]
            # Example: (B,2), (P,1), (B,2), (P,1)
            if (last_streaks[0][1] == 2 and last_streaks[1][1] == 1 and
                last_streaks[2][1] == 2 and last_streaks[3][1] == 1 and
                last_streaks[0][0] == last_streaks[2][0] and # B1 == B3
                last_streaks[1][0] == last_streaks[3][0] and # P2 == P4
                last_streaks[0][0] != last_streaks[1][0]): # B1 != P2
                patterns_detected.append(('Two-One Pattern', tuple(pb_history[-sum(s[1] for s in last_streaks):])))

        # --- 7. Broken Pattern (BPBPPBP) ---
        if len(pb_history) >= 7:
            last7 = "".join(pb_history[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7:
                patterns_detected.append(('Broken Pattern', tuple(pb_history[-7:])))

        # --- 8. FollowStreak (Simple consecutive streak, general) ---
        # If the last streak is long (already covered by Momentum 3+)
        if streaks:
            last_streak = streaks[-1]
            if last_streak[1] >= 3:
                # Add a general FollowStreak pattern
                patterns_detected.append(('FollowStreak', tuple(pb_history[-last_streak[1]:])))

        # --- 9. 2D Patterns (Big Eye Boy, Small Road, Cockroach Pig) ---
        # These patterns are harder to define purely from linear history.
        # They depend on the Big Road structure's "bead" positions relative to each other.
        # Simple implementations based on 2D Big Road data.

        # Ensure big_road_data is provided and has enough columns
        if big_road_data and len(big_road_data) >= 3:
            # Get data of the last three main columns for 2D pattern analysis
            # Ensure safe access to column data
            last_col = big_road_data[-1] if len(big_road_data) >= 1 else None
            prev_col = big_road_data[-2] if len(big_road_data) >= 2 else None
            prev_prev_col = big_road_data[-3] if len(big_road_data) >= 3 else None
            
            # Extract main outcomes for comparison (ignoring ties and other info in tuple)
            last_col_actual = [cell[0] for cell in last_col if cell is not None and cell[0] in ['P', 'B', 'S6']] if last_col else []
            prev_col_actual = [cell[0] for cell in prev_col if cell is not None and cell[0] in ['P', 'B', 'S6']] if prev_col else []
            prev_prev_col_actual = [cell[0] for cell in prev_prev_col if cell is not None and cell[0] in ['P', 'B', 'S6']] if prev_prev_col else []

            # Ensure all relevant columns exist and have at least one outcome
            if last_col_actual and prev_col_actual and prev_prev_col_actual:
                # Get the first outcome of each column (P or B, treating S6 as B)
                last_col_first_outcome = 'B' if last_col_actual[0] == 'S6' else last_col_actual[0]
                prev_col_first_outcome = 'B' if prev_col_actual[0] == 'S6' else prev_col_actual[0]
                prev_prev_col_first_outcome = 'B' if prev_prev_col_actual[0] == 'S6' else prev_prev_col_actual[0]

                # Get the length of each column
                last_col_len = len(last_col_actual)
                prev_col_len = len(prev_col_actual)
                prev_prev_col_len = len(prev_prev_col_actual)

                # Big Eye Boy (2D Simple - Follow vs Break) - Example: P P B (last 3 columns have 2nd bead matching first, or cutting)
                # This is a simplification. True Big Eye Boy depends on specific entry points.
                # A very basic interpretation: Is the current column following the pattern of the prev_prev_col vs prev_col?
                if len(big_road_data) >= 3:
                    # Check if prev_col is chopped vs prev_prev_col (i.e. if prev_col_len == prev_prev_col_len, it's following)
                    if prev_col_len == prev_prev_col_len:
                        # If prev_col and prev_prev_col have same length (or prev_col breaks prev_prev_col)
                        # Check if last_col is following this behavior
                        if last_col_len == prev_col_len: # Example: P P B (2,2,2) -> follows
                            patterns_detected.append(('Big Eye Boy (2D Simple - Follow)', tuple(last_col_actual)))
                        elif last_col_len < prev_col_len: # Example: P P B (2,2,1) -> breaks
                            patterns_detected.append(('Big Eye Boy (2D Simple - Break)', tuple(last_col_actual)))
                
                # Small Road (2D Simple - Chop) - Example: P B P (columns of length 1)
                if len(big_road_data) >= 3:
                     # Check if prev_col and prev_prev_prev_col have data
                    if len(big_road_data) >= 4:
                        prev_prev_prev_col = big_road_data[-4]
                        prev_prev_prev_col_actual = [cell[0] for cell in prev_prev_prev_col if cell is not None and cell[0] in ['P', 'B', 'S6']] if prev_prev_prev_col else []
                        if prev_prev_prev_col_actual:
                            prev_prev_prev_col_first_outcome_val = 'B' if prev_prev_prev_col_actual[0] == 'S6' else prev_prev_prev_col_actual[0] # Corrected line

                            if (last_col_len == prev_col_len and prev_col_len == prev_prev_col_len and prev_prev_col_len == prev_prev_prev_col_len and
                                last_col_len == 1 and prev_col_len == 1 and prev_prev_col_len == 1 and prev_prev_prev_col_len == 1 and
                                last_col_first_outcome != prev_col_first_outcome and
                                prev_col_first_outcome != prev_prev_col_first_outcome and
                                prev_prev_col_first_outcome != prev_prev_prev_col_first_outcome_val): # All single and alternating
                                patterns_detected.append(('Small Road (2D Simple - All Single Alternating)', tuple(last_col_actual)))
                
                # Cockroach Pig (2D Simple - Chop) - Example: P B B P (columns of length 1)
                # Similar to Small Road, but usually 3rd and 4th column from the left
                # This is a simplification.
                if len(big_road_data) >= 4:
                    # Very basic check: are the last 4 columns short and alternating?
                    last4_cols = big_road_data[-4:]
                    if all(len([c for c in col if c is not None and c[0] in ['P','B','S6']]) == 1 for col in last4_cols):
                        outcomes = [('B' if c[0]=='S6' else c[0]) for col in last4_cols for c in col if c is not None and c[0] in ['P','B','S6']]
                        if len(outcomes) == 4 and outcomes[0] != outcomes[1] and outcomes[1] != outcomes[2] and outcomes[2] != outcomes[3]:
                             patterns_detected.append(('Cockroach Pig (2D Simple - All Single Alternating)', tuple(last_col_actual)))


        return patterns_detected

    def detect_momentum(self, history, big_road_data):
        """Detects momentum patterns like B3+, P3+, Steady Repeat, Ladder Momentum."""
        pb_history = self._get_pb_history(history)
        streaks = self._get_streaks(pb_history)
        momentum_detected = []

        if not pb_history:
            return momentum_detected

        # --- 1. Basic Momentum (3+ consecutive) ---
        if streaks:
            last_streak = streaks[-1]
            if last_streak[1] >= 3:
                momentum_detected.append((f"{last_streak[0]}{last_streak[1]}+ Momentum", tuple(pb_history[-last_streak[1]:])))

        # --- 2. Steady Repeat (Pingpong-like, but long and consistent) ---
        # Checks for P-B-P-B-P-B-P or B-P-B-P-B-P-B
        for length in [7, 9, 11]: # Check for 7x, 9x, 11x alternating
            if len(pb_history) >= length:
                last_n = pb_history[-length:]
                is_steady_repeat = True
                for i in range(length - 1):
                    if last_n[i] == last_n[i+1]: # Not alternating
                        is_steady_repeat = False
                        break
                if is_steady_repeat:
                    momentum_detected.append((f'Steady Repeat Momentum ({length}x)', tuple(last_n)))

        # --- 3. Ladder Momentum (1-2-3 or X-Y-XX-Y) ---
        if len(streaks) >= 3:
            # 1-2-3 Ladder: (A,1), (B,1), (A,2), (B,1), (A,3)
            # This is complex and might lead to false positives without careful definition.
            # Simplified for now: looking for increasing streak lengths after a chop.
            if len(streaks) >= 5: # e.g. A1, B1, A2, B1, A3
                s = streaks
                if (s[-5][1] == 1 and s[-4][1] == 1 and s[-3][1] == 2 and s[-2][1] == 1 and s[-1][1] == 3 and
                    s[-5][0] == s[-3][0] == s[-1][0] and # A,A,A
                    s[-4][0] == s[-2][0] and # B,B
                    s[-5][0] != s[-4][0]): # A!=B
                    momentum_detected.append(('Ladder Momentum (1-1-2-1-3)', tuple(pb_history[-sum(s[1] for s in s[-5:]):])))

        return momentum_detected
    
    def detect_tie_super6_patterns(self, history):
        """
        Detects specific patterns that might indicate Tie or Super6 opportunity.
        These are weaker signals but can contribute to confidence.
        """
        tie_super6_patterns = []

        # Tie Patterns
        # Tie after alternating P/B (e.g., P-B-P-Tie)
        pb_history_for_pattern = self._get_pb_history(history[:-1]) # History without current actual result
        if history and history[-1]['main_outcome'] == 'T': # Only if last hand was Tie
            if len(pb_history_for_pattern) >= 3 and pb_history_for_pattern[-1] != pb_history_for_pattern[-2] and pb_history_for_pattern[-2] != pb_history_for_pattern[-3]:
                tie_super6_patterns.append(('Tie After Alternating PB', tuple(pb_history_for_pattern[-3:] + ['T']))) # Include T for context

        # Super6 Patterns (very rare, usually no strong patterns from just PB history)
        # S6 after a short Banker streak (e.g. B-B-S6)
        if history and history[-1]['main_outcome'] == 'S6': # Only if last hand was S6
            pb_history_for_pattern = self._get_pb_history(history[:-1]) # History without current actual result
            streaks_for_pattern = self._get_streaks(pb_history_for_pattern)
            if streaks_for_pattern:
                last_streak = streaks_for_pattern[-1]
                if last_streak[0] == 'B' and last_streak[1] in [1, 2]: # S6 after 1 or 2 Bankers
                    tie_super6_patterns.append((f'S6 After B Streak ({last_streak[1]}x)', tuple(pb_history_for_pattern[-last_streak[1]:] + ['S6'])))
        
        return tie_super6_patterns

    def _update_stats(self, stats_dict, name, sequence_snapshot, is_hit):
        key = (name, sequence_snapshot)
        if key not in stats_dict:
            stats_dict[key] = {'total_hits': 0, 'total_attempts': 0}
        
        stats_dict[key]['total_attempts'] += 1
        if is_hit:
            stats_dict[key]['total_hits'] += 1

    def _update_sequence_memory_stats(self, sequences_detected, predicted_outcome, actual_outcome):
        """
        Updates sequence_memory_stats based on the predicted outcome and actual outcome.
        This is for N-bit sequence matching where the sequence itself is the predictor.
        """
        for seq_tuple, next_expected_outcome in sequences_detected:
            if seq_tuple not in self.sequence_memory_stats:
                self.sequence_memory_stats[seq_tuple] = {}
            
            # Initialize sub-dict for the predicted outcome type if not exists
            if next_expected_outcome not in self.sequence_memory_stats[seq_tuple]:
                self.sequence_memory_stats[seq_tuple][next_expected_outcome] = {'hits': 0, 'attempts': 0}
            
            self.sequence_memory_stats[seq_tuple][next_expected_outcome]['attempts'] += 1
            if actual_outcome == next_expected_outcome:
                self.sequence_memory_stats[seq_tuple][next_expected_outcome]['hits'] += 1

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        """
        Updates the learning states (pattern_stats, momentum_stats, failed_pattern_instances)
        based on the AI's prediction and the actual outcome.
        """
        is_hit = (predicted_outcome == actual_outcome)
        
        # Adjust is_hit for S6 scenarios: if Banker was predicted and S6 came out, it's a hit.
        if predicted_outcome == 'B' and actual_outcome == 'S6':
            is_hit = True
        # Adjust is_hit for Tie scenarios: if P/B/S6 was predicted and T came out, it's a hit (neutral/push)
        # Note: For Tie, if P/B/S6 was predicted and Tie came out, it's a neutral outcome.
        # We treat it as a "hit" for pattern learning to not penalize P/B/S6 patterns on Ties.
        if predicted_outcome in ['P', 'B', 'S6'] and actual_outcome == 'T':
            is_hit = True
        
        # Update Pattern Stats
        for name, snapshot in patterns_detected:
            self._update_stats(self.pattern_stats, name, snapshot, is_hit)

        # Update Momentum Stats
        for name, snapshot in momentum_detected:
            self._update_stats(self.momentum_stats, name, snapshot, is_hit)
        
        # Update Sequence Memory Stats
        self._update_sequence_memory_stats(sequences_detected, predicted_outcome, actual_outcome)

        # Update Tie/Super6 Specific Stats (not directly linked to a specific prediction, but for overall tracking)
        # This part needs to be carefully handled to avoid over-updating.
        # For simplicity, Tie/Super6 patterns are part of patterns_detected.

    def _is_pattern_instance_failed(self, name, sequence_snapshot):
        """Checks if a specific pattern instance previously led to a miss."""
        # For now, this is implied by success rates.
        # If we had a specific 'failed_pattern_instances' dict, it would be checked here.
        # Current logic relies on low success rates in pattern_stats.
        return False # Placeholder if specific instance tracking is not needed.


    def get_current_learning_states(self):
        """Returns the current state of learning stats for caching/debugging."""
        return {
            "pattern_stats": self.pattern_stats,
            "momentum_stats": self.momentum_stats,
            "sequence_memory_stats": self.sequence_memory_stats,
            "tie_stats": self.tie_stats,
            "super6_stats": self.super6_stats
        }

    def confidence_score(self, history, big_road_data):
        """
        Calculates the confidence score (0-100%) for the current prediction.
        Based on pattern frequency, momentum stability, and sequence memory.
        """
        pb_history = self._get_pb_history(history)
        patterns = self.detect_patterns(history, big_road_data) # Pass full history for S6/Tie context
        momentum = self.detect_momentum(history, big_road_data)
        sequences_for_conf = self._detect_sequences(history) # Get all relevant sequences

        score = self.base_confidence_score # Start with base score

        # Score based on detected patterns
        for p_name, p_snapshot in patterns:
            key = (p_name, p_snapshot)
            if key in self.pattern_stats:
                stats = self.pattern_stats[key]
                if stats['total_attempts'] > 0:
                    success_rate = stats['total_hits'] / stats['total_attempts']
                    weight = self.pattern_weights.get(p_name, 0.5) # Default weight if not found
                    score += success_rate * weight * 10 # Scale up influence

        # Score based on detected momentum
        for m_name, m_snapshot in momentum:
            key = (m_name, m_snapshot)
            if key in self.momentum_stats:
                stats = self.momentum_stats[key]
                if stats['total_attempts'] > 0:
                    success_rate = stats['total_hits'] / stats['total_attempts']
                    weight = self.momentum_weights.get(m_name, 0.5)
                    score += success_rate * weight * 8 # Scale up influence

        # Score based on sequence memory
        # This part would need to be enhanced to check the *predicted* sequence's success rate
        # For now, we just add a small score if any sequence is found.
        if sequences_for_conf:
            score += len(sequences_for_conf) * 2 # Small positive score for finding sequences

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score

    def get_tie_opportunity_analysis(self, current_history):
        """
        Analyzes the opportunity for Tie or Super6 based on frequencies and specific patterns.
        Returns {'prediction': 'T'/'S6'/'?', 'confidence': %, 'reason': 'text'}
        """
        # Ensure current_history is not empty before proceeding
        if not current_history:
            return {'prediction': '?', 'confidence': 0, 'reason': 'ประวัติว่างเปล่า'}

        pb_history = self._get_pb_history(current_history) # P/B history only
        num_pb_hands = len(pb_history)
        total_hands = len(current_history)

        tie_count_empirical = sum(1 for h in current_history if h['main_outcome'] == 'T')
        super6_count_empirical = sum(1 for h in current_history if h['main_outcome'] == 'S6')

        # --- Calculate Blended Frequencies (Theoretical vs Empirical) ---
        # Weight for empirical data increases with more hands
        empirical_weight = min(1.0, total_hands / self.min_history_for_empirical_tie_super6)
        theoretical_weight = 1.0 - empirical_weight

        # Blended Tie Frequency
        blended_tie_freq = (self.theoretical_tie_prob * theoretical_weight + 
                            (tie_count_empirical / total_hands if total_hands > 0 else 0) * empirical_weight)
        
        # Blended Super6 Frequency
        blended_super6_freq = (self.theoretical_super6_prob * theoretical_weight +
                               (super6_count_empirical / total_hands if total_hands > 0 else 0) * empirical_weight)
        
        # Convert blended frequencies to Confidence Scores (scaled from 0-100)
        # Max expected frequency is slightly higher than theoretical max (e.g., if a specific shoe has very high occurrence)
        # Scale to make higher frequencies give higher confidence
        max_tie_freq_for_scaling = 0.15 # Max freq to map to 100% confidence for Tie (15%)
        max_super6_freq_for_scaling = 0.05 # Max freq to map to 100% confidence for S6 (5%)

        tie_confidence = min(100, int((blended_tie_freq / max_tie_freq_for_scaling) * 100))
        super6_confidence = min(100, int((blended_super6_freq / max_super6_freq_for_scaling) * 100))

        # Update internal tracking stats (for developer view)
        self.tie_stats['Blended_Frequency'] = blended_tie_freq
        self.tie_stats['Confidence'] = tie_confidence
        self.tie_stats['Empirical_Count'] = tie_count_empirical
        self.super6_stats['Blended_Frequency'] = blended_super6_freq
        self.super6_stats['Confidence'] = super6_confidence
        self.super6_stats['Empirical_Count'] = super6_count_empirical

        # --- Decision Logic for Tie/Super6 Prediction ---
        predicted_outcome = '?'
        reason = "ยังไม่พบแนวโน้ม Tie/Super6 ที่ชัดเจน (อิงตามความถี่ในขอนปัจจุบัน)"
        highest_confidence = 0
        
        # Collect potential outcomes that pass individual thresholds
        potential_outcomes = []
        if tie_confidence >= self.tie_recommendation_threshold:
            potential_outcomes.append(('T', tie_confidence, f"ความถี่ Tie ในขอนนี้สูงผิดปกติ ({blended_tie_freq:.2%})"))
        if super6_confidence >= self.super6_recommendation_threshold:
            potential_outcomes.append(('S6', super6_confidence, f"ความถี่ Super6 ในขอนนี้สูงผิดปกติ ({blended_super6_freq:.2%})"))
        
        potential_outcomes.sort(key=lambda x: x[1], reverse=True) # Sort by confidence

        if potential_outcomes:
            # Check if the top prediction is significantly better than others
            if len(potential_outcomes) > 1:
                top_pred = potential_outcomes[0]
                second_pred = potential_outcomes[1]
                
                # If the top confidence is significantly higher (e.g., 10% difference)
                if top_pred[1] - second_pred[1] >= 10: 
                    predicted_outcome = top_pred[0]
                    highest_confidence = top_pred[1]
                    reason = top_pred[2]
                else: # Confidences are too close, no clear winner
                    predicted_outcome = '?' 
                    highest_confidence = top_pred[1] # Show highest available confidence
                    reason = "Confidence ของ Tie/Super6 ใกล้เคียงกันเกินไป หรือไม่โดดเด่นพอ"
            else: # Only one outcome passed the threshold, predict it
                predicted_outcome = potential_outcomes[0][0]
                highest_confidence = potential_outcomes[0][1]
                reason = potential_outcomes[0][2]
        else: # No outcome passed any threshold
            # If nothing is strong, but history is long enough, show current average confidence
            if total_hands >= self.min_history_for_empirical_tie_super6:
                # If empirical data is available but low confidence, calculate average potential confidence
                avg_tie_conf_potential = int((self.theoretical_tie_prob / max_tie_freq_for_scaling) * 100)
                avg_s6_conf_potential = int((self.theoretical_super6_prob / max_super6_freq_for_scaling) * 100)
                # Show max of current tie/s6 confidence, or average theoretical if empirical is 0
                highest_confidence = max(tie_confidence, super6_confidence, avg_tie_conf_potential, avg_s6_conf_potential)
                reason = "ยังไม่พบแนวโน้ม Tie/Super6 ที่ชัดเจน (อิงตามความถี่ในขอนปัจจุบัน)"
            else: # History too short for empirical data, fallback to theoretical average
                highest_confidence = int((self.theoretical_tie_prob / max_tie_freq_for_scaling) * 100) # Default to theoretical Tie confidence
                reason = "ประวัติ Tie/Super6 ไม่เพียงพอ (ใช้ค่าเฉลี่ยทางทฤษฎี)"


        return {'prediction': predicted_outcome, 'confidence': highest_confidence, 'reason': reason}


    def predict_next(self, current_live_drawdown=0):
        """
        Main function to analyze and predict the next outcome.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view_lines = []

        # Get relevant history
        pb_history = self._get_pb_history(self.history)
        
        # Build Big Road Data for pattern detection
        # Ensure _build_big_road_data is directly accessible (it's a global function)
        big_road_data = _build_big_road_data(self.history) # Pass full history to build

        # Calculate current confidence score
        conf_score = self.confidence_score(self.history, big_road_data) # Pass full history for Tie/S6 context
        
        # --- Drawdown Protection (Highest Priority) ---
        DRAWDOWN_LIMIT_FOR_AVOID = 4 # If live_drawdown hits 4 or more, force Avoid
        if current_live_drawdown >= DRAWDOWN_LIMIT_FOR_AVOID:
            prediction_result = '?' # No specific prediction
            risk_level = f"High Drawdown ({current_live_drawdown} misses)"
            recommendation = "Avoid ❌ (ป้องกันแพ้ติดกัน)"
            developer_view_lines.append(f"Decision: Forced Avoid due to {current_live_drawdown} consecutive misses (Limit: {DRAWDOWN_LIMIT_FOR_AVOID}).")
            
            # Populate developer view with current state for debugging why drawdown happened
            developer_view_lines.append(f"Confidence (Layer 1): {conf_score}%")
            developer_view_lines.append(f"Detected Patterns: {[p[0] for p in self.detect_patterns(self.history, big_road_data)]}") 
            developer_view_lines.append(f"Detected Momentum: {[m[0] for m in self.detect_momentum(self.history, big_road_data)]}") 
            developer_view_lines.append(f"Detected Sequences: {[f'{s[0]}->{n}' for s,n in self._detect_sequences(self.history)]}") 
            
            return {
                "developer_view": "\n".join(developer_view_lines),
                "prediction": prediction_result,
                "accuracy": _cached_backtest_accuracy(self.history, self.pattern_stats, self.momentum_stats, self.failed_pattern_instances, self.sequence_memory_stats, self.tie_stats, self.super6_stats)['accuracy_percent'],
                "risk": risk_level,
                "recommendation": recommendation,
                "confidence": conf_score # Still show confidence of current state
            }

        # --- Insufficient History Check ---
        if len(pb_history) < self.min_history_for_prediction:
            developer_view_lines.append("Decision: Insufficient history for primary prediction.")
            return {
                "developer_view": "\n".join(developer_view_lines),
                "prediction": '?',
                "accuracy": 0, # Cannot calculate meaningful accuracy
                "risk": "Insufficient Data",
                "recommendation": "Avoid ❌",
                "confidence": 0 # No confidence yet
            }

        # --- Primary Prediction Logic (Player/Banker) ---
        # Prioritize strong patterns and momentum
        patterns = self.detect_patterns(self.history, big_road_data)
        momentum = self.detect_momentum(self.history, big_road_data)
        sequences = self._detect_sequences(self.history)
        
        # Collect potential predictions with their confidence contributions
        potential_predictions = [] # [(outcome, confidence_contribution, reason)]

        # 1. From Patterns
        if patterns:
            for p_name, p_snapshot in patterns:
                key = (p_name, p_snapshot)
                if key in self.pattern_stats:
                    stats = self.pattern_stats[key]
                    if stats['total_attempts'] > 0:
                        success_rate = stats['total_hits'] / stats['total_attempts']
                        weight = self.pattern_weights.get(p_name, 0.5) # Default weight if not found
                        # Predict next based on pattern (e.g. Pingpong -> opposite, Dragon -> same)
                        predicted_by_pattern = '?'
                        if 'Pingpong' in p_name and pb_history:
                            predicted_by_pattern = 'P' if pb_history[-1] == 'B' else 'B'
                        elif 'Dragon' in p_name or 'FollowStreak' in p_name and pb_history:
                            predicted_by_pattern = pb_history[-1]
                        elif 'Two-Cut' in p_name and len(pb_history) >= 2: # BB PP -> B
                            predicted_by_pattern = 'P' if pb_history[-1] == 'B' else 'B'
                        elif 'Triple-Cut' in p_name and len(pb_history) >= 3: # BBB PPP -> B
                            predicted_by_pattern = 'P' if pb_history[-1] == 'B' else 'B'
                        elif 'One-Two Pattern' in p_name and len(pb_history) >= 2: # B PP -> B
                            predicted_by_pattern = 'P' if pb_history[-1] == 'B' else 'B'
                        elif 'Two-One Pattern' in p_name and len(pb_history) >= 2: # BB P -> B
                            predicted_by_pattern = 'P' if pb_history[-1] == 'B' else 'B'
                        
                        if predicted_by_pattern != '?':
                            potential_predictions.append((predicted_by_pattern, success_rate * weight * 10, f"Pattern: {p_name} ({int(success_rate*100)}%)"))
        
        # 2. From Momentum
        if momentum:
            for m_name, m_snapshot in momentum:
                key = (m_name, m_snapshot)
                if key in self.momentum_stats:
                    stats = self.momentum_weights.get(m_name, 0.5)
                    if stats['total_attempts'] > 0:
                        success_rate = stats['total_hits'] / stats['total_attempts']
                        weight = self.momentum_weights.get(m_name, 0.5)
                        # Predict next based on momentum (usually follow streak)
                        predicted_by_momentum = '?'
                        if 'Momentum' in m_name and pb_history:
                            predicted_by_momentum = pb_history[-1]
                        elif 'Steady Repeat Momentum' in m_name and len(pb_history) >= 2: # PBPBPB -> P
                            predicted_by_momentum = 'P' if pb_history[-1] == 'B' else 'B'
                        
                        if predicted_by_momentum != '?':
                            potential_predictions.append((predicted_by_momentum, success_rate * weight * 8, f"Momentum: {m_name} ({int(success_rate*100)}%)"))

        # 3. From Sequence Memory (N-bit)
        if sequences and pb_history:
            # Example for how to get predictions from sequence memory:
            for seq_len, seq_weight in self.sequence_weights.items():
                if len(pb_history) >= seq_len:
                    current_seq_tuple = tuple(pb_history[-seq_len:])
                    if current_seq_tuple in self.sequence_memory_stats:
                        best_seq_pred_outcome = '?'
                        best_seq_confidence_contribution = -1
                        for pred_outcome, stats in self.sequence_memory_stats[current_seq_tuple].items():
                            if stats['attempts'] > 0:
                                # Scale confidence contribution based on success rate and sequence weight
                                current_conf_contrib = (stats['hits'] / stats['attempts']) * seq_weight * 10 
                                if current_conf_contrib > best_seq_confidence_contribution:
                                    best_seq_confidence_contribution = current_conf_contrib
                                    best_seq_pred_outcome = pred_outcome
                        
                        if best_seq_pred_outcome != '?':
                            potential_predictions.append((best_seq_pred_outcome, best_seq_confidence_contribution, f"Seq ({seq_len}): {current_seq_tuple} -> {best_seq_pred_outcome}"))


        # Consolidate predictions
        final_prediction_score = {'P': 0, 'B': 0}
        for pred, conf_contrib, _ in potential_predictions:
            if pred in final_prediction_score:
                final_prediction_score[pred] += conf_contrib
        
        # Select the best prediction
        if final_prediction_score['P'] > final_prediction_score['B']:
            prediction_result = 'P'
        elif final_prediction_score['B'] > final_prediction_score['P']:
            prediction_result = 'B'
        else: # Tie in score or no strong prediction based on patterns/momentum/sequences
            prediction_result = '?' # Fallback to intuition or default

        # Fallback to Intuition Logic if no strong pattern-based prediction
        if prediction_result == '?':
            intuitive_guess = self.intuition_predict(self.history)
            if intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view_lines.append(f"Decision: Using Intuition Logic, predicted {intuitive_guess}.")
            else:
                developer_view_lines.append("Decision: No strong pattern or intuition prediction.")
                risk_level = "Uncertainty"
                recommendation = "Avoid ❌" # Final avoid if nothing is clear

        # --- Final Confidence Check for Play/Avoid ---
        if conf_score < self.confidence_threshold_play:
            recommendation = "Avoid ❌"
            risk_level = "Low Confidence"
            developer_view_lines.append(f"Decision: Confidence ({conf_score}%) is below Play threshold ({self.confidence_threshold_play}%).")
        
        # --- Populate Developer View ---
        developer_view_lines.append(f"Confidence (Layer 1): {conf_score}%")
        developer_view_lines.append(f"Raw Patterns Detected: {[p[0] for p in patterns]}") # Use 'patterns' directly
        developer_view_lines.append(f"Raw Momentum Detected: {[m[0] for m in momentum]}") # Use 'momentum' directly
        developer_view_lines.append(f"Raw Sequences Detected: {[f'{s[0]}->{n}' for s,n in sequences]}") # Display sequence + next outcome
        developer_view_lines.append(f"Prediction Contributions: {potential_predictions}")
        developer_view_lines.append(f"Final Prediction Score: {final_prediction_score}")
        
        # Add Tie/Super6 Analysis summary to Developer View
        tie_super6_analysis_summary = self.get_tie_opportunity_analysis(self.history)
        developer_view_lines.append(f"Tie/Super6 Opportunity: {tie_super6_analysis_summary['prediction']} (Conf: {tie_super6_analysis_summary['confidence']}%) - {tie_super6_analysis_summary['reason']}")


        return {
            "developer_view": "\n".join(developer_view_lines),
            "prediction": prediction_result,
            "accuracy": _cached_backtest_accuracy(self.history, self.pattern_stats, self.momentum_stats, self.failed_pattern_instances, self.sequence_memory_stats, self.tie_stats, self.super6_stats)['accuracy_percent'],
            "risk": risk_level,
            "recommendation": recommendation,
            "confidence": conf_score
        }

    def intuition_predict(self, history):
        """
        Uses deep logic for prediction when no clear patterns are found.
        Focuses on subtle patterns in alternating or chopping sequences.
        """
        pb_history = self._get_pb_history(history)
        if len(pb_history) < 3:
            return '?'

        last3 = tuple(pb_history[-3:])
        last4 = tuple(pb_history[-4:]) if len(pb_history) >= 4 else None
        
        # Specific patterns from common Baccarat intuition
        if last3 == ('P','B','P'): return 'B' # PBP -> Predict B (common continuation)
        if last3 == ('B','P','B'): return 'P' # BPB -> Predict P (common continuation)
        if last3 == ('B','B','P'): return 'P' # BB P -> Predict P (chop)
        if last3 == ('P','P','B'): return 'B' # PP B -> Predict B (chop)

        if last4 == ('B','P','B','B'): return 'P' # B P B B -> Predict P (chop after double)
        if last4 == ('P','B','P','P'): return 'B' # P B P P -> Predict B (chop after double)

        if len(pb_history) >= 5 and tuple(pb_history[-5:]) == ('B','P','B','P','P'): return 'B' # B P B P P -> Predict B (chop after double)
        if len(pb_history) >= 5 and tuple(pb_history[-5:]) == ('P','B','P','B','B'): return 'P' # P B P B B -> Predict P (chop after double)


        return '?'


@st.cache_data(ttl=None)
def _cached_backtest_accuracy(history, pattern_stats, momentum_stats, failed_pattern_instances, sequence_memory_stats, tie_stats, super6_stats):
    """
    Calculates accuracy and drawdown by simulating predictions over historical data.
    Uses cached learning states to ensure consistency.
    """
    if len(history) < 20: # Need at least 20 hands for meaningful backtest
        return {"accuracy_percent": 0, "hits": 0, "total_bets": 0, "max_drawdown": 0}

    sim_engine = OracleEngine()
    sim_engine.pattern_stats = pattern_stats.copy()
    sim_engine.momentum_stats = momentum_stats.copy()
    sim_engine.sequence_memory_stats = sequence_memory_stats.copy()
    sim_engine.tie_stats = tie_stats.copy()
    sim_engine.super6_stats = super6_stats.copy()

    hits = 0
    total_bets_counted = 0
    current_drawdown_tracker = 0
    max_drawdown = 0

    # Start backtest from when prediction would begin (20th P/B hand)
    pb_history_only = sim_engine._get_pb_history(history)
    start_index_for_backtest = 0
    temp_pb_count = 0
    for i, item in enumerate(history):
        if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B', 'S6']: # Count P/B/S6 for minimum history
            temp_pb_count += 1
        if temp_pb_count >= sim_engine.min_history_for_prediction:
            start_index_for_backtest = i + 1 # Start predicting from the hand AFTER the 20th PB hand
            break
    
    if start_index_for_backtest >= len(history): # Not enough history for even one backtest prediction
        return {"accuracy_percent": 0, "hits": 0, "total_bets": 0, "max_drawdown": 0}


    # Simulate predictions
    for i in range(start_index_for_backtest, len(history)):
        simulated_history_up_to_this_point = history[:i]
        actual_outcome_of_current_hand = history[i]['main_outcome']

        # Get prediction from the simulated engine (which has learned from past data)
        # Pass a dummy drawdown of 0, as backtest calculates its own drawdown
        simulated_prediction_output = sim_engine.predict_next(current_live_drawdown=0) 
        
        simulated_predicted_outcome = simulated_prediction_output['prediction']
        simulated_recommendation = simulated_prediction_output['recommendation']

        # Check if the simulated AI actually recommended 'Play' for this hand
        if simulated_recommendation == "Play ✅" and simulated_predicted_outcome != '?':
            total_bets_counted += 1 # Only count bets that AI recommended to play
            
            is_hit_in_simulation = False
            # Check for HIT conditions
            if simulated_predicted_outcome == actual_outcome_of_current_hand:
                is_hit_in_simulation = True
            elif simulated_predicted_outcome == 'B' and actual_outcome_of_current_hand == 'S6':
                is_hit_in_simulation = True # Banker prediction is a hit if S6 comes
            elif simulated_predicted_outcome in ['P', 'B', 'S6'] and actual_outcome_of_current_hand == 'T':
                is_hit_in_simulation = True # P/B/S6 prediction is a hit if T comes (neutral break)
            elif simulated_predicted_outcome == 'T' and actual_outcome_of_current_hand == 'T':
                is_hit_in_simulation = True
            elif simulated_predicted_outcome == 'S6' and actual_outcome_of_current_hand == 'S6':
                is_hit_in_simulation = True
            
            if is_hit_in_simulation:
                hits += 1
                current_drawdown_tracker = 0 # Reset drawdown on a hit
            else:
                current_drawdown_tracker += 1 # Increment drawdown on a miss
            
            max_drawdown = max(max_drawdown, current_drawdown_tracker)

        # Update the simulated engine's learning states with the actual outcome of the current hand
        # This is crucial for backtest learning
        sim_engine._update_learning(
            predicted_outcome=simulated_predicted_outcome, # Use the outcome AI would have predicted
            actual_outcome=actual_outcome_of_current_hand,
            patterns_detected=sim_engine.detect_patterns(simulated_history_up_to_this_point, _build_big_road_data(simulated_history_up_to_this_point)),
            momentum_detected=sim_engine.detect_momentum(simulated_history_up_to_this_point, _build_big_road_data(simulated_history_up_to_this_point)),
            sequences_detected=sim_engine._detect_sequences(simulated_history_up_to_this_point)
        )

    accuracy_percent = (hits / total_bets_counted * 100) if total_bets_counted > 0 else 0

    return {
        "accuracy_percent": accuracy_percent,
        "hits": hits,
        "total_bets": total_bets_counted,
        "max_drawdown": max_drawdown
    }


@st.cache_data(ttl=None) # Added cache for big road data building
def _build_big_road_data(history_list):
    """
    Builds the 2D data structure for Big Road display.
    Handles bending after 6 rows.
    Returns a list of lists, where each inner list is a column of (outcome, ties, is_natural, is_super6) tuples.
    None indicates an empty cell.
    """
    if not history_list:
        return []

    big_road_columns = [] # List of columns
    current_column = [] # Current column being built
    
    # Track the last non-Tie/Super6 outcome to determine when to start a new column
    last_main_pb_outcome = None 

    for i, hand in enumerate(history_list):
        main_outcome = hand['main_outcome']
        is_natural = hand['is_any_natural']
        ties = hand['ties'] # Initial ties for this specific hand, will be incremented for subsequent ties

        # Treat S6 as B for Big Road column logic
        outcome_for_column_logic = 'B' if main_outcome == 'S6' else main_outcome

        # --- Handle Ties (already processed in history for display as tie_count on P/B/S6) ---
        # Ties are handled by incrementing 'ties' count on the P/B/S6 cell they belong to.
        # So no new column or cell is created for a pure 'T' hand here in big_road_data logic.
        # If the history contains standalone 'T' entries (no preceding P/B/S6), they will create new columns/cells.
        
        # If the hand is a Tie that was recorded as a standalone 'T', treat it as a new cell.
        # This occurs if 'T' is the very first hand or follows another standalone 'T'
        if main_outcome == 'T':
            # Create a new column for standalone 'T' for display purposes
            if current_column:
                big_road_columns.append(current_column)
            current_column = [(main_outcome, ties, is_natural, False)] # 'False' for is_super6
            last_main_pb_outcome = None # Standalone T breaks the PB streak logic
            continue # Move to next hand

        # --- Main P/B/S6 Outcome Logic ---
        # Start a new column if the outcome changes from the previous P/B/S6 outcome
        # OR if the current column is full (6 rows) and it's a continuing streak (bending)
        start_new_col = False
        if last_main_pb_outcome is None: # First P/B/S6 outcome in history
            start_new_col = True
        elif outcome_for_column_logic != last_main_pb_outcome: # Outcome changed (P to B, B to P)
            start_new_col = True
        elif len(current_column) >= 6: # Column is full, force new column for bending
            start_new_col = True
        
        if start_new_col:
            if current_column: # Add existing column to big_road_columns if not empty
                big_road_columns.append(current_column)
            current_column = [] # Start a new column
        
        # Add the current hand's data to the current column
        current_column.append((main_outcome, ties, is_natural, main_outcome == 'S6'))
        last_main_pb_outcome = outcome_for_column_logic

    # Add the last current column if it's not empty after the loop
    if current_column:
        big_road_columns.append(current_column)
    
    return big_road_columns
