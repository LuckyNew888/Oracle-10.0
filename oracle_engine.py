from collections import Counter
import random
import streamlit as st # Import streamlit for caching

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

@st.cache_data(ttl=60*5) # Cache for 5 minutes, or until inputs change
def _cached_backtest_accuracy(history, pattern_stats, momentum_stats, failed_pattern_instances):
    """
    Calculates the system's accuracy from historical predictions and tracks drawdown.
    This is a global cached function to improve performance.
    """
    pb_history_len = len(_get_pb_history(history))
    if pb_history_len < 20: # Need at least 20 P/B hands for meaningful backtest
        return {"accuracy_percent": 0, "max_drawdown": 0, "hits": 0, "misses": 0, "total_bets": 0}

    hits = 0
    misses = 0
    current_drawdown = 0
    max_drawdown = 0
    total_bets_counted = 0 # Only count bets where recommendation was 'Play' and prediction was P/B/T

    # Find the starting index for backtest. It should be where the engine can first make a prediction.
    pb_count = 0
    start_index_for_backtest = 0
    for i, item in enumerate(history):
        if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B']:
            pb_count += 1
        if pb_count >= 20:
            start_index_for_backtest = i + 1 # Start predicting from the next hand
            break
    
    if start_index_for_backtest == 0: # Not enough P/B history even after iterating all
        return {"accuracy_percent": 0, "max_drawdown": 0, "hits": 0, "misses": 0, "total_bets": 0}


    # Simulate predictions for each hand from start_index_for_backtest to the end
    for i in range(start_index_for_backtest, len(history)):
        simulated_history = history[:i]
        actual_result_obj = history[i]
        actual_main_outcome = actual_result_obj['main_outcome']

        # Create a temporary engine instance for simulation
        temp_sim_engine = OracleEngine(
            initial_pattern_stats=pattern_stats,
            initial_momentum_stats=momentum_stats,
            initial_failed_pattern_instances=failed_pattern_instances
        )
        temp_sim_engine.history = simulated_history # Set history for this simulation step

        # Get prediction for this simulated hand
        simulated_prediction_data = temp_sim_engine.predict_next_for_backtest() # Use a special method for backtest
        simulated_predicted_outcome = simulated_prediction_data['prediction']
        simulated_recommendation = simulated_prediction_data['recommendation']

        # Only count hit/miss if a 'Play' recommendation was given and a P/B/T prediction was made
        if simulated_recommendation == "Play ✅" and simulated_predicted_outcome in ['P', 'B', 'T']:
            total_bets_counted += 1
            if simulated_predicted_outcome == actual_main_outcome:
                hits += 1
                current_drawdown = 0 # Reset drawdown on a hit
            else:
                misses += 1
                current_drawdown += 1
                max_drawdown = max(max_drawdown, current_drawdown) # Update max drawdown

    accuracy_percent = (hits / total_bets_counted * 100) if total_bets_counted > 0 else 0

    return {
        "accuracy_percent": accuracy_percent,
        "max_drawdown": max_drawdown,
        "hits": hits,
        "misses": misses,
        "total_bets": total_bets_counted
    }


class OracleEngine:
    def __init__(self, initial_pattern_stats=None, initial_momentum_stats=None, initial_failed_pattern_instances=None):
        self.history = []
        self.pattern_stats = initial_pattern_stats if initial_pattern_stats is not None else {}
        self.momentum_stats = initial_momentum_stats if initial_momentum_stats is not None else {}
        self.failed_pattern_instances = initial_failed_pattern_instances if initial_failed_pattern_instances is not None else {}

    # --- Data Management (for the Engine itself) ---
    def update_history(self, result_obj):
        """Adds a new result object to the history (for internal engine use)."""
        if isinstance(result_obj, dict) and 'main_outcome' in result_obj:
            self.history.append(result_obj)

    def remove_last(self):
        """Removes the last result from the history."""
        if self.history:
            self.history.pop()
            self.reset_learning_states_on_undo() # Reset learning states

    def reset_learning_states_on_undo(self):
        """Resets only the learning-related states when an undo operation occurs."""
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.failed_pattern_instances = {}

    def reset_history(self):
        """Resets the entire history and all learning/backtest data."""
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.failed_pattern_instances = {}

    def get_current_learning_states(self):
        """Returns the current learning states for caching purposes."""
        return self.pattern_stats, self.momentum_stats, self.failed_pattern_instances

    # --- 1. 🧬 DNA Pattern Analysis (ตรวจจับรูปแบบ) ---
    def detect_patterns(self, current_history):
        """
        Detects various patterns and returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        h = _get_pb_history(current_history)
        streaks = _get_streaks(h)
        patterns_detected = []

        # Pingpong (B-P-B-P...) - streaks of length 1
        # Look for 4, 6, 8 consecutive single streaks
        for length in [4, 6, 8]:
            if len(streaks) >= length and all(s[1] == 1 for s in streaks[-length:]):
                patterns_detected.append((f'Pingpong ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # Dragon (long streak: 3+ consecutive same results)
        if streaks and streaks[-1][1] >= 3:
            patterns_detected.append((f'Dragon ({streaks[-1][0]}{streaks[-1][1]})', tuple(h[-streaks[-1][1]:])))

        # Two-Cut (BB-PP-BB-PP...) - streaks of length 2
        for length in [4, 6]: # Look for 4, 6 consecutive double streaks
            if len(streaks) >= length and all(s[1] == 2 for s in streaks[-length:]):
                patterns_detected.append((f'Two-Cut ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # Triple-Cut (BBB-PPP-BBB-PPP...) - streaks of length 3
        for length in [4]: # Look for 4 consecutive triple streaks
            if len(streaks) >= length and all(s[1] == 3 for s in streaks[-length:]):
                patterns_detected.append((f'Triple-Cut ({length}x)', tuple(h[-sum(s[1] for s in streaks[-length:]):])))

        # One-Two Pattern (B-PP-B-PP...) - streaks like (X,1), (Y,2), (X,1), (Y,2)
        if len(streaks) >= 4:
            last4_streaks = streaks[-4:]
            if (last4_streaks[0][1] == 1 and last4_streaks[1][1] == 2 and
                last4_streaks[2][1] == 1 and last4_streaks[3][1] == 2 and
                last4_streaks[0][0] == last4_streaks[2][0] and
                last4_streaks[1][0] == last4_streaks[3][0] and
                last4_streaks[0][0] != last4_streaks[1][0]):
                patterns_detected.append(('One-Two Pattern', tuple(h[-sum(s[1] for s in last4_streaks):])))

        # Two-One Pattern (BB-P-BB-P...) - streaks like (X,2), (Y,1), (X,2), (Y,1)
        if len(streaks) >= 4:
            last4_streaks = streaks[-4:]
            if (last4_streaks[0][1] == 2 and last4_streaks[1][1] == 1 and
                last4_streaks[2][1] == 2 and last4_streaks[3][1] == 1 and
                last4_streaks[0][0] == last4_streaks[2][0] and
                last4_streaks[1][0] == last4_streaks[3][0] and
                last4_streaks[0][0] != last4_streaks[1][0]):
                patterns_detected.append(('Two-One Pattern', tuple(h[-sum(s[1] for s in last4_streaks):])))
        
        # Broken Pattern (e.g., B P B P P B P) - a common "broken" pattern
        if len(h) >= 7:
            last7_str = "".join(h[-7:])
            if "BPBPPBP" in last7_str or "PBPBBBP" in last7_str:
                patterns_detected.append(('Broken Pattern', tuple(h[-7:])))

        # New: Big Eye Boy (เค้าไพ่ทึบ) - simplified check based on streaks
        # Requires at least 4 streaks. Looks for alternating patterns in streaks.
        if len(streaks) >= 4:
            # Check if the last two streaks are of the same length and alternating color
            if streaks[-1][1] == streaks[-2][1] and streaks[-1][0] != streaks[-2][0]:
                if streaks[-2][1] == streaks[-3][1] and streaks[-2][0] != streaks[-3][0]:
                    patterns_detected.append(('Big Eye Boy (Simple)', tuple(h[-sum(s[1] for s in streaks[-3:]):])))

        # New: Small Road (เค้าไพ่โปร่ง) - simplified check
        # Looks for patterns where the second and third entries in a column are similar.
        # This is hard to do with just linear history. Needs Big Road structure.
        # For now, a very basic interpretation: if the last few results are alternating in a "2-1" fashion (BB P BB P)
        if len(streaks) >= 3:
            s3 = streaks[-3:]
            if s3[0][1] >= 2 and s3[1][1] == 1 and s3[2][1] >= 2 and s3[0][0] == s3[2][0] and s3[0][0] != s3[1][0]:
                patterns_detected.append(('Small Road (Simple)', tuple(h[-sum(s[1] for s in s3):])))

        # New: Cockroach Pig (เค้าไพ่ไม้ขีด) - simplified check
        # Similar to Small Road, but looking for 3-1-3 or 2-1-2 with specific patterns
        if len(streaks) >= 3:
            s3 = streaks[-3:]
            if s3[0][1] >= 3 and s3[1][1] == 1 and s3[2][1] >= 3 and s3[0][0] == s3[2][0] and s3[0][0] != s3[1][0]:
                patterns_detected.append(('Cockroach Pig (Simple)', tuple(h[-sum(s[1] for s in s3):])))


        return patterns_detected

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self, current_history):
        """
        Detects momentum and returns a list of (momentum_name, sequence_snapshot) tuples.
        Momentum often implies continuation of a trend.
        """
        h = _get_pb_history(current_history)
        streaks = _get_streaks(h)
        momentum_detected = []

        # B3+, P3+ Momentum (3 or more consecutive same results) - same as Dragon detection for 3+
        if streaks and streaks[-1][1] >= 3:
            momentum_detected.append((f"{streaks[-1][0]}{streaks[-1][1]}+ Momentum", tuple(h[-streaks[-1][1]:])))

        # Steady Repeat (PBPBPBP or BPBPBPB) - Pingpong of length 7 or more
        for length in [7, 9]:
            if len(streaks) >= length and all(s[1] == 1 for s in streaks[-length:]):
                seq_snapshot = tuple(h[-sum(s[1] for s in streaks[-length:]):])
                if (seq_snapshot == ('P','B','P','B','P','B','P') or
                    seq_snapshot == ('B','P','B','P','B','P','B')):
                    momentum_detected.append((f"Steady Repeat Momentum ({length}x)", seq_snapshot))

        # Ladder Momentum (e.g., B-P-BB-P-BBB) - increasing streak, cut by single, increasing again
        # Simplified check for X, Y, XX, Y, XXX
        if len(streaks) >= 5: # Need at least 5 streaks for X, Y, XX, Y, XXX
            s5 = streaks[-5:]
            # Check for (X,1), (Y,1), (X,2), (Y,1), (X,3)
            if (s5[0][1] == 1 and s5[1][1] == 1 and s5[2][1] == 2 and s5[3][1] == 1 and s5[4][1] == 3 and
                s5[0][0] == s5[2][0] == s5[4][0] and s5[1][0] == s5[3][0] and s5[0][0] != s5[1][0]):
                momentum_detected.append(('Ladder Momentum (1-2-3)', tuple(h[-sum(s[1] for s in s5):])))
        
        # Another simplified ladder: X, Y, XX, Y, XXX
        if len(streaks) >= 4:
            s4 = streaks[-4:]
            # Check for (X, N), (Y, 1), (X, N+1), (Y, 1)
            if (s4[1][1] == 1 and s4[3][1] == 1 and
                s4[0][0] == s4[2][0] and s4[1][0] == s4[3][0] and
                s4[0][0] != s4[1][0] and s4[2][1] == s4[0][1] + 1):
                momentum_detected.append((f'Ladder Momentum (X-Y-XX-Y)', tuple(h[-sum(s[1] for s in s4):])))

        return momentum_detected

    # --- 3. ⚠️ Trap Zone Detection (ตรวจจับโซนอันตราย) ---
    def in_trap_zone(self, current_history):
        """Detects zones where changes are rapid and dangerous. Uses main_outcome."""
        h = _get_pb_history(current_history)
        if len(h) < 2:
            return False

        # P1-B1, B1-P1 (Unstable / Choppy) - very short alternations
        last2 = tuple(h[-2:])
        if last2 in [('P','B'), ('B','P')]:
            return True

        # B3-P1 or P3-B1 → เสี่ยงกลับตัว (3 consecutive then cut)
        if len(h) >= 4:
            last4 = tuple(h[-4:])
            if (last4[0] == last4[1] == last4[2] and last4[2] != last4[3]): # e.g., PPPB or BBBP
                return True
        return False

    # --- 4. 🎯 Confidence Engine (ระบบประเมินความมั่นใจ 0-100%) ---
    def confidence_score(self, current_history):
        """Calculates the system's confidence score for prediction."""
        # Ensure enough P/B history for meaningful score
        pb_history_len = len(_get_pb_history(current_history))
        if pb_history_len < 10: # Minimum 10 P/B results for confidence
            return 0

        patterns = self.detect_patterns(current_history)
        momentum = self.detect_momentum(current_history)
        trap = self.in_trap_zone(current_history)

        score = 50 # Base confidence

        # Factor in pattern and momentum success rates
        for p_name, p_snapshot in patterns:
            stats = self.pattern_stats.get(p_name, {'hits': 0, 'misses': 0})
            total = stats['hits'] + stats['misses']
            if total > 0:
                success_rate = stats['hits'] / total
                score += success_rate * 20 # Patterns with higher success add more confidence
            else: # If no data, still give a small boost for detection
                score += 5

        for m_name, m_snapshot in momentum:
            stats = self.momentum_stats.get(m_name, {'hits': 0, 'misses': 0})
            total = stats['hits'] + stats['misses']
            if total > 0:
                success_rate = stats['hits'] / total
                score += success_rate * 15 # Momentum with higher success add more confidence
            else: # If no data, still give a small boost for detection
                score += 3

        if trap:
            score -= 60 # Significant penalty for trap zone

        # Ensure score is within 0-100 bounds
        score = max(0, min(100, score))
        return int(score)

    # --- 5. 🔁 Memory Logic (จดจำ Pattern ที่เคยพลาด) ---
    def _is_pattern_instance_failed(self, pattern_type, sequence_snapshot):
        """Checks if this specific pattern instance has previously led to a miss."""
        return self.failed_pattern_instances.get((pattern_type, sequence_snapshot), 0) > 0

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected):
        """
        Updates pattern/momentum success statistics and failed pattern instances.
        Called after each actual result is recorded.
        """
        is_hit = (predicted_outcome == actual_outcome)

        # Update pattern stats
        for p_name, p_snapshot in patterns_detected:
            # Only update if the pattern was actually used for prediction (or considered relevant)
            if p_name not in self.pattern_stats:
                self.pattern_stats[p_name] = {'hits': 0, 'misses': 0}
            if is_hit:
                self.pattern_stats[p_name]['hits'] += 1
            else:
                self.pattern_stats[p_name]['misses'] += 1
                # If it was a miss, record the specific failed instance
                failed_key = (p_name, p_snapshot)
                self.failed_pattern_instances[failed_key] = self.failed_pattern_instances.get(failed_key, 0) + 1

        # Update momentum stats
        for m_name, m_snapshot in momentum_detected:
            # Only update if the momentum was actually used for prediction (or considered relevant)
            if m_name not in self.momentum_stats:
                self.momentum_stats[m_name] = {'hits': 0, 'misses': 0}
            if is_hit:
                self.momentum_stats[m_name]['hits'] += 1
            else:
                self.momentum_stats[m_name]['misses'] += 1
                # If it was a miss, record the specific failed instance
                failed_key = (m_name, m_snapshot)
                self.failed_pattern_instances[failed_key] = self.failed_pattern_instances.get(failed_key, 0) + 1


    # --- 6. 🧠 Intuition Logic (ลอจิกเชิงลึกเมื่อไม่มี Pattern ชัดเจน) ---
    def intuition_predict(self, current_history):
        """Uses deep logic to predict when no clear pattern is present."""
        # Use only P/B for most intuition, but full_h for Tie detection
        h = _get_pb_history(current_history)
        full_h = current_history
        streaks = _get_streaks(h)

        if len(h) < 3: # Need at least 3 P/B results for most intuition
            return '?'

        last3_pb = tuple(h[-3:])
        last4_pb = tuple(h[-4:]) if len(h) >= 4 else None

        # Specific Tie patterns (check full history for 'T' presence)
        # Check last 3 actual results for Tie presence
        last3_full = [item['main_outcome'] for item in full_h[-3:] if item and 'main_outcome' in item]
        if 'T' in last3_full and last3_full.count('T') == 1 and last3_full[0] != last3_full[1] and last3_full[1] != last3_full[2]:
            return 'T'
        if len(full_h) >= 4:
            last4_full = [item['main_outcome'] for item in full_h[-4:] if item and 'main_outcome' in item]
            if Counter(last4_full)['T'] >= 2:
                return 'T'

        # Specific P/B patterns
        if last3_pb == ('P','B','P'): # PBP -> P
            return 'P'
        if last3_pb == ('B','B','P'): # BBP -> P (often seen as a reversal after a streak)
            return 'P'
        if last3_pb == ('P','P','B'): # PPB -> B
            return 'B'
        if len(h) >= 5 and tuple(h[-5:]) == ('B','P','B','P','P'): # B P B P P -> B (often a reversal)
            return 'B'
        
        # New Intuition: Repeat Cut (BBPBB -> B) - simplified
        # This is a pattern where a streak is cut, then the original streak continues
        # e.g., B B P B B -> suggests B will continue.
        if len(h) >= 5 and h[-1] == h[-2] and h[-2] != h[-3] and h[-3] != h[-4] and h[-4] == h[-5]:
            # Example: B B P B B (predict B) or P P B P P (predict P)
            # This is a simplified check.
            return h[-1] # Predict the repeated outcome

        # New Intuition: Alternating streaks (e.g., B P BB PP BBB PPP)
        if len(streaks) >= 2:
            last_streak = streaks[-1]
            prev_streak = streaks[-2]
            if last_streak[1] == prev_streak[1]: # If last two streaks are same length, predict opposite
                return 'P' if last_streak[0] == 'B' else 'B'
            
        # New Intuition: Follow the long streak if it's 4+ and then cut
        if len(streaks) >= 2:
            last_streak = streaks[-1]
            prev_streak = streaks[-2]
            if prev_streak[1] >= 4 and last_streak[1] == 1: # e.g., BBBBB P -> predict B
                return prev_streak[0] # Predict continuation of the long streak

        return '?'

    # --- Main function for predicting the next result (for UI display) ---
    def predict_next(self):
        """
        Main function for analyzing and predicting the next outcome for UI display.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        current_pb_history = _get_pb_history(self.history)
        
        # Get backtest stats using the cached global function
        backtest_stats = _cached_backtest_accuracy(
            self.history,
            self.pattern_stats,
            self.momentum_stats,
            self.failed_pattern_instances
        )

        # --- 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที) ---
        if self.in_trap_zone(self.history):
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = f"Trap Zone detected: High volatility. Confidence: {self.confidence_score(self.history)}%. Recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": backtest_stats['accuracy_percent'],
                "risk": risk_level,
                "recommendation": recommendation,
                "active_patterns": [],
                "active_momentum": []
            }

        # --- 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำกว่าเกณฑ์) ---
        score = self.confidence_score(self.history)
        if score < 60: # Keep threshold at 60 for now, but provide more info
            recommendation = "Avoid ❌"
            risk_level = "Low Confidence"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%). Recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": backtest_stats['accuracy_percent'],
                "risk": risk_level,
                "recommendation": recommendation,
                "active_patterns": [],
                "active_momentum": []
            }

        # --- 3. ตรวจสอบ Drawdown (หากเกิน 3 miss ติดกัน ให้งดเดิมพัน) ---
        if backtest_stats['max_drawdown'] >= 3: # If max drawdown exceeds 3 misses
            risk_level = "High Drawdown"
            recommendation = "Avoid ❌"
            developer_view = f"Drawdown exceeded 3 consecutive misses ({backtest_stats['max_drawdown']} misses). Recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": backtest_stats['accuracy_percent'],
                "risk": risk_level,
                "recommendation": recommendation,
                "active_patterns": [],
                "active_momentum": []
            }

        # --- 4. ใช้ Pattern หลักในการทำนาย (หากมี) ---
        patterns = self.detect_patterns(self.history)
        momentum = self.detect_momentum(self.history)

        active_patterns_for_learning = []
        active_momentum_for_learning = []

        # Prioritize prediction based on detected patterns and momentum
        predicted_by_rule = False
        prediction_source = ""

        if patterns:
            developer_view_patterns_list = []
            for p_name, p_snapshot in patterns:
                developer_view_patterns_list.append(p_name)
                # Only add to active_patterns_for_learning if not a failed instance
                if not self._is_pattern_instance_failed(p_name, p_snapshot):
                    active_patterns_for_learning.append((p_name, p_snapshot))

                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self._is_pattern_instance_failed(p_name, p_snapshot):
                    developer_view += f" (Note: Pattern '{p_name}' instance previously failed. Skipping for prediction.)"
                    continue # Skip this pattern for prediction if it has failed before

                # ลอจิกการทำนายตาม Pattern ที่มั่นใจ
                if 'Dragon' in p_name:
                    prediction_result = current_pb_history[-1]
                    prediction_source = f"DNA Pattern: {p_name}. Predicting last result ({prediction_result})."
                    predicted_by_rule = True
                    break
                elif 'Pingpong' in p_name:
                    last = current_pb_history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    prediction_source = f"DNA Pattern: {p_name}. Predicting opposite of last ({prediction_result})."
                    predicted_by_rule = True
                    break
                elif 'Two-Cut' in p_name or 'Triple-Cut' in p_name:
                    if len(current_pb_history) >= 2:
                        last_block_char = _get_streaks(current_pb_history)[-1][0]
                        prediction_result = 'P' if last_block_char == 'B' else 'B'
                        prediction_source = f"DNA Pattern: {p_name}. Predicting opposite of current block ({prediction_result})."
                        predicted_by_rule = True
                        break
                elif 'One-Two Pattern' in p_name:
                    if len(current_pb_history) >= 3: # B-PP-B -> predict PP
                        if current_pb_history[-1] == current_pb_history[-3] and current_pb_history[-1] != current_pb_history[-2]:
                            prediction_result = current_pb_history[-2] # The middle of the pair
                            prediction_source = f"DNA Pattern: {p_name}. Predicting {prediction_result} to complete One-Two."
                            predicted_by_rule = True
                            break
                elif 'Two-One Pattern' in p_name:
                    if len(current_pb_history) >= 3: # BB-P-BB -> predict P
                        if current_pb_history[-1] == current_pb_history[-2] and current_pb_history[-1] != current_pb_history[-3]:
                            prediction_result = current_pb_history[-3] # The single one before
                            prediction_source = f"DNA Pattern: {p_name}. Predicting {prediction_result} to complete Two-One."
                            predicted_by_rule = True
                            break
                elif 'Big Eye Boy' in p_name or 'Small Road' in p_name or 'Cockroach Pig' in p_name:
                    # For these, typically predict continuation of the trend (same as last result)
                    prediction_result = current_pb_history[-1]
                    prediction_source = f"DNA Pattern: {p_name}. Predicting continuation ({prediction_result})."
                    predicted_by_rule = True
                    break


            if developer_view_patterns_list:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            if predicted_by_rule:
                developer_view += f" | Prediction source: {prediction_source}"


        # If no prediction from patterns, try momentum
        if not predicted_by_rule and momentum:
            for m_name, m_snapshot in momentum:
                # Only add to active_momentum_for_learning if not a failed instance
                if not self._is_pattern_instance_failed(m_name, m_snapshot):
                    active_momentum_for_learning.append((m_name, m_snapshot))

                if self._is_pattern_instance_failed(m_name, m_snapshot):
                    developer_view += f" (Note: Momentum '{m_name}' instance previously failed. Skipping for prediction.)"
                    continue

                if 'Momentum' in m_name: # Generic momentum, predict continuation
                    prediction_result = current_pb_history[-1]
                    prediction_source = f"Momentum: {m_name}. Predicting continuation ({prediction_result})."
                    predicted_by_rule = True
                    break
                elif m_name == "Steady Repeat Momentum":
                    if len(current_pb_history) >= 6: # PBPBPB -> predict P
                        prediction_result = current_pb_history[-6] # The one that started the pattern
                        prediction_source = f"Momentum: {m_name}. Predicting {prediction_result} to continue the repeat."
                        predicted_by_rule = True
                        break
                elif 'Ladder Momentum' in m_name:
                    # This logic needs to be very specific based on the ladder type
                    if _get_streaks(self.history) and len(_get_streaks(self.history)) >= 2:
                        last_streak = _get_streaks(self.history)[-1]
                        prev_streak = _get_streaks(self.history)[-2]
                        if last_streak[1] == 1 and prev_streak[1] >= 2: # e.g., BB P -> predict BB
                            prediction_result = prev_streak[0]
                            prediction_source = f"Momentum: {m_name}. Predicting {prediction_result} to continue ladder."
                            predicted_by_rule = True
                            break
                        elif last_streak[1] >= 2 and prev_streak[1] == 1: # e.g., B PP -> predict P
                            prediction_result = prev_streak[0] # The single one before
                            prediction_source = f"Momentum: {m_name}. Predicting {prediction_result} to continue ladder."
                            predicted_by_rule = True
                            break
            if momentum and not prediction_source: # If momentum detected but no prediction made
                momentum_names = [m[0] for m in momentum]
                if developer_view: developer_view += " | "
                developer_view += f"Momentum detected: {', '.join(momentum_names)} (no prediction from momentum)."
            elif predicted_by_rule and not "Prediction source" in developer_view:
                developer_view += f" | Prediction source: {prediction_source}"


        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if not predicted_by_rule: # ถ้ายังไม่มีการทำนายจาก Pattern หลักหรือ Momentum
            intuitive_guess = self.intuition_predict(self.history) # Pass full history for Tie check

            if intuitive_guess == 'T':
                prediction_result = 'T'
                developer_view += " (Intuition Logic: Specific Tie pattern identified.)"
            elif intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view += f" (Intuition Logic: Predicting {intuitive_guess} based on subtle patterns.)"
            else:
                recommendation = "Avoid ❌"
                risk_level = "Uncertainty"
                developer_view += " (Intuition Logic: No strong P/B/T prediction, recommending Avoid.)"
                prediction_result = '?'
        
        # Final check: If still no prediction, and no specific reason to avoid, default to Avoid
        if prediction_result == '?' and recommendation == "Play ✅":
            recommendation = "Avoid ❌"
            risk_level = "Uncertainty"
            developer_view += " (No clear patterns, momentum, or intuition for prediction. Final decision: Recommending Avoid.)"

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": backtest_stats['accuracy_percent'],
            "risk": risk_level,
            "recommendation": recommendation,
            "active_patterns": active_patterns_for_learning, # Pass for learning
            "active_momentum": active_momentum_for_learning # Pass for learning
        }

    # Special predict method for backtesting to avoid infinite recursion with predict_next
    def predict_next_for_backtest(self):
        """
        Simplified prediction for backtesting, without calling backtest_accuracy recursively.
        """
        prediction_result = '?'
        recommendation = "Play ✅" # Assume play for backtest unless a strong avoid rule
        
        current_pb_history = _get_pb_history(self.history)
        streaks = _get_streaks(current_pb_history)

        if self.in_trap_zone(self.history):
            recommendation = "Avoid ❌"
            return {"prediction": prediction_result, "recommendation": recommendation}

        score = self.confidence_score(self.history)
        if score < 60:
            recommendation = "Avoid ❌"
            return {"prediction": prediction_result, "recommendation": recommendation}
        
        # In backtest, we don't use the max_drawdown from the backtest_accuracy itself
        # as that would be circular. We rely on confidence and trap zone.

        patterns = self.detect_patterns(self.history)
        momentum = self.detect_momentum(self.history)

        # Prioritize prediction based on detected patterns
        predicted_by_rule_for_backtest = False
        if patterns:
            for p_name, p_snapshot in patterns:
                if self._is_pattern_instance_failed(p_name, p_snapshot):
                    continue

                if 'Dragon' in p_name:
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
                elif 'One-Two Pattern' in p_name:
                    if streaks and len(streaks) >= 2:
                        last_streak = streaks[-1]
                        prev_streak = streaks[-2]
                        if last_streak[1] == 2 and prev_streak[1] == 1:
                            prediction_result = prev_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
                        elif last_streak[1] == 1 and prev_streak[1] == 2:
                            prediction_result = last_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
                elif 'Two-One Pattern' in p_name:
                    if streaks and len(streaks) >= 2:
                        last_streak = streaks[-1]
                        prev_streak = streaks[-2]
                        if last_streak[1] == 1 and prev_streak[1] == 2:
                            prediction_result = prev_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
                        elif last_streak[1] == 2 and prev_streak[1] == 1:
                            prediction_result = last_streak[0]
                            predicted_by_rule_for_backtest = True
                            break
                elif 'Big Eye Boy' in p_name or 'Small Road' in p_name or 'Cockroach Pig' in p_name:
                    prediction_result = current_pb_history[-1]
                    predicted_by_rule_for_backtest = True
                    break


        # If no prediction from patterns, try momentum
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

        # If still no prediction from patterns or momentum, use intuition
        if not predicted_by_rule_for_backtest:
            intuitive_guess = self.intuition_predict(self.history)
            if intuitive_guess in ['P', 'B', 'T']:
                prediction_result = intuitive_guess
            else:
                recommendation = "Avoid ❌" # If intuition also fails, avoid
        
        return {"prediction": prediction_result, "recommendation": recommendation}
