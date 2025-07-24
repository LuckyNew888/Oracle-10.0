from collections import Counter
import random
import math
import streamlit as st # Only for @st.cache_data

# Define the current version of the OracleEngine logic
# This is used by streamlit_app.py for compatibility checks.
__version__ = "1.10" # Updated version to 1.10

class OracleEngine:
    def __init__(self):
        # --- Core History and Learning States ---
        self.history = []  # Stores actual game results (list of dicts)
        self.pattern_stats = {}  # {'PatternName': {'hits': X, 'misses': Y}}
        self.momentum_stats = {}  # {'MomentumName': {'hits': X, 'misses': Y}}
        self.sequence_memory_stats = {} # {'sequence_tuple': {'hits': X, 'misses': Y}}
        self.tie_stats = {} # {'TiePatternName': {'hits': X, 'misses': Y}}
        self.super6_stats = {} # {'Super6PatternName': {'hits': X, 'misses': Y}}
        self.failed_pattern_instances = {}  # {('PatternName', sequence_tuple): count_failed}

        # --- Prediction Parameters (Tunable) ---
        self.CONFIDENCE_THRESHOLD = 60 # Min confidence for specific prediction (P/B/T/S6)
        self.DRAWDOWN_LIMIT_FOR_AVOID = 5 # If live_drawdown >= this, force Avoid
        self.TIE_RECOMMENDATION_THRESHOLD = 50 # Min confidence for Tie prediction
        self.SUPER6_RECOMMENDATION_THRESHOLD = 60 # Min confidence for Super6 prediction

        # Weights for confidence calculation
        self.pattern_weights = {
            'Dragon': 1.0,
            'FollowStreak': 0.9,
            'Pingpong': 0.8,
            'Two-Cut': 0.7,
            'Triple-Cut': 0.7,
            'One-Two Pattern': 0.6,
            'Two-One Pattern': 0.6,
            'Broken Pattern': 0.2, # Low weight for chaotic patterns
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9,
            'P3+ Momentum': 0.9,
            'Steady Repeat Momentum': 0.7,
            'Ladder Momentum (1-2-3)': 0.6,
            'Ladder Momentum (X-Y-XX-Y)': 0.5,
        }
        self.sequence_weights = {
            '3-bit': 0.6,
            '4-bit': 0.7,
            '5-bit': 0.8,
        }
        # Weights for Tie/Super6 patterns are now calculated based on their theoretical probability + empirical freq.
        # So specific weights here might be less critical.

        # Theoretical probabilities for Tie/Super6 (for blending)
        self.THEORETICAL_TIE_PROB = 0.0951 # Approx 9.51%
        self.THEORETICAL_SUPER6_PROB = 0.0128 # Approx 1.28%

        # Minimum hands required for empirical frequency to start blending
        # Below this, relies more on theoretical. Above, relies more on empirical.
        self.MIN_HANDS_FOR_EMPIRICAL_TIE_SUPER6 = 20
        self.FULL_EMPIRICAL_TIE_SUPER6_HANDS = 80 # After this many hands, rely fully on empirical

    def reset_history(self):
        """Resets all history and learning states for a new shoe."""
        self.history = []
        self.reset_learning_states_on_undo()

    def reset_learning_states_on_undo(self):
        """Resets only learning states, used for undo or re-initialization."""
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.tie_stats = {}
        self.super6_stats = {}
        self.failed_pattern_instances = {}


    # --- Helper Functions for Pattern Detection ---
    def _get_pb_history(self, current_history):
        """Extracts only Player/Banker/Super6 results from history, ignoring Ties."""
        pb_history = []
        for item in current_history:
            if item and 'main_outcome' in item:
                if item['main_outcome'] == 'T': # Ties are attached, not main P/B history points for streaks
                    continue
                # Treat S6 as 'B' for general P/B pattern detection
                pb_history.append('B' if item['main_outcome'] == 'S6' else item['main_outcome'])
        return pb_history
    
    def _get_streaks(self, pb_history):
        """
        Converts a list of P/B outcomes into a list of (outcome, count) streaks.
        Example: ['P', 'P', 'B', 'B', 'B', 'P'] -> [('P', 2), ('B', 3), ('P', 1)]
        """
        if not pb_history:
            return []
        
        streaks = []
        current_streak_char = pb_history[0]
        current_streak_count = 0
        
        for char in pb_history:
            if char == current_streak_char:
                current_streak_count += 1
            else:
                streaks.append((current_streak_char, current_streak_count))
                current_streak_char = char
                current_streak_count = 1
        streaks.append((current_streak_char, current_streak_count)) # Add the last streak
        return streaks

    # --- 1. 🧬 DNA Pattern Analysis (Detects Patterns) ---
    def detect_patterns(self, current_history, big_road_data):
        """
        Detects various patterns in the game history, including 2D patterns.
        Returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        patterns_detected = []
        pb_history = self._get_pb_history(current_history)
        h = pb_history # Use pb_history for linear pattern detection
        streaks = self._get_streaks(h)
        
        # Ensure sufficient history for pattern detection
        if len(h) < 4: # Most patterns need at least 4 P/B outcomes
            return patterns_detected

        # --- Linear Patterns (from h - P/B history) ---
        
        # Dragon (long streak: 3+ consecutive of same outcome)
        for i in range(3, min(len(h) + 1, 10)): # Check for dragons up to 10 length
            if len(set(h[-i:])) == 1:
                patterns_detected.append((f'Dragon ({i}x)', tuple(h[-i:])))
                # If it's a long dragon (>=4), also add FollowStreak for more weight
                if i >= 4:
                    patterns_detected.append(('FollowStreak', tuple(h[-i:])))

        # Pingpong (Alternating P/B pattern) - Check for 1-1-1...
        pingpong_count = 0
        for i in range(len(h) - 1, 0, -1):
            if h[i] != h[i-1]:
                pingpong_count += 1
            else:
                break
        if pingpong_count >= 3: # At least 3 alternations (e.g., PBPB is 3 alternations)
            patterns_detected.append((f'Pingpong ({pingpong_count + 1}x)', tuple(h[-(pingpong_count + 1):])))
            if pingpong_count + 1 >= 5: # If it's a long pingpong, add Steady Repeat for more weight
                patterns_detected.append(('Steady Repeat Momentum', tuple(h[-(pingpong_count + 1):])))

        # Two-Cut (XXYYXXYY) - 2-2-2...
        if len(streaks) >= 2:
            # Check last 2 pairs of streaks for 2-2 pattern
            for i in range(len(streaks) - 1):
                if streaks[i][1] == 2 and streaks[i+1][1] == 2:
                    # Check for XXYY, YYXX
                    if (len(h) >= 4 and h[-4] == h[-3] and h[-2] == h[-1] and h[-4] != h[-2]):
                        patterns_detected.append(('Two-Cut', tuple(h[-4:])))
                    if (len(h) >= 6 and h[-6] == h[-5] and h[-4] == h[-3] and h[-2] == h[-1] and h[-6] != h[-4] and h[-4] != h[-2]):
                        patterns_detected.append(('Two-Cut (6x)', tuple(h[-6:])))
                    if (len(h) >= 8 and h[-8] == h[-7] and h[-6] == h[-5] and h[-4] == h[-3] and h[-2] == h[-1] and h[-8] != h[-6] and h[-6] != h[-4] and h[-4] != h[-2]):
                        patterns_detected.append(('Two-Cut (8x)', tuple(h[-8:])))

        # Triple-Cut (XXXYYYXXXYYY) - 3-3-3...
        if len(streaks) >= 2:
            # Check last 2 pairs of streaks for 3-3 pattern
            for i in range(len(streaks) - 1):
                if streaks[i][1] == 3 and streaks[i+1][1] == 3:
                    # Check for XXXYYY, YYYXXX
                    if (len(h) >= 6 and h[-6] == h[-5] == h[-4] and h[-3] == h[-2] == h[-1] and h[-6] != h[-3]):
                        patterns_detected.append(('Triple-Cut', tuple(h[-6:])))
                    if (len(h) >= 12 and h[-12:-9] == h[-9:-6] == h[-6:-3] == h[-3:] and h[-12] != h[-9] and h[-9] != h[-6] and h[-6] != h[-3]):
                         patterns_detected.append(('Triple-Cut (12x)', tuple(h[-12:])))


        # One-Two Pattern (1-2-1-2) e.g., B PP B PP
        if len(streaks) >= 4:
            # Look for recent streaks that match 1,2,1,2 sequence in terms of outcome and count
            if (streaks[-4][1] == 1 and streaks[-3][1] == 2 and
                streaks[-2][1] == 1 and streaks[-1][1] == 2 and
                streaks[-4][0] == streaks[-2][0] and
                streaks[-3][0] == streaks[-1][0] and
                streaks[-4][0] != streaks[-3][0]):
                patterns_detected.append(('One-Two Pattern', tuple(h[-sum(s[1] for s in streaks[-4:]):])))

        # Two-One Pattern (2-1-2-1) e.g., BB P BB P
        if len(streaks) >= 4:
            # Look for recent streaks that match 2,1,2,1 sequence in terms of outcome and count
            if (streaks[-4][1] == 2 and streaks[-3][1] == 1 and
                streaks[-2][1] == 2 and streaks[-1][1] == 1 and
                streaks[-4][0] == streaks[-2][0] and
                streaks[-3][0] == streaks[-1][0] and
                streaks[-4][0] != streaks[-3][0]):
                patterns_detected.append(('Two-One Pattern', tuple(h[-sum(s[1] for s in streaks[-4:]):])))

        # --- 2D Patterns (from big_road_data) ---
        if big_road_data and len(big_road_data) >= 3: # Need at least 3 columns for 2D patterns
            # Note: 2D patterns (Big Eye Boy, Small Road, Cockroach Pig) are complex
            # This is a simplified "Rule-based" implementation.
            # Real 2D patterns require specific algorithms for drawing roads.

            # We need at least 3 columns for Big Eye Boy/Small Road/Cockroach Pig
            # Get the last 3 columns for analysis
            current_col = [c for c in big_road_data[-1] if c is not None]
            prev_col_full = [c for c in big_road_data[-2] if c is not None]
            prev_prev_col_full = [c for c in big_road_data[-3] if c is not None]

            if len(current_col) >=1 and len(prev_col_full) >=1 and len(prev_prev_col_full) >=1:
                # Big Eye Boy (Simplified: Checks if current col follows 2nd prev col's pattern or breaks)
                # Follow (Red Dot) or Break (Blue Dot) logic
                # Rule: Look at the current position relative to two columns left.
                # If prev_prev_col_full[0] is not same outcome as prev_col_full[0], it's a "break" (similar to zigzag)
                # If prev_prev_col_full[0] is same outcome as prev_col_full[0], it's a "follow" (similar to streak)

                # Get the outcome of the first cell in 2nd and 3rd previous columns
                prev_col_first_outcome = prev_col_full[0][0] # Outcome of the first cell in the previous column
                prev_prev_col_first_outcome = prev_prev_col_full[0][0] # Outcome of the first cell in the 2nd previous column
                
                # Check for Chop (alternating between 2nd and 3rd col)
                if prev_col_first_outcome != prev_prev_col_first_outcome:
                    patterns_detected.append(('Big Eye Boy (2D Simple - Chop)', tuple(h[-2:]))) # Example pattern snapshot

                # Check for Streak (same as 2nd prev col)
                if prev_col_first_outcome == prev_prev_col_first_outcome:
                    patterns_detected.append(('Big Eye Boy (2D Simple - Follow)', tuple(h[-2:]))) # Example pattern snapshot


                # Small Road (Simplified: Checks if current col matches 3rd prev col's pattern or breaks)
                if len(big_road_data) >= 4:
                    prev_prev_prev_col_full = [c for c in big_road_data[-4] if c is not None]
                    if len(prev_prev_prev_col_full) >=1:
                        prev_prev_prev_col_first_outcome = prev_prev_prev_col_full[0][0]
                        
                        # Fix UnboundLocalError: Ensure prev_prev_prev_col_first_outcome is correctly assigned
                        # This line itself was causing the UnboundLocalError.
                        # It should assign the value, not try to use it before assignment.
                        # The logic implies checking if the current result would create a pattern with the 3rd previous.
                        # Let's simplify the check to avoid this error and make it more direct.

                        # A simplified way to check Small Road / Cockroach Pig (using 1st and 2nd cells of previous columns)
                        # Simplified Rule: Checks if the column 3 places to the left is a continuation or break.
                        # If (prev_col[0] == prev_prev_prev_col[0]) it's a follow. Else it's a chop.
                        
                        if prev_col_full[0][0] == prev_prev_prev_col_full[0][0]:
                            patterns_detected.append(('Small Road (2D Simple - Follow)', tuple(h[-2:])))
                        else:
                            patterns_detected.append(('Small Road (2D Simple - Chop)', tuple(h[-2:])))
                
                # Cockroach Pig (Simplified: Similar to Small Road, checks if current matches 4th prev col)
                if len(big_road_data) >= 5:
                    prev_prev_prev_prev_col_full = [c for c in big_road_data[-5] if c is not None]
                    if len(prev_prev_prev_prev_col_full) >=1:
                        # Similar simplified logic for Cockroach Pig
                        if prev_col_full[0][0] == prev_prev_prev_prev_col_full[0][0]:
                            patterns_detected.append(('Cockroach Pig (2D Simple - Follow)', tuple(h[-2:])))
                        else:
                            patterns_detected.append(('Cockroach Pig (2D Simple - Chop)', tuple(h[-2:])))
        return patterns_detected

    # --- 2. 🚀 Momentum Tracker (Detects Momentum) ---
    def detect_momentum(self, current_history, big_road_data):
        """
        Detects various momentum patterns.
        Returns a list of (momentum_name, sequence_snapshot) tuples.
        """
        momentum_detected = []
        pb_history = self._get_pb_history(current_history)
        h = pb_history
        streaks = self._get_streaks(h)

        if len(h) < 3:
            return momentum_detected
        
        # B3+, P3+ Momentum (3+ consecutive of same outcome) - already covered by Dragon
        # This will mainly be about detecting if the *current* outcome forms a momentum

        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
            for i in reversed(range(len(h))):
                if h[i] == last_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                momentum_detected.append((f"{last_char}{streak_count}+ Momentum", tuple(h[-streak_count:])))

        # Steady Repeat Momentum (PBPBPBP or BPBPBPB) - long alternating
        if len(h) >= 7:
            if all(h[i] != h[i+1] for i in range(len(h)-7, len(h)-1)):
                momentum_detected.append(("Steady Repeat Momentum", tuple(h[-7:])))

        # Ladder Momentum (1-2-3) - B-P-BB-P-BBB
        if len(streaks) >= 3:
            # Check for current ladder up to 3
            if streaks[-1][1] == 3 and streaks[-2][1] == 1 and streaks[-3][1] == 2:
                momentum_detected.append(('Ladder Momentum (1-2-3)', tuple(h[-sum(s[1] for s in streaks[-3:]):])))
            elif streaks[-1][1] == 2 and streaks[-2][1] == 3 and streaks[-3][1] == 1:
                momentum_detected.append(('Ladder Momentum (3-1-2)', tuple(h[-sum(s[1] for s in streaks[-3:]):])))

        # Ladder Momentum (X-Y-XX-Y) - e.g. B-P-BB-P-BBB-P
        if len(streaks) >= 4:
            if (streaks[-4][1] == streaks[-2][1] - 1 and # Y-X-Y-XX
                streaks[-3][1] == streaks[-1][1] and
                streaks[-4][0] == streaks[-2][0] and
                streaks[-3][0] == streaks[-1][0]):
                momentum_detected.append(('Ladder Momentum (X-Y-XX-Y)', tuple(h[-sum(s[1] for s in streaks[-4:]):])))

        return momentum_detected
    
    # --- Sequence Memory Logic ---
    def _detect_sequences(self, current_history):
        """
        Detects short sequences (3, 4, 5 bits) for memory-based matching.
        Returns a list of (sequence_name, sequence_tuple) tuples.
        """
        sequences_detected = []
        pb_history = self._get_pb_history(current_history)
        h = pb_history # Use pb_history for sequence detection

        if len(h) >= 3:
            sequences_detected.append(('3-bit', tuple(h[-3:])))
        if len(h) >= 4:
            sequences_detected.append(('4-bit', tuple(h[-4:])))
        if len(h) >= 5:
            sequences_detected.append(('5-bit', tuple(h[-5:])))
        
        return sequences_detected

    # --- Tie and Super6 Pattern Analysis (Module for T and S6) ---
    def detect_tie_super6_patterns(self, current_history):
        """
        Detects patterns specifically related to Tie and Super6 outcomes.
        Returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        tie_super6_patterns = []
        h = current_history # Use full history for Tie/Super6 to include T/S6 outcomes
        
        # Ensure sufficient history for pattern detection
        if len(h) < 2:
            return tie_super6_patterns

        # --- Tie Patterns ---
        # Consecutive Ties (TT, TTT)
        if len(h) >= 2 and h[-1]['main_outcome'] == 'T' and h[-2]['main_outcome'] == 'T':
            tie_super6_patterns.append(('Consecutive Tie (TT)', tuple([r['main_outcome'] for r in h[-2:]])))
        if len(h) >= 3 and h[-1]['main_outcome'] == 'T' and h[-2]['main_outcome'] == 'T' and h[-3]['main_outcome'] == 'T':
            tie_super6_patterns.append(('Consecutive Tie (TTT)', tuple([r['main_outcome'] for r in h[-3:]])))

        # Tie after PBP pattern (PBPT)
        if len(h) >= 4 and h[-1]['main_outcome'] == 'T':
            pb_h = self._get_pb_history(h[:-1]) # P/B history before the Tie
            if len(pb_h) >= 3 and pb_h[-1] == 'B' and pb_h[-2] == 'P' and pb_h[-3] == 'B':
                tie_super6_patterns.append(('Tie after B-P-B', tuple([r['main_outcome'] for r in h[-4:]])))
            if len(pb_h) >= 3 and pb_h[-1] == 'P' and pb_h[-2] == 'B' and pb_h[-3] == 'P':
                tie_super6_patterns.append(('Tie after P-B-P', tuple([r['main_outcome'] for r in h[-4:]])))

        # Tie after Dragon broken
        if len(h) >= 4 and h[-1]['main_outcome'] == 'T':
            pb_h = self._get_pb_history(h[:-1])
            if len(pb_h) >= 3 and len(set(pb_h[-3:])) == 1: # P/B streak of 3
                if len(h) >= 4 and h[-4]['main_outcome'] != h[-3]['main_outcome']: # Broken by opposite in previous hand
                    tie_super6_patterns.append(('Tie after Dragon Broken', tuple([r['main_outcome'] for r in h[-4:]])))
        
        # --- Super6 Patterns ---
        # Super6 after Banker Streak
        if len(h) >= 2 and h[-1]['main_outcome'] == 'S6':
            pb_h = self._get_pb_history(h[:-1])
            if len(pb_h) >= 1 and pb_h[-1] == 'B': # S6 after B
                tie_super6_patterns.append(('Super6 after Banker', tuple([r['main_outcome'] for r in h[-2:]])))
            if len(pb_h) >= 2 and pb_h[-1] == 'B' and pb_h[-2] == 'B': # S6 after BB
                tie_super6_patterns.append(('Super6 after Double Banker', tuple([r['main_outcome'] for r in h[-3:]])))
        
        # Super6 after Choppy/Pingpong
        if len(h) >= 5 and h[-1]['main_outcome'] == 'S6':
            pb_h = self._get_pb_history(h[:-1])
            pingpong_like = all(pb_h[i] != pb_h[i+1] for i in range(len(pb_h)-4, len(pb_h)-1)) # PBPB pattern
            if len(pb_h) >= 4 and pingpong_like:
                tie_super6_patterns.append(('Super6 after Pingpong-like', tuple([r['main_outcome'] for r in h[-5:]])))

        return tie_super6_patterns

    # --- 3. ⚠️ Trap Zone Detection (Detects dangerous zones) ---
    # Moved inside predict_next logic to provide developer_view info directly

    # --- 4. 🎯 Confidence Engine (Calculates Confidence Score) ---
    def confidence_score(self, current_history, big_road_data):
        """
        Calculates a confidence score for the prediction.
        Based on pattern frequency, momentum stability, and memory-based matching.
        """
        score = 75 # Starting confidence
        pb_history = self._get_pb_history(current_history)
        
        patterns = self.detect_patterns(current_history, big_road_data)
        momentum = self.detect_momentum(current_history, big_road_data)
        sequences = self._detect_sequences(current_history)

        # Confidence from Patterns
        for p_name, p_seq in patterns:
            p_stats = self.pattern_stats.get(p_name, {'hits': 0, 'misses': 0})
            total = p_stats['hits'] + p_stats['misses']
            weight = self.pattern_weights.get(p_name, 0.5) # Default weight if not found

            if total >= 3: # Only consider patterns with at least 3 occurrences
                success_rate = p_stats['hits'] / total
                score += success_rate * weight * 10 # Scale based on success rate and weight

        # Confidence from Momentum
        for m_name, m_seq in momentum:
            m_stats = self.momentum_stats.get(m_name, {'hits': 0, 'misses': 0})
            total = m_stats['hits'] + m_stats['misses']
            weight = self.momentum_weights.get(m_name, 0.5)

            if total >= 3:
                success_rate = m_stats['hits'] / total
                score += success_rate * weight * 8

        # Confidence from Sequence Memory
        for s_name, s_seq in sequences:
            s_stats = self.sequence_memory_stats.get(s_seq, {'hits': 0, 'misses': 0})
            total = s_stats['hits'] + s_stats['misses']
            weight = self.sequence_weights.get(s_name, 0.5) # Use sequence_name to get weight

            if total >= 2: # Sequences need fewer occurrences to be considered
                success_rate = s_stats['hits'] / total
                score += success_rate * weight * 15 # Sequences can have high impact

        # Confidence from failed patterns (negative impact)
        for fp_seq_tuple in self.failed_pattern_instances:
            # Check if any currently detected pattern/sequence matches a failed instance
            for p_name, p_seq in patterns:
                if (p_name, p_seq) == fp_seq_tuple:
                    score -= 30 # Significant penalty for recently failed patterns
            for m_name, m_seq in momentum:
                if (m_name, m_seq) == fp_seq_tuple:
                    score -= 20
            for s_name, s_seq in sequences:
                if (s_name, s_seq) == fp_seq_tuple:
                    score -= 25

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        return score

    # --- 5. 🔁 Memory Logic (Remembers Failed Patterns) ---
    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        """
        Updates learning states based on prediction outcome.
        This includes pattern_stats, momentum_stats, sequence_memory_stats,
        and failed_pattern_instances.
        """
        # Update Pattern Stats
        for p_name, p_seq in patterns_detected:
            self.pattern_stats.setdefault(p_name, {'hits': 0, 'misses': 0})
            if predicted_outcome != '?': # Only update if a specific prediction was made by the AI
                if self._get_predicted_main_outcome(predicted_outcome, actual_outcome) == actual_outcome: # Simplified hit check for now
                    self.pattern_stats[p_name]['hits'] += 1
                else:
                    self.pattern_stats[p_name]['misses'] += 1

        # Update Momentum Stats
        for m_name, m_seq in momentum_detected:
            self.momentum_stats.setdefault(m_name, {'hits': 0, 'misses': 0})
            if predicted_outcome != '?':
                if self._get_predicted_main_outcome(predicted_outcome, actual_outcome) == actual_outcome:
                    self.momentum_stats[m_name]['hits'] += 1
                else:
                    self.momentum_stats[m_name]['misses'] += 1

        # Update Sequence Memory Stats
        for s_name, s_seq in sequences_detected:
            self.sequence_memory_stats.setdefault(s_seq, {'hits': 0, 'misses': 0})
            if predicted_outcome != '?':
                if self._get_predicted_main_outcome(predicted_outcome, actual_outcome) == actual_outcome:
                    self.sequence_memory_stats[s_seq]['hits'] += 1
                else:
                    self.sequence_memory_stats[s_seq]['misses'] += 1
                    # Add to failed instances if this specific sequence was a miss
                    # Using a generic key, as we don't know which specific pattern used this sequence
                    self.failed_pattern_instances[(s_name, s_seq)] = self.failed_pattern_instances.get((s_name, s_seq), 0) + 1

        # Update Tie/Super6 Stats (based on their specific predictions from get_tie_opportunity_analysis)
        # This part requires prediction from the tie_super6 analysis, not just overall predicted_outcome
        # This will be updated later when we integrate get_tie_opportunity_analysis's prediction.
        pass # For now, tie/super6 stats are updated indirectly or in get_tie_opportunity_analysis

    def _get_predicted_main_outcome(self, predicted_outcome, actual_outcome):
        """Helper to determine the actual outcome for hit/miss comparison, especially for S6."""
        if actual_outcome == 'S6':
            return 'B' # Super6 is a Banker win
        return actual_outcome

    # --- 6. 🧠 Intuition Logic (Deep Logic when patterns are unclear) ---
    def intuition_predict(self, current_history):
        """
        Uses deep logic to predict when patterns are unclear.
        Returns prediction ('P', 'B', 'T', 'S6') or '?'
        """
        pb_history = self._get_pb_history(current_history)
        h = pb_history

        if len(h) < 3:
            return '?'

        last3 = tuple(h[-3:])
        last4 = tuple(h[-4:]) if len(h) >= 4 else None
        
        # Intuition for specific sequences (e.g., PBP -> P)
        if last3 == ('P','B','P'): return 'P'
        if last3 == ('B','P','B'): return 'B' # Added counterpart
        if last3 == ('B','B','P'): return 'P'
        if last3 == ('P','P','B'): return 'B'
        
        # Repeat Cut (e.g., BBPBB -> B)
        if len(h) >= 5 and tuple(h[-5:]) == ('B','B','P','B','B'): return 'B'
        if len(h) >= 5 and tuple(h[-5:]) == ('P','P','B','P','P'): return 'P' # Added counterpart

        # Try to predict the continuation of a short streak or alternation
        if len(h) >= 2:
            if h[-1] == h[-2]: # Streak of 2, predict continuation
                return h[-1]
            elif h[-1] != h[-2]: # Alternating, predict alternation
                return 'P' if h[-1] == 'B' else 'B'

        return '?' # Fallback if no strong intuition

    # --- Helper for Backtest (outside class for caching) ---
# NOTE: _cached_backtest_accuracy is defined outside the class in Streamlit_app.py
# because @st.cache_data requires the function to be at the module level.
# It receives all necessary states as arguments.


    # --- Tie and Super6 Opportunity Analysis Module ---
    def get_tie_opportunity_analysis(self, current_history):
        """
        Analyzes the opportunity for Tie or Super6 based on historical frequency and patterns.
        Returns a dictionary: {'prediction': 'T'/'S6'/'?', 'confidence': X, 'reason': '...'}.
        """
        tie_pred_outcome = '?'
        tie_confidence = 0
        tie_reason = "ยังไม่มีการวิเคราะห์"

        total_hands_pb = len(self._get_pb_history(current_history)) # Count P/B/S6 hands only for frequency calculation
        total_hands_actual = len(current_history) # Total hands including Ties

        # Count actual Ties and Super6 in history
        actual_ties_count = sum(1 for hand in current_history if hand['main_outcome'] == 'T')
        actual_super6_count = sum(1 for hand in current_history if hand['main_outcome'] == 'S6')

        # --- Calculate Blended Confidence for Tie ---
        empirical_tie_freq = actual_ties_count / total_hands_actual if total_hands_actual > 0 else 0
        
        # Blending Factor: Starts at 0 (all theoretical) and moves to 1 (all empirical)
        # Based on how many P/B hands have passed
        blending_factor_tie = max(0, min(1, (total_hands_pb - self.MIN_HANDS_FOR_EMPIRICAL_TIE_SUPER6) / \
                                      (self.FULL_EMPIRICAL_TIE_SUPER6_HANDS - self.MIN_HANDS_FOR_EMPIRICAL_TIE_SUPER6)))
        
        blended_tie_freq = (self.THEORETICAL_TIE_PROB * (1 - blending_factor_tie)) + \
                           (empirical_tie_freq * blending_factor_tie)
        
        # Convert frequency to Confidence (e.g., 0-100 scale, with 50 as neutral)
        # Assuming theoretical prob gives ~50 confidence
        # And empirical above theoretical pushes it up, below pulls it down
        tie_confidence = min(100, max(0, 50 + (blended_tie_freq - self.THEORETICAL_TIE_PROB) / self.THEORETICAL_TIE_PROB * 50))
        # Clamp confidence for very low or very high freqs to avoid extreme values.
        tie_confidence = max(0, min(100, tie_confidence))


        # --- Calculate Blended Confidence for Super6 ---
        empirical_super6_freq = actual_super6_count / total_hands_actual if total_hands_actual > 0 else 0
        
        blending_factor_super6 = max(0, min(1, (total_hands_pb - self.MIN_HANDS_FOR_EMPIRICAL_TIE_SUPER6) / \
                                         (self.FULL_EMPIRICAL_TIE_SUPER6_HANDS - self.MIN_HANDS_FOR_EMPIRICAL_TIE_SUPER6)))
        
        blended_super6_freq = (self.THEORETICAL_SUPER6_PROB * (1 - blending_factor_super6)) + \
                              (empirical_super6_freq * blending_factor_super6)
        
        super6_confidence = min(100, max(0, 50 + (blended_super6_freq - self.THEORETICAL_SUPER6_PROB) / self.THEORETICAL_SUPER6_PROB * 50))
        super6_confidence = max(0, min(100, super6_confidence))


        # Update Tie/Super6 Stats for tracking (not used for prediction here, just for debug/log)
        self.tie_stats.setdefault('Tie_Freq_Tracker', {'hits': 0, 'misses': 0})
        self.tie_stats['Tie_Freq_Tracker']['hits'] = actual_ties_count
        self.tie_stats['Tie_Freq_Tracker']['misses'] = total_hands_actual - actual_ties_count

        self.super6_stats.setdefault('Super6_Freq_Tracker', {'hits': 0, 'misses': 0})
        self.super6_stats['Super6_Freq_Tracker']['hits'] = actual_super6_count
        self.super6_stats['Super6_Freq_Tracker']['misses'] = total_hands_actual - actual_super6_count


        # --- Decision Logic for Tie/Super6 Recommendation ---
        # Prioritize Super6 if its confidence is significantly higher AND meets its threshold
        if super6_confidence >= self.SUPER6_RECOMMENDATION_THRESHOLD and \
           super6_confidence > tie_confidence + 10: # S6 must be significantly higher than Tie
            tie_pred_outcome = 'S6'
            tie_reason = f"ความถี่ Super6 ในขอนนี้สูงผิดปกติ ({empirical_super6_freq:.2%}) (อิงตามความถี่ในขอนปัจจุบัน {total_hands_actual} ตา)"
            return {'prediction': tie_pred_outcome, 'confidence': super6_confidence, 'reason': tie_reason}
        
        # Then consider Tie if its confidence is high enough and not significantly lower than S6
        elif tie_confidence >= self.TIE_RECOMMENDATION_THRESHOLD:
            tie_pred_outcome = 'T'
            tie_reason = f"ความถี่ Tie ในขอนนี้สูงผิดปกติ ({empirical_tie_freq:.2%}) (อิงตามความถี่ในขอนปัจจุบัน {total_hands_actual} ตา)"
            return {'prediction': tie_pred_outcome, 'confidence': tie_confidence, 'reason': tie_reason}
        
        else: # No strong recommendation for Tie/Super6
            tie_reason = f"ยังไม่พบแนวโน้ม Tie/Super6 ที่ชัดเจน (อิงตามความถี่ในขอนปัจจุบัน {total_hands_actual} ตา)"
            return {'prediction': '?', 'confidence': 0, 'reason': tie_reason}


    # --- Main Prediction Function ---
    def predict_next(self, current_live_drawdown):
        """
        Main function to analyze and predict the next outcome.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view_parts = [] # Collect messages for developer_view

        pb_history = self._get_pb_history(self.history)
        big_road_data = _build_big_road_data(self.history) # Pass full history to get big road

        # --- Layer 2 Confidence: Drawdown Protection (Highest Priority) ---
        if current_live_drawdown >= self.DRAWDOWN_LIMIT_FOR_AVOID:
            prediction_result = '?'
            recommendation = "Avoid ❌ (ป้องกันแพ้ติดกัน)"
            risk_level = "High Drawdown"
            developer_view_parts.append(f"High Drawdown ({current_live_drawdown} misses) detected. Forcing Avoid.")
            return {
                "developer_view": "\n".join(developer_view_parts),
                "prediction": prediction_result,
                "accuracy": 0, # Not relevant when avoiding
                "risk": risk_level,
                "recommendation": recommendation,
                "current_live_drawdown": current_live_drawdown # Pass through for display
            }

        # --- Layer 1 Confidence (Primary Prediction based on Patterns) ---
        score = self.confidence_score(self.history, big_road_data)
        developer_view_parts.append(f"Initial Confidence Score (Layer 1): {score}")

        if score < self.CONFIDENCE_THRESHOLD:
            prediction_result = '?'
            recommendation = "Avoid ❌"
            risk_level = "Low Confidence"
            developer_view_parts.append(f"Confidence Score ({score}%) is below threshold ({self.CONFIDENCE_THRESHOLD}%). Recommending Avoid.")
            return {
                "developer_view": "\n".join(developer_view_parts),
                "prediction": prediction_result,
                "accuracy": 0, # Not relevant when avoiding
                "risk": risk_level,
                "recommendation": recommendation,
                "current_live_drawdown": current_live_drawdown
            }

        # --- Main Prediction Logic ---
        # If confidence is sufficient, try to find a prediction
        patterns = self.detect_patterns(self.history, big_road_data)
        momentum = self.detect_momentum(self.history, big_road_data)
        sequences = self._detect_sequences(self.history)

        # Prioritize based on pattern strength and recent hits
        strong_predictions = []

        # Predict based on strong patterns
        for p_name, p_seq in patterns:
            p_stats = self.pattern_stats.get(p_name, {'hits': 0, 'misses': 0})
            total = p_stats['hits'] + p_stats['misses']
            if total > 0:
                success_rate = p_stats['hits'] / total
                if success_rate >= 0.7: # Consider a pattern strong if its success rate is >= 70%
                    if 'Dragon' in p_name or 'FollowStreak' in p_name:
                        strong_predictions.append((h[-1], 20)) # Predict last, high weight
                    elif 'Pingpong' in p_name:
                        strong_predictions.append(('P' if h[-1] == 'B' else 'B', 15)) # Predict opposite, medium weight
                    elif 'Two-Cut' in p_name:
                        strong_predictions.append(('P' if h[-1] == h[-2] else h[-1], 10)) # Predict opposite of pair or follow last, medium weight
                    elif 'Triple-Cut' in p_name:
                        strong_predictions.append(('P' if h[-1] == h[-2] else h[-1], 10)) # Predict opposite of triple or follow last, medium weight
                    elif 'One-Two Pattern' in p_name:
                        strong_predictions.append(('P' if h[-1] == 'B' else 'B', 8)) # Predict opposite, medium weight
                    elif 'Two-One Pattern' in p_name:
                        strong_predictions.append((h[-1], 8)) # Predict same, medium weight
                    # Add 2D pattern predictions with appropriate weights
                    if '2D Simple - Follow' in p_name:
                         strong_predictions.append((h[-1], 12)) # Tendency to follow
                    if '2D Simple - Chop' in p_name:
                         strong_predictions.append(('P' if h[-1] == 'B' else 'B', 12)) # Tendency to chop

        # Predict based on strong momentum
        for m_name, m_seq in momentum:
            m_stats = self.momentum_stats.get(m_name, {'hits': 0, 'misses': 0})
            total = m_stats['hits'] + m_stats['misses']
            if total > 0:
                success_rate = m_stats['hits'] / total
                if success_rate >= 0.7:
                    if '+' in m_name: # B3+, P3+
                        strong_predictions.append((h[-1], 18)) # Predict last, high weight
                    elif 'Steady Repeat' in m_name:
                        strong_predictions.append(('P' if h[-1] == 'B' else 'B', 14)) # Predict opposite, medium weight
                    elif 'Ladder Momentum' in m_name:
                        strong_predictions.append((h[-1], 10)) # Predict last, medium weight

        # Predict based on sequences if they have high success rates
        for s_name, s_seq in sequences:
            s_stats = self.sequence_memory_stats.get(s_seq, {'hits': 0, 'misses': 0})
            total = s_stats['hits'] + s_stats['misses']
            if total > 0 and s_stats['hits'] / total >= 0.8: # Very high success rate for sequences
                # This logic assumes sequence stats store what should be predicted next for that sequence.
                # For now, just use the last element as the predicted outcome.
                strong_predictions.append((s_seq[-1], 25)) # Predict based on sequence, very high weight

        # Aggregate predictions
        if strong_predictions:
            # Simple voting based on predicted outcome and weight
            prediction_votes = Counter()
            for pred_outcome, weight in strong_predictions:
                prediction_votes[pred_outcome] += weight
            
            most_common_prediction, _ = prediction_votes.most_common(1)[0]
            
            # Final check against failed instances
            is_failed_pattern_in_current_prediction = False
            for fp_seq_tuple in self.failed_pattern_instances:
                fp_name, fp_seq = fp_seq_tuple
                if fp_name in [p[0] for p in patterns] and fp_seq == most_common_prediction: # Simplified check
                     is_failed_pattern_in_current_prediction = True
                     break
            
            if is_failed_pattern_in_current_prediction:
                developer_view_parts.append(f"Warning: Primary prediction '{most_common_prediction}' is based on a pattern previously failed. Falling back to intuition or '?'")
                prediction_result = self.intuition_predict(self.history)
                if prediction_result == '?':
                    recommendation = "Avoid ❌"
                    risk_level = "Uncertainty (Failed Pattern)"
            else:
                prediction_result = most_common_prediction
                developer_view_parts.append(f"Strongest prediction from patterns/momentum/sequences: {prediction_result}")
        else:
            # Fallback to Intuition if no strong patterns detected
            intuitive_guess = self.intuition_predict(self.history)
            if intuitive_guess != '?':
                prediction_result = intuitive_guess
                developer_view_parts.append(f"No strong patterns. Using Intuition Logic: {prediction_result}.")
            else:
                prediction_result = '?'
                recommendation = "Avoid ❌"
                risk_level = "Uncertainty (No Patterns)"
                developer_view_parts.append("No strong patterns or intuition detected.")


        # Final Check on Recommendation
        if prediction_result == '?':
            recommendation = "Avoid ❌"
        else:
            recommendation = "Play ✅"


        return {
            "developer_view": "\n".join(developer_view_parts),
            "prediction": prediction_result,
            "accuracy": 0, # Placeholder, calculated by cached_backtest_accuracy
            "risk": risk_level,
            "recommendation": recommendation,
            "current_live_drawdown": current_live_drawdown
        }

