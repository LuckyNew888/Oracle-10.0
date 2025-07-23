from collections import Counter
import random
import streamlit as st

# --- Helper Functions (outside OracleEngine class) ---
def _get_pb_history(current_history):
    """Helper to extract only P/B outcomes from structured history."""
    if not current_history:
        return []
    return [item['main_outcome'] for item in current_history if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B']]

def _get_streaks(history_pb):
    """Helper to get streaks from a P/B history list. Returns list of (char, length)."""
    if not history_pb:
        return []
    streaks = []
    current_streak_char = history_pb[0]
    current_streak_length = 0
    for char in history_pb:
        if char == current_streak_char:
            current_streak_length += 1
        else:
            streaks.append((current_streak_char, current_streak_length))
            current_streak_char = char
            current_streak_length = 1
    streaks.append((current_streak_char, current_streak_length)) # Add last streak
    return streaks

def _build_big_road_data(full_history_list):
    """
    Builds the Big Road data structure with a fixed vertical height of 6 rows.
    If a streak exceeds 6, it wraps to the next column at the top.
    Returns a list of columns, where each column is a list of (outcome, ties, is_natural) tuples,
    or None for empty cells to maintain grid structure.
    """
    big_road_columns = []
    
    # Track the last P/B outcome to determine if a new streak/column starts
    last_main_pb_outcome = None
    
    # Track the current column and row index for placing the next result
    current_col_idx = -1
    current_row_idx = -1
    
    MAX_ROWS = 6 # Standard Big Road has 6 rows

    for entry_idx, entry in enumerate(full_history_list):
        main_outcome = entry['main_outcome']
        ties = entry.get('ties', 0)
        is_natural = entry.get('is_any_natural', False)

        if main_outcome == 'T':
            # Ties are attached to the most recent P/B outcome in the grid.
            # Find the last actual P/B cell and increment its tie count.
            found_pb_for_tie = False
            for c_idx in reversed(range(len(big_road_columns))):
                for r_idx in reversed(range(len(big_road_columns[c_idx]))):
                    cell = big_road_columns[c_idx][r_idx]
                    if cell is not None and cell[0] in ['P', 'B']:
                        updated_cell = list(cell)
                        updated_cell[1] += 1 # Increment ties
                        big_road_columns[c_idx][r_idx] = tuple(updated_cell)
                        found_pb_for_tie = True
                        break
                if found_pb_for_tie:
                    break
            continue # Ties do not create new cells or affect column/row placement

        # Handle P/B outcomes
        if big_road_columns and main_outcome == last_main_pb_outcome:
            # Same outcome as the previous P/B, so continue the streak
            if current_row_idx < MAX_ROWS - 1: # If not yet at the bottom row (0-5)
                current_row_idx += 1
            else: # Column is full (row_idx is MAX_ROWS - 1), need to start a new column
                current_col_idx += 1
                current_row_idx = 0 # Start at the top of the new column
        else:
            # New streak or first entry
            current_col_idx += 1
            current_row_idx = 0 # Start at the top of a new column
            last_main_pb_outcome = main_outcome # Update the outcome for the new streak

        # Ensure big_road_columns has enough columns
        while len(big_road_columns) <= current_col_idx:
            big_road_columns.append([None] * MAX_ROWS) # Add an empty column, pre-filled with None for 6 rows
        
        # Place the current result
        big_road_columns[current_col_idx][current_row_idx] = (main_outcome, ties, is_natural)
        
    return big_road_columns


@st.cache_data(ttl=60*5) # Cache for 5 minutes, or until inputs change
def _cached_backtest_accuracy(history, pattern_stats, momentum_stats, failed_pattern_instances, sequence_memory_stats, tie_stats, super6_stats):
    """
    Calculates the system's accuracy from historical predictions and tracks max drawdown.
    This is a global cached function to improve performance.
    """
    hits = 0
    misses = 0
    temp_drawdown_for_max = 0 # This tracks consecutive misses for max_drawdown calculation
    max_drawdown = 0
    total_bets_counted = 0

    # Find the starting index for backtest. It should be where the engine can first make a prediction.
    pb_count = 0
    start_index_for_backtest = 0
    for i, item in enumerate(history):
        if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B']:
            pb_count += 1
        if pb_count >= 20: # Need at least 20 P/B hands for meaningful backtest
            start_index_for_backtest = i + 1
            break
    
    if start_index_for_backtest == 0:
        return {"accuracy_percent": 0, "max_drawdown": 0, "hits": 0, "misses": 0, "total_bets": 0}

    # Iterate through the history from the point where predictions can start
    for i in range(start_index_for_backtest, len(history)):
        simulated_history = history[:i] # History up to the current point (excluding current result)
        actual_result_obj = history[i] # The actual result of the current hand
        actual_main_outcome = actual_result_obj['main_outcome']

        # Create a temporary engine to get the prediction for this historical point
        temp_sim_engine = OracleEngine(
            initial_pattern_stats=pattern_stats,
            initial_momentum_stats=momentum_stats,
            initial_failed_pattern_instances=failed_pattern_instances,
            initial_sequence_memory_stats=sequence_memory_stats,
            initial_tie_stats=tie_stats, # Pass tie stats
            initial_super6_stats=super6_stats # Pass super6 stats
        )
        temp_sim_engine.history = simulated_history

        simulated_prediction_data = temp_sim_engine.predict_next_for_backtest()
        simulated_predicted_outcome = simulated_prediction_data['prediction']
        simulated_recommendation = simulated_prediction_data['recommendation'] 

        # --- Logic for overall accuracy (hits/misses/total_bets_counted) ---
        # This counts bets only when the system would have recommended "Play ✅"
        if simulated_recommendation == "Play ✅" and simulated_predicted_outcome in ['P', 'B', 'T', 'S6']: # Include S6
            total_bets_counted += 1
            if simulated_predicted_outcome == actual_main_outcome:
                hits += 1
            else:
                misses += 1
        
        # --- Logic for max_drawdown calculation within backtest ---
        # This counts consecutive hands where a P/B/T/S6 prediction was made and was wrong.
        # It resets only on a correct P/B/T/S6 prediction.
        if simulated_predicted_outcome in ['P', 'B', 'T', 'S6']: # If a specific prediction (P, B, T, S6) was made
            if simulated_predicted_outcome == actual_main_outcome:
                temp_drawdown_for_max = 0 # Reset on a correct P/B/T/S6 prediction
            else:
                temp_drawdown_for_max += 1 # Increment on an incorrect P/B/T/S6 prediction
        else: # If simulated_predicted_outcome is '?'
            temp_drawdown_for_max = 0 # Reset if AI made no specific prediction for this hand

        max_drawdown = max(max_drawdown, temp_drawdown_for_max) 
    
    accuracy_percent = (hits / total_bets_counted * 100) if total_bets_counted > 0 else 0

    return {
        "accuracy_percent": accuracy_percent,
        "max_drawdown": max_drawdown,
        "hits": hits,
        "misses": misses,
        "total_bets": total_bets_counted,
    }


class OracleEngine:
    def __init__(self, initial_pattern_stats=None, initial_momentum_stats=None, initial_failed_pattern_instances=None, initial_sequence_memory_stats=None, initial_tie_stats=None, initial_super6_stats=None):
        self.history = []
        self.pattern_stats = initial_pattern_stats if initial_pattern_stats is not None else {}
        self.momentum_stats = initial_momentum_stats if initial_momentum_stats is not None else {}
        self.failed_pattern_instances = initial_failed_pattern_instances if initial_failed_pattern_instances is not None else {}
        self.sequence_memory_stats = initial_sequence_memory_stats if initial_sequence_memory_stats is not None else {}
        
        # New: Stats for Tie and Super6 predictions
        self.tie_stats = initial_tie_stats if initial_tie_stats is not None else {}
        self.super6_stats = initial_super6_stats if initial_super6_stats is not None else {}

        # Weighted Pattern Scoring: Define base weights for each pattern and momentum
        # Actual contribution to confidence will be modulated by their success rate
        self.pattern_weights = {
            'Dragon': 1.0,
            'FollowStreak': 0.95,
            'Pingpong': 0.9,
            'Two-Cut': 0.8,
            'Triple-Cut': 0.8,
            'One-Two Pattern': 0.7,
            'Two-One Pattern': 0.7,
            'Big Eye Boy (2D Simple - Follow)': 0.9,
            'Big Eye Boy (2D Simple - Break)': 0.8,
            'Small Road (2D Simple - Chop)': 0.75,
            'Cockroach Pig (2D Simple - Chop)': 0.7,
            'Broken Pattern': 0.3,
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9,
            'P3+ Momentum': 0.9,
            'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7,
            'Ladder Momentum (X-Y-XX-Y)': 0.6,
        }
        # Weights for sequence memory (can be adjusted)
        self.sequence_weights = {
            3: 0.6, # Weight for 3-bit sequences
            4: 0.7, # Weight for 4-bit sequences
            5: 0.8, # Weight for 5-bit sequences
        }
        # New: Weights for Tie and Super6 patterns (can be adjusted)
        self.tie_weights = {
            'Tie After PBP': 0.7,
            'Tie After BBP': 0.7,
            'Consecutive Tie': 0.8,
            'Tie Frequency Pattern': 0.6, # Placeholder for more advanced freq analysis
        }
        self.super6_weights = {
            'Super6 After B Streak': 0.6, # Placeholder, highly dependent on actual card data
            'Super6 After P Cut': 0.5, # Placeholder
        }


    # --- Data Management (for the Engine itself) ---
    def update_history(self, result_obj):
        """Adds a new result object to the history (for internal engine use)."""
        if isinstance(result_obj, dict) and 'main_outcome' in result_obj:
            self.history.append(result_obj)

    def remove_last(self):
        """Removes the last result from the history."""
        if self.history:
            self.history.pop()
            self.reset_learning_states_on_undo()

    def reset_learning_states_on_undo(self):
        """Resets only the learning-related states when an undo operation occurs."""
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.failed_pattern_instances = {}
        self.sequence_memory_stats = {}
        self.tie_stats = {} # Reset Tie stats
        self.super6_stats = {} # Reset Super6 stats

    def reset_history(self):
        """Resets the entire history and all learning/backtest data."""
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.failed_pattern_instances = {}
        self.sequence_memory_stats = {}
        self.tie_stats = {} # Reset Tie stats
        self.super6_stats = {} # Reset Super6 stats

    def get_current_learning_states(self):
        """Returns the current learning states for caching purposes."""
        return self.pattern_stats, self.momentum_stats, self.failed_pattern_instances, self.sequence_memory_stats, self.tie_stats, self.super6_stats

    # --- 1. 🧬 DNA Pattern Analysis (Pattern Detection) ---
    def detect_patterns(self, current_history, big_road_data):
        """
        Detects various patterns using both linear history and Big Road data.
        Returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        h = _get_pb_history(current_history)
        streaks = _get_streaks(h)
        patterns_detected = []

        # --- Linear Patterns ---
        # Pingpong (B-P-B-P...) - streaks of length 1
        for length in [4, 6, 8, 10]:
            if len(streaks) >= length and all(s[1] == 1 for s in streaks[-length:]):
                patterns_detected.append((f'Pingpong ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # Dragon (long streak: 3+ consecutive same results)
        if streaks and streaks[-1][1] >= 3:
            patterns_detected.append((f'Dragon ({streaks[-1][0]}{streaks[-1][1]})', tuple(h[-streaks[-1][1]:])))

        # Two-Cut (BB-PP-BB-PP...) - streaks of length 2
        for length in [4, 6, 8]:
            if len(streaks) >= length and all(s[1] == 2 for s in streaks[-length:]):
                patterns_detected.append((f'Two-Cut ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # Triple-Cut (BBB-PPP-BBB-PPP...) - streaks of length 3
        for length in [4, 6]:
            if len(streaks) >= length and all(s[1] == 3 for s in streaks[-length:]):
                patterns_detected.append((f'Triple-Cut ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # Improved One-Two Pattern (1-2-1) and Two-One Pattern (2-1-2)
        # Look for alternating short and medium streaks
        if len(streaks) >= 4:
            s_last_4 = streaks[-4:]
            # Example: B(1) P(2) B(1) P(2) or B(2) P(1) B(2) P(1)
            # Check for alternating characters
            if s_last_4[0][0] != s_last_4[1][0] and \
               s_last_4[1][0] != s_last_4[2][0] and \
               s_last_4[2][0] != s_last_4[3][0]:
                
                # Check for 1-2-1-2 like pattern (short-long-short-long)
                # Allowing some flexibility in streak lengths (e.g., 1-2-1-3 or 1-3-1-2)
                if (s_last_4[0][1] <= 2 and s_last_4[1][1] >= 2 and s_last_4[1][1] <= 3 and \
                    s_last_4[2][1] <= 2 and s_last_4[3][1] >= 2 and s_last_4[3][1] <= 3):
                    patterns_detected.append(('One-Two Pattern (Flexible)', tuple(h[-sum(s[1] for s in s_last_4):])))
                
                # Check for 2-1-2-1 like pattern (long-short-long-short)
                # Allowing some flexibility in streak lengths (e.g., 2-1-3-1 or 3-1-2-1)
                elif (s_last_4[0][1] >= 2 and s_last_4[0][1] <= 3 and s_last_4[1][1] <= 2 and \
                      s_last_4[2][1] >= 2 and s_last_4[2][1] <= 3 and s_last_4[3][1] <= 2):
                    patterns_detected.append(('Two-One Pattern (Flexible)', tuple(h[-sum(s[1] for s in s_last_4):])))

        # Original strict One-Two Pattern (B-PP-B-PP...)
        if len(streaks) >= 4:
            last4_streaks = streaks[-4:]
            if (last4_streaks[0][1] == 1 and last4_streaks[1][1] == 2 and
                last4_streaks[2][1] == 1 and last4_streaks[3][1] == 2 and
                last4_streaks[0][0] == last4_streaks[2][0] and
                last4_streaks[1][0] == last4_streaks[3][0] and
                last4_streaks[0][0] != last4_streaks[1][0]):
                patterns_detected.append(('One-Two Pattern (Strict)', tuple(h[-sum(s[1] for s in last4_streaks):])))

        # Original strict Two-One Pattern (BB-P-BB-P...)
        if len(streaks) >= 4:
            last4_streaks = streaks[-4:]
            if (last4_streaks[0][1] == 2 and last4_streaks[1][1] == 1 and
                last4_streaks[2][1] == 2 and last4_streaks[3][1] == 1 and
                last4_streaks[0][0] == last4_streaks[2][0] and
                last4_streaks[1][0] == last4_streaks[3][0] and
                last4_streaks[0][0] != last4_streaks[1][0]):
                patterns_detected.append(('Two-One Pattern (Strict)', tuple(h[-sum(s[1] for s in last4_streaks):])))
        
        # Broken Pattern
        if len(h) >= 7:
            last7_str = "".join(h[-7:])
            if "BPBPPBP" in last7_str or "PBPBBBP" in last7_str:
                patterns_detected.append(('Broken Pattern', tuple(h[-7:])))

        # FollowStreak (if the last streak is 3 or more, it's a strong trend)
        if streaks and streaks[-1][1] >= 3:
            patterns_detected.append((f'FollowStreak ({streaks[-1][0]}{streaks[-1][1]})', tuple(h[-streaks[-1][1]:])))

        # --- 2D Big Road Patterns (Improved Simplified) ---
        num_cols = len(big_road_data)
        if num_cols >= 3: # Need at least 3 columns for meaningful 2D patterns
            # Note: big_road_data now includes None for bending, so we need to filter for actual cells
            last_col_actual = [cell for cell in big_road_data[-1] if cell is not None]
            prev_col_actual = [cell for cell in big_road_data[-2] if cell is not None]
            
            # Big Eye Boy (Simplified): Check if the pattern "follows the previous column's trend"
            # If the current column's depth is similar to the previous column's depth, it's a "follow"
            # This is a key characteristic of Big Eye Boy.
            if last_col_actual and prev_col_actual: # Ensure columns are not empty after filtering None
                if len(last_col_actual) == len(prev_col_actual) and last_col_actual[0][0] == prev_col_actual[0][0]: # Same depth, same outcome (implies follow)
                    patterns_detected.append(('Big Eye Boy (2D Simple - Follow)', tuple(h[-sum(len([c for c in col if c is not None]) for col in big_road_data[-2:]):])))
                elif len(last_col_actual) == 1 and len(prev_col_actual) > 1 and last_col_actual[0][0] != prev_col_actual[0][0]: # Single cut after a streak (implies break)
                    patterns_detected.append(('Big Eye Boy (2D Simple - Break)', tuple(h[-sum(len([c for c in col if c is not None]) for col in big_road_data[-2:]):])))

            # Small Road (Simplified): Check if the current column is the same as the column two columns back (alternating)
            # This implies a "chop" or "alternating" pattern in the 2D view.
            if num_cols >= 3:
                prev_prev_col_actual = [cell for cell in big_road_data[-3] if cell is not None]
                if last_col_actual and prev_prev_col_actual:
                    if len(last_col_actual) == len(prev_prev_col_actual) and last_col_actual[0][0] == prev_prev_col_actual[0][0]:
                        patterns_detected.append(('Small Road (2D Simple - Chop)', tuple(h[-sum(len([c for c in col if c is not None]) for col in big_road_data[-3:]):])))

            # Cockroach Pig (Simplified): Similar to Small Road, but looking at 3 columns back
            if num_cols >= 4:
                prev_prev_prev_col_actual = [cell for cell in big_road_data[-4] if cell is not None]
                if last_col_actual and prev_prev_prev_col_actual:
                    if len(last_col_actual) == len(prev_prev_prev_col_actual) and last_col_actual[0][0] == prev_prev_prev_col_actual[0][0]:
                        patterns_detected.append(('Cockroach Pig (2D Simple - Chop)', tuple(h[-sum(len([c for c in col if c is not None]) for col in big_road_data[-4:]):])))


        return patterns_detected

    # --- 1.1 New: Memory-based Matching (for short sequences) ---
    def _detect_sequences(self, current_history):
        """
        Detects short, exact sequences in the recent history (e.g., last 3, 4, 5 outcomes).
        Returns a list of (sequence_length, sequence_tuple) tuples.
        """
        h = _get_pb_history(current_history)
        detected_sequences = []

        # Check for sequences of length 3, 4, 5
        for length in [3, 4, 5]:
            if len(h) >= length:
                sequence = tuple(h[-length:])
                detected_sequences.append((length, sequence))
        return detected_sequences

    # --- 2. 🚀 Momentum Tracker (Momentum Detection) ---
    def detect_momentum(self, current_history, big_road_data):
        """
        Detects momentum and returns a list of (momentum_name, sequence_snapshot) tuples.
        Momentum often implies continuation of a trend.
        """
        h = _get_pb_history(current_history)
        streaks = _get_streaks(h)
        momentum_detected = []

        # B3+, P3+ Momentum (3 or more consecutive same results)
        if streaks and streaks[-1][1] >= 3:
            momentum_detected.append((f"{streaks[-1][0]}{streaks[-1][1]}+ Momentum", tuple(h[-streaks[-1][1]:])))

        # Steady Repeat (PBPBPBP or BPBPBPB) - Pingpong of length 7 or more
        for length in [7, 9]:
            if len(streaks) >= length and all(s[1] == 1 for s in streaks[-length:]):
                seq_snapshot = tuple(h[-sum(s[1] for s in streaks[-length:]):])
                momentum_detected.append((f"Steady Repeat Momentum ({length}x)", seq_snapshot))

        # Ladder Momentum (e.g., B-P-BB-P-BBB) - increasing streak, cut by single, increasing again
        if len(streaks) >= 5:
            s5 = streaks[-5:]
            if (s5[0][1] == 1 and s5[1][1] == 1 and s5[2][1] == 2 and s5[3][1] == 1 and s5[4][1] == 3 and
                s5[0][0] == s5[2][0] == s5[4][0] and s5[1][0] == s5[3][0] and s5[0][0] != s5[1][0]):
                momentum_detected.append(('Ladder Momentum (1-2-3)', tuple(h[-sum(s[1] for s in s5):])))
        
        if len(streaks) >= 4:
            s4 = streaks[-4:]
            if (s4[1][1] == 1 and s4[3][1] == 1 and
                s4[0][0] == s4[2][0] and s4[1][0] == s4[3][0] and
                s4[0][0] != s4[1][0] and s4[2][1] == s4[0][1] + 1):
                momentum_detected.append((f'Ladder Momentum (X-Y-XX-Y)', tuple(h[-sum(s[1] for s in s4):])))

        return momentum_detected

    # --- New: Tie and Super6 Pattern Detection ---
    def detect_tie_super6_patterns(self, current_history):
        """
        Detects patterns that might indicate a Tie or Super6.
        Returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        h = _get_pb_history(current_history) # Only P/B history for most patterns
        full_h = current_history # Full history including Ties for Tie-specific patterns
        tie_super6_patterns_detected = []

        # --- Tie Patterns ---
        # Consecutive Ties
        tie_streak_count = 0
        for i in reversed(range(len(full_h))):
            if full_h[i]['main_outcome'] == 'T':
                tie_streak_count += 1
            else:
                break
        if tie_streak_count >= 2: # Detects TT, TTT, etc.
            # Use full_h for snapshot to include 'T' outcomes
            tie_super6_patterns_detected.append((f'Consecutive Tie ({tie_streak_count}x)', tuple([item['main_outcome'] for item in full_h[-tie_streak_count:]])))

        # Tie after specific P/B patterns (e.g., PBP, BBP)
        if len(h) >= 3:
            last3_pb = tuple(h[-3:])
            if last3_pb == ('P', 'B', 'P'):
                tie_super6_patterns_detected.append(('Tie After PBP', last3_pb))
            elif last3_pb == ('B', 'B', 'P'):
                tie_super6_patterns_detected.append(('Tie After BBP', last3_pb))
        
        # Tie frequency pattern (simple check: if ties are unusually frequent in last N hands)
        if len(full_h) >= 10:
            last10_outcomes = [item['main_outcome'] for item in full_h[-10:]]
            tie_count_last10 = last10_outcomes.count('T')
            if tie_count_last10 >= 3: # If 3 or more ties in last 10 hands
                tie_super6_patterns_detected.append(('Tie Frequency Pattern (High in last 10)', tuple(last10_outcomes)))

        # --- Super6 Patterns (Highly speculative without card data) ---
        # Super6 after a Banker streak (very simple, needs refinement with card data)
        if len(h) >= 3 and h[-1] == 'B' and h[-2] == 'B' and h[-3] == 'B':
            # This is a very weak indicator without knowing the exact score
            tie_super6_patterns_detected.append(('Super6 After B Streak (Simple)', tuple(h[-3:])))
        
        # Super6 after a Player cut (another very weak indicator)
        if len(h) >= 2 and h[-1] == 'B' and h[-2] == 'P' and _get_streaks(h)[-1][1] == 1:
            # Player streak of 1, then Banker wins. Could be a Super6.
            tie_super6_patterns_detected.append(('Super6 After P Cut (Simple)', tuple(h[-2:])))

        return tie_super6_patterns_detected

    # --- 4. 🎯 Confidence Engine (2-Layer Confidence Score 0-100%) ---
    def confidence_score(self, current_history, big_road_data):
        """
        Calculates the system's confidence score for prediction (Layer 1: Pattern Stability).
        This layer incorporates Weighted Pattern Scoring and Memory-based Matching.
        """
        pb_history_len = len(_get_pb_history(current_history))
        if pb_history_len < 10:
            return 0

        patterns = self.detect_patterns(current_history, big_road_data)
        momentum = self.detect_momentum(current_history, big_road_data)
        sequences = self._detect_sequences(current_history) # New: Detected sequences
        tie_super6_patterns = self.detect_tie_super6_patterns(current_history) # New: Tie/Super6 patterns
        
        score = 75 # Increased base confidence to be even more proactive

        # Layer 1: Weighted Pattern Scoring based on frequency and stability
        for p_name, p_snapshot in patterns:
            stats = self.pattern_stats.get(p_name, {'hits': 0, 'misses': 0})
            total = stats['hits'] + stats['misses']
            base_weight = self.pattern_weights.get(p_name, 0.5)

            if total > 0:
                success_rate = stats['hits'] / total
                # Dynamic weighting: higher success rate * higher base_weight = higher contribution
                score += success_rate * base_weight * 100
            else: # If no data, still give a significant boost for detection
                score += base_weight * 50 # Boost for new patterns, scaled by base_weight

        for m_name, m_snapshot in momentum:
            stats = self.momentum_stats.get(m_name, {'hits': 0, 'misses': 0})
            total = stats['hits'] + stats['misses']
            base_weight = self.momentum_weights.get(m_name, 0.5)

            if total > 0:
                success_rate = stats['hits'] / total
                score += success_rate * base_weight * 80
            else: # If no data, still give a significant boost for detection
                score += base_weight * 40

        # New: Incorporate Sequence Memory Stats into Confidence
        for length, sequence_tuple in sequences:
            seq_stats = self.sequence_memory_stats.get(sequence_tuple, {'hits': 0, 'misses': 0})
            total_seq = seq_stats['hits'] + seq_stats['misses']
            seq_weight = self.sequence_weights.get(length, 0.5) # Get weight based on sequence length

            if total_seq > 0:
                seq_success_rate = seq_stats['hits'] / total_seq
                score += seq_success_rate * seq_weight * 70 # Scale contribution for sequences
            else:
                score += seq_weight * 30 # Boost for new sequences

        # New: Incorporate Tie/Super6 Pattern Stats into Confidence
        for ts_name, ts_snapshot in tie_super6_patterns:
            if ts_name.startswith('Tie'):
                stats = self.tie_stats.get(ts_name, {'hits': 0, 'misses': 0})
                total = stats['hits'] + stats['misses']
                base_weight = self.tie_weights.get(ts_name, 0.3) # Lower base weight for Tie patterns

                if total > 0:
                    success_rate = stats['hits'] / total
                    score += success_rate * base_weight * 60 # Scaled contribution
                else:
                    score += base_weight * 20
            elif ts_name.startswith('Super6'):
                stats = self.super6_stats.get(ts_name, {'hits': 0, 'misses': 0})
                total = stats['hits'] + stats['misses']
                base_weight = self.super6_weights.get(ts_name, 0.2) # Even lower base weight for Super6

                if total > 0:
                    success_rate = stats['hits'] / total
                    score += success_rate * base_weight * 50 # Scaled contribution
                else:
                    score += base_weight * 15

        score = max(0, min(100, score))
        return int(score)

    # --- 5. 🔁 Memory Logic (Remembering Failed Patterns & Sequences) ---
    def _is_pattern_instance_failed(self, pattern_type, sequence_snapshot):
        """Checks if this specific pattern instance has previously led to a miss."""
        return self.failed_pattern_instances.get((pattern_type, sequence_snapshot), 0) > 0

    def _is_sequence_failed(self, sequence_tuple):
        """Checks if this specific sequence has previously led to a miss."""
        return self.sequence_memory_stats.get(sequence_tuple, {}).get('misses', 0) > 0


    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        """
        Updates pattern/momentum/sequence success statistics and failed pattern instances.
        Called after each actual result is recorded.
        """
        is_hit = (predicted_outcome == actual_outcome)

        # Update Pattern Stats
        for p_name, p_snapshot in patterns_detected:
            if p_name not in self.pattern_stats:
                self.pattern_stats[p_name] = {'hits': 0, 'misses': 0}
            if is_hit:
                self.pattern_stats[p_name]['hits'] += 1
            else:
                self.pattern_stats[p_name]['misses'] += 1
                failed_key = (p_name, p_snapshot)
                self.failed_pattern_instances[failed_key] = self.failed_pattern_instances.get(failed_key, 0) + 1

        # Update Momentum Stats
        for m_name, m_snapshot in momentum_detected:
            if m_name not in self.momentum_stats:
                self.momentum_stats[m_name] = {'hits': 0, 'misses': 0}
            if is_hit:
                self.momentum_stats[m_name]['hits'] += 1
            else:
                self.momentum_stats[m_name]['misses'] += 1
                failed_key = (m_name, m_snapshot)
                self.failed_pattern_instances[failed_key] = self.failed_pattern_instances.get(failed_key, 0) + 1
        
        # Update Sequence Memory Stats
        for length, sequence_tuple in sequences_detected:
            if sequence_tuple not in self.sequence_memory_stats:
                self.sequence_memory_stats[sequence_tuple] = {'hits': 0, 'misses': 0}
            if is_hit:
                self.sequence_memory_stats[sequence_tuple]['hits'] += 1
            else:
                self.sequence_memory_stats[sequence_tuple]['misses'] += 1
        
        # New: Update Tie and Super6 Stats
        # Re-detect patterns for the *current* state (including the just-added actual_outcome)
        # This is crucial for learning from the very last hand.
        # We need to pass the full history to detect_tie_super6_patterns
        tie_super6_patterns_detected_for_learning = self.detect_tie_super6_patterns(self.history) 
        for ts_name, ts_snapshot in tie_super6_patterns_detected_for_learning:
            if ts_name.startswith('Tie'):
                if ts_name not in self.tie_stats:
                    self.tie_stats[ts_name] = {'hits': 0, 'misses': 0}
                if actual_outcome == 'T': # Only count hit if actual outcome was Tie
                    self.tie_stats[ts_name]['hits'] += 1
                else: # Count as miss if actual outcome was not Tie
                    self.tie_stats[ts_name]['misses'] += 1
            elif ts_name.startswith('Super6'):
                if ts_name not in self.super6_stats:
                    self.super6_stats[ts_name] = {'hits': 0, 'misses': 0}
                # Assuming 'S6' is a distinct outcome in actual_outcome for learning
                if actual_outcome == 'S6': 
                    self.super6_stats[ts_name]['hits'] += 1
                else:
                    self.super6_stats[ts_name]['misses'] += 1


    # --- 6. 🧠 Adaptive Intuition Logic (Deep Logic when no clear Pattern) ---
    def intuition_predict(self, current_history):
        """
        Uses deep logic to predict when no clear pattern is present,
        adapting based on the context of the current streak/history.
        """
        h = _get_pb_history(current_history)
        full_h = current_history
        streaks = _get_streaks(h)

        if len(h) < 3:
            return '?'

        last3_pb = tuple(h[-3:])
        
        # Specific Tie patterns (check full history for 'T' presence)
        last3_full = [item['main_outcome'] for item in full_h[-3:] if item and 'main_outcome' in item]
        if 'T' in last3_full and last3_full.count('T') == 1 and last3_full[0] != last3_full[1] and last3_full[1] != last3_full[2]:
            return 'T'
        if len(full_h) >= 4:
            last4_full = [item['main_outcome'] for item in full_h[-4:] if item and 'main_outcome' in item]
            if Counter(last4_full)['T'] >= 2:
                return 'T'

        # Adaptive Logic based on streak length and recent history
        if streaks:
            last_streak = streaks[-1]
            # If current streak is very long (e.g., 5+), lean towards continuation
            if last_streak[1] >= 5:
                return last_streak[0]
            
            # If pingpong (alternating) is dominant in recent history (e.g., last 4 results are PBPB or BPBP)
            if len(h) >= 4 and h[-1] != h[-2] and h[-2] != h[-3] and h[-3] != h[-4]:
                return 'P' if h[-1] == 'B' else 'B' # Predict opposite for pingpong

            # If the last two are same, but previous streak was long and cut (e.g., BBB P B)
            if len(streaks) >= 2:
                prev_streak = streaks[-2]
                if prev_streak[1] >= 4 and last_streak[1] == 1: # Long streak cut by one
                    return prev_streak[0] # Predict continuation of the long streak (often seen after a single cut)

        # General P/B patterns (fallback if no adaptive logic applies)
        if last3_pb == ('P','B','P'):
            return 'P'
        if last3_pb == ('B','B','P'):
            return 'P'
        if last3_pb == ('P','P','B'):
            return 'B'
        if len(h) >= 5 and tuple(h[-5:]) == ('B','P','B','P','P'):
            return 'B'
        
        # Repeat Cut (BBPBB -> B)
        if len(h) >= 5 and h[-1] == h[-2] and h[-2] != h[-3] and h[-3] != h[-4] and h[-4] == h[-5]:
            return h[-1]

        # Alternating streaks (e.g., B P BB PP BBB PPP)
        if len(streaks) >= 2:
            last_streak = streaks[-1]
            prev_streak = streaks[-2]
            if last_streak[1] == prev_streak[1]:
                return 'P' if last_streak[0] == 'B' else 'B'
            
        # If last two are same, predict opposite to break streak (common in choppy)
        if len(h) >= 2 and h[-1] == h[-2]:
            return 'P' if h[-1] == 'B' else 'B'

        # If last two are opposite, predict same as last (common in pingpong)
        if len(h) >= 2 and h[-1] != h[-2]:
            return h[-1]

        return '?'

    # --- Main function for predicting the next result (for UI display) ---
    def predict_next(self):
        """
        Main function for analyzing and predicting the next outcome for UI display.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal" # Default to Normal
        recommendation = "Play ✅" # Default to Play
        developer_view = ""
        decision_path = [] # To log the decision making process

        current_pb_history = _get_pb_history(self.history)
        big_road_data = _build_big_road_data(self.history)

        backtest_stats = _cached_backtest_accuracy(
            self.history,
            self.pattern_stats,
            self.momentum_stats,
            self.failed_pattern_instances,
            self.sequence_memory_stats,
            self.tie_stats, # Pass tie stats
            self.super6_stats # Pass super6 stats
        )

        # --- Debugging Info for Developer View ---
        debug_info = {
            "Current PB History Length": len(current_pb_history),
            "Big Road Columns (P/B only)": [[cell[0] for cell in col if cell is not None] for col in big_road_data], # Adjusted for None cells
            "Raw Patterns Detected": [p[0] for p in self.detect_patterns(self.history, big_road_data)],
            "Raw Momentum Detected": [m[0] for m in self.detect_momentum(self.history, big_road_data)],
            "Raw Sequences Detected": [f"{l}-bit: {s}" for l, s in self._detect_sequences(self.history)],
            "Raw Tie/Super6 Patterns Detected": [ts[0] for ts in self.detect_tie_super6_patterns(self.history)], # New debug info
            "Calculated Confidence Score (Layer 1)": self.confidence_score(self.history, big_road_data),
            "Backtest Max Drawdown": backtest_stats['max_drawdown'],
        }
        developer_view_parts = []
        for key, value in debug_info.items():
            developer_view_parts.append(f"{key}: {value}")
        developer_view = "\n".join(developer_view_parts) + "\n--- Prediction Logic ---\n"


        # --- Main Prediction Logic (Attempt to predict if confidence is high enough) ---
        score = self.confidence_score(self.history, big_road_data)
        
        if score >= 60: # If confidence is 60% or higher, attempt to make a prediction
            decision_path.append(f"Confidence Score (Layer 1: {score}%) is >= 60%. Attempting prediction.")
            patterns = self.detect_patterns(self.history, big_road_data)
            momentum = self.detect_momentum(self.history, big_road_data)
            sequences = self._detect_sequences(self.history)
            tie_super6_patterns = self.detect_tie_super6_patterns(self.history) # Re-detect for current prediction cycle

            active_patterns_for_learning = []
            active_momentum_for_learning = []
            active_sequences_for_learning = []
            active_tie_super6_for_learning = [] # New: For Tie/Super6 patterns

            predicted_by_rule = False
            
            # --- Prioritize Tie/Super6 patterns if they are very strong ---
            # This is a critical decision point: should Tie/Super6 override P/B?
            # For now, let's give them a chance if their specific patterns are detected.
            # We can refine this prioritization later.
            if tie_super6_patterns:
                decision_path.append("Evaluating Tie/Super6 Patterns for prediction:")
                for ts_name, ts_snapshot in tie_super6_patterns:
                    active_tie_super6_for_learning.append((ts_name, ts_snapshot))
                    
                    # Check if this specific Tie/Super6 pattern instance has failed before
                    # For simplicity, we'll use failed_pattern_instances for now, but
                    # ideally Tie/Super6 patterns should have their own failure tracking.
                    if self._is_pattern_instance_failed(ts_name, ts_snapshot): # Using generic failed pattern
                        decision_path.append(f"  - Tie/Super6 Pattern '{ts_name}' instance previously failed. Skipping for prediction.")
                        continue

                    # Predict Tie
                    if ts_name.startswith('Tie'):
                        tie_stats_current = self.tie_stats.get(ts_name, {'hits': 0, 'misses': 0})
                        tie_total = tie_stats_current['hits'] + tie_stats_current['misses']
                        if tie_total > 0 and tie_stats_current['hits'] / tie_total > 0.65: # Only predict if Tie pattern has good success rate
                            prediction_result = 'T'
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {ts_name}. Predicting Tie ({prediction_result}).")
                            break
                    # Predict Super6
                    elif ts_name.startswith('Super6'):
                        super6_stats_current = self.super6_stats.get(ts_name, {'hits': 0, 'misses': 0})
                        super6_total = super6_stats_current['hits'] + super6_stats_current['misses']
                        if super6_total > 0 and super6_stats_current['hits'] / super6_total > 0.65: # Only predict if Super6 pattern has good success rate
                            prediction_result = 'S6' # Use 'S6' as the prediction outcome
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {ts_name}. Predicting Super6 ({prediction_result}).")
                            break
                if predicted_by_rule: # If a Tie or Super6 was predicted, we stop here for primary prediction
                    developer_view += "\n".join(decision_path)
                    return {
                        "developer_view": developer_view,
                        "prediction": prediction_result,
                        "accuracy": backtest_stats['accuracy_percent'],
                        "risk": risk_level,
                        "recommendation": recommendation,
                        "active_patterns": active_patterns_for_learning, # Still pass all detected for dev view
                        "active_momentum": active_momentum_for_learning,
                        "active_sequences": active_sequences_for_learning,
                        "active_tie_super6": active_tie_super6_for_learning,
                    }
                else:
                    decision_path.append("  - Tie/Super6 patterns detected but no strong prediction made or instances failed.")


            # If no prediction from strong Tie/Super6 patterns, proceed with P/B patterns
            if patterns:
                decision_path.append("Evaluating Patterns for prediction:")
                for p_name, p_snapshot in patterns:
                    active_patterns_for_learning.append((p_name, p_snapshot))

                    if self._is_pattern_instance_failed(p_name, p_snapshot):
                        decision_path.append(f"  - Pattern '{p_name}' instance previously failed. Skipping for prediction.")
                        continue

                    # Prediction logic for patterns
                    if 'Dragon' in p_name or 'FollowStreak' in p_name:
                        prediction_result = current_pb_history[-1]
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched {p_name}. Predicting continuation ({prediction_result}).")
                        break
                    elif 'Pingpong' in p_name:
                        last = current_pb_history[-1]
                        prediction_result = 'P' if last == 'B' else 'B'
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched {p_name}. Predicting opposite ({prediction_result}).")
                        break
                    elif 'Two-Cut' in p_name or 'Triple-Cut' in p_name:
                        if len(current_pb_history) >= 2:
                            last_block_char = _get_streaks(current_pb_history)[-1][0]
                            prediction_result = 'P' if last_block_char == 'B' else 'B'
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {p_name}. Predicting opposite of block ({prediction_result}).")
                            break
                    elif 'One-Two Pattern' in p_name: # Covers both strict and flexible
                        if len(current_pb_history) >= 3: # Need at least 3 results for 1-2-1 or 2-1-2 logic
                            last_outcome = current_pb_history[-1]
                            # If the last outcome is the same as the outcome two steps back (e.g., P B P) -> predict B
                            # Or if the last outcome is different from the outcome two steps back (e.g., P P B) -> predict P
                            # This is a simplified logic for 1-2-1 / 2-1-2 type patterns
                            if len(current_pb_history) >= 3:
                                if current_pb_history[-1] == current_pb_history[-3]: # P B P -> predict B
                                    prediction_result = 'P' if last_outcome == 'B' else 'B'
                                else: # P P B -> predict P
                                    prediction_result = current_pb_history[-3]
                            else: # Fallback if not enough history for specific 1-2-1/2-1-2 logic
                                prediction_result = 'P' if last_outcome == 'B' else 'B' # Assume alternation
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {p_name}. Predicting {prediction_result} to complete pattern.")
                            break
                    elif 'Two-One Pattern' in p_name: # Covers both strict and flexible
                        if len(current_pb_history) >= 3: # Need at least 3 results for 1-2-1 or 2-1-2 logic
                            last_outcome = current_pb_history[-1]
                            # If the last outcome is the same as the outcome two steps back (e.g., B P B) -> predict P
                            # Or if the last outcome is different from the outcome two steps back (e.g., B B P) -> predict B
                            # This is a simplified logic for 1-2-1 / 2-1-2 type patterns
                            if len(current_pb_history) >= 3:
                                if current_pb_history[-1] == current_pb_history[-3]: # B P B -> predict P
                                    prediction_result = 'P' if last_outcome == 'B' else 'B'
                                else: # B B P -> predict B
                                    prediction_result = current_pb_history[-3]
                            else: # Fallback if not enough history for specific 1-2-1/2-1-2 logic
                                prediction_result = current_pb_history[-1] # Assume continuation
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {p_name}. Predicting {prediction_result} to complete pattern.")
                            break
                    elif 'Big Eye Boy' in p_name or 'Small Road' in p_name or 'Cockroach Pig' in p_name:
                        prediction_result = current_pb_history[-1] # For simplicity, these 2D patterns often imply continuation of main road trend
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched {p_name}. Predicting continuation ({prediction_result}).")
                        break
                
                if not predicted_by_rule:
                    decision_path.append(f"  - Patterns detected but no prediction made (or all instances failed). Raw patterns: {[p[0] for p in patterns]}")

            # If no prediction from patterns, try momentum
            if not predicted_by_rule and momentum:
                decision_path.append("Evaluating Momentum for prediction:")
                for m_name, m_snapshot in momentum:
                    active_momentum_for_learning.append((m_name, m_snapshot))

                    if self._is_pattern_instance_failed(m_name, m_snapshot):
                        decision_path.append(f"  - Momentum '{m_name}' instance previously failed. Skipping for prediction.")
                        continue

                    if 'Momentum' in m_name:
                        prediction_result = current_pb_history[-1]
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched {m_name}. Predicting continuation ({prediction_result}).")
                        break
                    elif m_name == "Steady Repeat Momentum":
                        if len(current_pb_history) >= 6:
                            prediction_result = current_pb_history[-6]
                            predicted_by_rule = True
                            decision_path.append(f"  - Matched {m_name}. Predicting {prediction_result} to continue repeat.")
                            break
                    elif 'Ladder Momentum' in m_name:
                        streaks = _get_streaks(self.history)
                        if streaks and len(streaks) >= 2:
                            last_streak = streaks[-1]
                            prev_streak = streaks[-2]
                            if last_streak[1] == 1 and prev_streak[1] >= 2:
                                prediction_result = prev_streak[0]
                                predicted_by_rule = True
                                decision_path.append(f"  - Matched {m_name}. Predicting {prediction_result} to continue ladder.")
                                break
                            elif last_streak[1] >= 2 and prev_streak[1] == 1:
                                prediction_result = prev_streak[0]
                                predicted_by_rule = True
                                decision_path.append(f"  - Matched {m_name}. Predicting {prediction_result} to continue ladder.")
                                break
                
                if not predicted_by_rule:
                    decision_path.append(f"  - Momentum detected but no prediction made (or all instances failed). Raw momentum: {[m[0] for m in momentum]}")

            # If no prediction from patterns or momentum, try memory-based sequences
            if not predicted_by_rule and sequences:
                decision_path.append("Evaluating Memory-based Sequences for prediction:")
                sequences.sort(key=lambda x: (x[0], self.sequence_memory_stats.get(x[1], {'hits':0, 'misses':0}).get('hits',0)), reverse=True)
                
                for length, sequence_tuple in sequences:
                    active_sequences_for_learning.append((length, sequence_tuple))
                    seq_stats = self.sequence_memory_stats.get(sequence_tuple, {'hits': 0, 'misses': 0})
                    total_seq = seq_stats['hits'] + seq_stats['misses']

                    if total_seq > 0 and seq_stats['hits'] / total_seq < 0.6: # Only use if success rate is decent
                        decision_path.append(f"  - Sequence {sequence_tuple} has low success rate ({seq_stats['hits']}/{total_seq}). Skipping.")
                        continue
                    
                    if len(sequence_tuple) >= 2 and sequence_tuple[-1] == sequence_tuple[-2]: # Last two are same, implies streak
                        prediction_result = sequence_tuple[-1] # Predict continuation
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched Sequence {sequence_tuple}. Predicting continuation ({prediction_result}).")
                        break
                    elif len(sequence_tuple) >= 2 and sequence_tuple[-1] != sequence_tuple[-2]: # Last two are different, implies alternation
                        prediction_result = 'P' if sequence_tuple[-1] == 'B' else 'B' # Predict alternation
                        predicted_by_rule = True
                        decision_path.append(f"  - Matched Sequence {sequence_tuple}. Predicting alternation ({prediction_result}).")
                        break
                
                if not predicted_by_rule:
                    decision_path.append(f"  - Sequences detected but no prediction made (or all instances failed/low success). Raw sequences: {sequences}")

            # --- Intuition Logic (Used when no clear Primary Pattern or Momentum or Sequence) ---
            if not predicted_by_rule:
                decision_path.append("Applying Intuition Logic (No strong patterns/momentum/sequences):")
                intuitive_guess = self.intuition_predict(self.history)
                if intuitive_guess == 'T':
                    prediction_result = 'T'
                    decision_path.append("  - Intuition Logic: Specific Tie pattern identified.")
                elif intuitive_guess in ['P', 'B']:
                    prediction_result = intuitive_guess
                    decision_path.append(f"  - Intuition Logic: Predicting {intuitive_guess} based on subtle patterns/context.")
                else:
                    prediction_result = '?' # If intuition can't give a strong P/B/T, then no prediction
                    decision_path.append("  - Intuition Logic: No strong P/B/T prediction from intuition.")
        else: # Confidence < 60%
            recommendation = "Avoid ❌"
            risk_level = "Low Confidence"
            decision_path.append(f"Decision: Confidence Score (Layer 1: {score}%) is below threshold (60%). Recommending avoidance.")
            # prediction_result remains '?' from initialization

        # --- No Layer 2 Confidence: Protection systems are removed.
        # Risk_level is now purely informational, and recommendation is based solely on prediction availability.
        
        # Determine risk_level for display (informational only)
        # Simplified risk level based on whether a prediction was made.
        if prediction_result == '?':
            risk_level = "Uncertainty"
            recommendation = "Avoid ❌" # If no prediction, it's an avoid
            decision_path.append("Final Decision: No clear prediction could be made. Defaulting to Avoid.")
        else:
            risk_level = "Normal" # If a prediction was made, it's considered normal risk (as protection is off)
            recommendation = "Play ✅" # If a prediction was made, it's a play
            decision_path.append("Final Decision: Prediction made. Recommending Play.")


        developer_view += "\n".join(decision_path)

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": backtest_stats['accuracy_percent'],
            "risk": risk_level, # Risk level is now informational, and simplified
            "recommendation": recommendation, # Recommendation based on prediction availability
            "active_patterns": active_patterns_for_learning,
            "active_momentum": active_momentum_for_learning,
            "active_sequences": active_sequences_for_learning,
            "active_tie_super6": active_tie_super6_for_learning, # New: Pass active Tie/Super6 patterns
        }

    # Special predict method for backtesting to avoid infinite recursion with predict_next
    def predict_next_for_backtest(self):
        """
        Simplified prediction for backtesting, without calling backtest_accuracy recursively.
        This version reflects the new logic: predict if confidence >= 60%, no protection override.
        """
        prediction_result = '?'
        recommendation = "Play ✅" # Default recommendation for backtest if prediction is made
        
        current_pb_history = _get_pb_history(self.history)
        big_road_data = _build_big_road_data(self.history)
        streaks = _get_streaks(current_pb_history)

        score = self.confidence_score(self.history, big_road_data)
        
        if score < 60:
            recommendation = "Avoid ❌" # If confidence is too low, backtest also avoids
            return {"prediction": prediction_result, "recommendation": recommendation}

        # If confidence is high enough, try to predict
        patterns = self.detect_patterns(self.history, big_road_data)
        momentum = self.detect_momentum(self.history, big_road_data)
        sequences = self._detect_sequences(self.history)
        tie_super6_patterns = self.detect_tie_super6_patterns(self.history) # For backtest

        predicted_by_rule_for_backtest = False

        # --- Prioritize Tie/Super6 for backtest prediction ---
        if tie_super6_patterns:
            for ts_name, ts_snapshot in tie_super6_patterns:
                # Using generic failed pattern check for now
                if self._is_pattern_instance_failed(ts_name, ts_snapshot):
                    continue

                if ts_name.startswith('Tie'):
                    tie_stats_current = self.tie_stats.get(ts_name, {'hits': 0, 'misses': 0})
                    tie_total = tie_stats_current['hits'] + tie_stats_current['misses']
                    if tie_total > 0 and tie_stats_current['hits'] / tie_total > 0.65:
                        prediction_result = 'T'
                        predicted_by_rule_for_backtest = True
                        break
                elif ts_name.startswith('Super6'):
                    super6_stats_current = self.super6_stats.get(ts_name, {'hits': 0, 'misses': 0})
                    super6_total = super6_stats_current['hits'] + super6_stats_current['misses']
                    if super6_total > 0 and super6_stats_current['hits'] / super6_total > 0.65:
                        prediction_result = 'S6'
                        predicted_by_rule_for_backtest = True
                        break
            if predicted_by_rule_for_backtest:
                return {"prediction": prediction_result, "recommendation": recommendation}

        # Prioritize patterns for backtest prediction
        if not predicted_by_rule_for_backtest and patterns:
            for p_name, p_snapshot in patterns:
                if self._is_pattern_instance_failed(p_name, p_snapshot):
                    continue

                if 'Dragon' in p_name or 'FollowStreak' in p_name:
                    prediction_result = current_pb_history[-1]
                    predicted_by_rule_for_backtest = True
                    break
                elif 'Pingpong' in p_name:
                    last = current_pb_history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    predicted_by_rule_for_backtest = True
                    break
                elif 'Two-Cut' in p_name or 'Triple-Cut' in p_name:
                    if len(current_pb_history) >= 2:
                        last_block_char = _get_streaks(current_pb_history)[-1][0]
                        prediction_result = 'P' if last_block_char == 'B' else 'B'
                        predicted_by_rule_for_backtest = True
                        break
                elif 'One-Two Pattern' in p_name: # Covers both strict and flexible
                    if len(current_pb_history) >= 3:
                        last_outcome = current_pb_history[-1]
                        if current_pb_history[-1] == current_pb_history[-3]:
                            prediction_result = 'P' if last_outcome == 'B' else 'B'
                        else:
                            prediction_result = current_pb_history[-3]
                    else:
                        prediction_result = 'P' if current_pb_history[-1] == 'B' else 'B'
                    predicted_by_rule_for_backtest = True
                    break
                elif 'Two-One Pattern' in p_name: # Covers both strict and flexible
                    if len(current_pb_history) >= 3:
                        last_outcome = current_pb_history[-1]
                        if current_pb_history[-1] == current_pb_history[-3]:
                            prediction_result = 'P' if last_outcome == 'B' else 'B'
                        else:
                            prediction_result = current_pb_history[-3]
                    else:
                        prediction_result = current_pb_history[-1]
                    predicted_by_rule_for_backtest = True
                    break
                elif 'Big Eye Boy' in p_name or 'Small Road' in p_name or 'Cockroach Pig' in p_name:
                    prediction_result = current_pb_history[-1]
                    predicted_by_rule_for_backtest = True
                    break

        # If no prediction from patterns, try momentum for backtest
        if not predicted_by_rule_for_backtest and momentum:
            for m_name, m_snapshot in momentum:
                if self._is_pattern_instance_failed(m_name, m_snapshot):
                    continue
                if 'Momentum' in m_name:
                    prediction_result = current_pb_history[-1]
                    predicted_by_rule_for_backtest = True
                    break
                elif m_name == "Steady Repeat Momentum":
                    if len(current_pb_history) >= 6:
                        prediction_result = current_pb_history[-6]
                        predicted_by_rule_for_backtest = True
                        break
                elif 'Ladder Momentum' in m_name:
                    if streaks and len(streaks) >= 2:
                        last_streak = streaks[-1]
                        prev_streak = streaks[-2]
                        if last_streak[1] == 1 and prev_streak[1] >= 2:
                            prediction_result = prev_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
                        elif last_streak[1] >= 2 and prev_streak[1] == 1:
                            prediction_result = prev_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
        
        # If no prediction from patterns or momentum, try memory-based sequences for backtest
        if not predicted_by_rule_for_backtest and sequences:
            sequences.sort(key=lambda x: (x[0], self.sequence_memory_stats.get(x[1], {'hits':0, 'misses':0}).get('hits',0)), reverse=True)
            for length, sequence_tuple in sequences:
                seq_stats = self.sequence_memory_stats.get(sequence_tuple, {'hits': 0, 'misses': 0})
                total_seq = seq_stats['hits'] + seq_stats['misses']
                if total_seq > 0 and seq_stats['hits'] / total_seq < 0.6:
                    continue

                if len(sequence_tuple) >= 2 and sequence_tuple[-1] == sequence_tuple[-2]:
                    prediction_result = sequence_tuple[-1]
                    predicted_by_rule_for_backtest = True
                    break
                elif len(sequence_tuple) >= 2 and sequence_tuple[-1] != sequence_tuple[-2]:
                    prediction_result = 'P' if sequence_tuple[-1] == 'B' else 'B'
                    predicted_by_rule_for_backtest = True
                    break

        # If still no prediction, use intuition logic for backtest
        if not predicted_by_rule_for_backtest:
            intuitive_guess = self.intuition_predict(self.history)
            if intuitive_guess in ['P', 'B', 'T']:
                prediction_result = intuitive_guess
            else:
                recommendation = "Avoid ❌" # If intuition can't give a strong P/B/T, avoid

        # No protection system override for backtest recommendation either
        if prediction_result == '?':
            recommendation = "Avoid ❌" # If no prediction could be made, it's an avoid
        else:
            recommendation = "Play ✅" # If a prediction was made, it's a play

        return {"prediction": prediction_result, "recommendation": recommendation}
