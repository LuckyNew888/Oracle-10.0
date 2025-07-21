from collections import Counter
import random

class OracleEngine:
    def __init__(self):
        # History will now store richer objects:
        # {'main_outcome': 'P'/'B'/'T', 'ties': int, 'is_any_natural': bool}
        self.history = []
        # Stores success rates of patterns and momentum: {'pattern_name': {'hits': int, 'misses': int}}
        self.pattern_stats = {}
        self.momentum_stats = {}
        # Stores specific pattern instances that led to a miss:
        # {('pattern_type', 'sequence_snapshot_tuple'): count_of_misses}
        self.failed_pattern_instances = {}
        self.backtest_results = [] # Stores results of backtesting: [{'predicted': 'P', 'actual': 'B', 'hit': False}]

    # --- Data Management (for the Engine itself) ---
    # This method is for internal engine use, not directly called by UI for adding new rounds.
    def update_history(self, result_obj):
        """Adds a new result object to the history (for internal engine use)."""
        if isinstance(result_obj, dict) and 'main_outcome' in result_obj:
            self.history.append(result_obj)

    def remove_last(self):
        """Removes the last result from the history."""
        if self.history:
            self.history.pop()
            # When history is removed, we should ideally revert backtest results and pattern stats
            # For simplicity, we'll reset them here. A full undo would be more complex.
            self.backtest_results = []
            self.pattern_stats = {}
            self.momentum_stats = {}
            self.failed_pattern_instances = {}


    def reset_history(self):
        """Resets the entire history and all learning/backtest data."""
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.failed_pattern_instances = {}
        self.backtest_results = []

    def _get_pb_history(self, current_history):
        """Helper to extract only P/B outcomes from structured history."""
        # Ensure current_history is not None or empty before processing
        if not current_history:
            return []
        return [item['main_outcome'] for item in current_history if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B']]

    # --- 1. 🧬 DNA Pattern Analysis (ตรวจจับรูปแบบ) ---
    def detect_patterns(self, current_history):
        """
        Detects various patterns and returns a list of (pattern_name, sequence_snapshot) tuples.
        """
        h = self._get_pb_history(current_history)
        patterns_detected = []

        # Pingpong (B-P-B-P)
        if len(h) >= 4:
            # Check for alternation from the end (at least 3 alternations for 4 results)
            alternating_count = 0
            for i in range(len(h) - 1, 0, -1):
                if h[i] != h[i-1]:
                    alternating_count += 1
                else:
                    break
            if alternating_count >= 3: # e.g., P-B-P-B (3 alternations)
                # Snapshot the sequence that forms the pattern
                snapshot = tuple(h[len(h) - (alternating_count + 1):])
                patterns_detected.append((f'Pingpong ({alternating_count + 1}x)', snapshot))

        # Two-Cut (BB-PP-BB-PP)
        if len(h) >= 4:
            last4 = tuple(h[-4:])
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns_detected.append(('Two-Cut', last4))

        # Dragon (long streak: 3 to 6 consecutive same results)
        for i in range(3, 7):
            if len(h) >= i:
                last_streak = tuple(h[-i:])
                if len(set(last_streak)) == 1:
                    patterns_detected.append((f'Dragon ({i})', last_streak))

        # Triple Cut (e.g., PPPBBB or BBBPPP)
        if len(h) >= 6:
            last6 = tuple(h[-6:])
            if (last6[0] == last6[1] == last6[2] and
                last6[3] == last6[4] == last6[5] and
                last6[0] != last6[3]):
                patterns_detected.append(('Triple Cut', last6))

        # Broken Pattern (BPBPPBP) - Example, can be refined
        if len(h) >= 7:
            last7_str = "".join(h[-7:])
            if "BPBPPBP" in last7_str or "PBPBBBP" in last7_str:
                patterns_detected.append(('Broken Pattern', tuple(h[-7:])))

        return patterns_detected

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self, current_history):
        """
        Detects momentum and returns a list of (momentum_name, sequence_snapshot) tuples.
        """
        h = self._get_pb_history(current_history)
        momentum_detected = []

        # B3+, P3+ Momentum (3 or more consecutive same results)
        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
            for i in reversed(range(len(h))):
                if h[i] == last_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                snapshot = tuple(h[-streak_count:])
                momentum_detected.append((f"{last_char}{streak_count}+ Momentum", snapshot))

        # Steady Repeat (PBPBPBP or BPBPBPB)
        if len(h) >= 7:
            seq_snapshot = tuple(h[-7:])
            if (seq_snapshot == ('P','B','P','B','P','B','P') or
                seq_snapshot == ('B','P','B','P','B','P','B')):
                momentum_detected.append(("Steady Repeat Momentum", seq_snapshot))

        # Ladder Momentum (e.g., BB-P-BBB-P-BBBB) - Conceptual, requires more specific definition
        if len(h) >= 6:
            # Check for patterns like X Y XX Y XXX
            # This is a simplified check for a "ladder"
            # For example, B P BB P BBB
            if h[-1] == h[-3] and h[-3] == h[-6] and h[-2] == h[-4] and h[-4] == h[-5]: # Very simplified
                 momentum_detected.append(("Ladder Momentum (Simplified)", tuple(h[-6:])))

        return momentum_detected

    # --- 3. ⚠️ Trap Zone Detection (ตรวจจับโซนอันตราย) ---
    def in_trap_zone(self, current_history):
        """Detects zones where changes are rapid and dangerous. Uses main_outcome."""
        h = self._get_pb_history(current_history)
        if len(h) < 2:
            return False

        # P1-B1, B1-P1 (Unstable)
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
        pb_history_len = len(self._get_pb_history(current_history))
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
        h = self._get_pb_history(current_history)
        full_h = current_history

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

        return '?'

    # --- 7. 🔬 Backtest Simulation (ทดสอบผลย้อนหลัง) ---
    def backtest_accuracy(self):
        """
        Calculates the system's accuracy from historical predictions and tracks drawdown.
        Simulates predictions from the 11th hand onwards (or 20th, as per confidence threshold).
        """
        # Need at least 20 P/B hands for meaningful backtest, as confidence starts at 20.
        pb_history_len = len(self._get_pb_history(self.history))
        if pb_history_len < 20:
            return {"accuracy_percent": 0, "max_drawdown": 0, "hits": 0, "misses": 0, "total_bets": 0}

        hits = 0
        misses = 0
        current_drawdown = 0
        max_drawdown = 0
        total_bets_counted = 0 # Only count bets where recommendation was 'Play' and prediction was P/B/T

        # Find the starting index for backtest. It should be where the engine can first make a prediction.
        # This is typically after enough history for confidence score (e.g., 20 P/B results).
        # We need to iterate through the full history to find the actual index corresponding to 20 P/B results.
        pb_count = 0
        start_index_for_backtest = 0
        for i, item in enumerate(self.history):
            if item and 'main_outcome' in item and item['main_outcome'] in ['P', 'B']:
                pb_count += 1
            if pb_count >= 20:
                start_index_for_backtest = i + 1 # Start predicting from the next hand
                break
        
        if start_index_for_backtest == 0: # Not enough P/B history even after iterating all
             return {"accuracy_percent": 0, "max_drawdown": 0, "hits": 0, "misses": 0, "total_bets": 0}


        # Simulate predictions for each hand from start_index_for_backtest to the end
        for i in range(start_index_for_backtest, len(self.history)):
            # Get the history up to the current hand (excluding the current hand itself)
            simulated_history = self.history[:i]
            actual_result_obj = self.history[i]
            actual_main_outcome = actual_result_obj['main_outcome']

            # Create a temporary engine instance for simulation to avoid polluting main engine's state
            temp_sim_engine = OracleEngine()
            temp_sim_engine.history = simulated_history
            # Copy learning stats to temp engine for realistic simulation
            temp_sim_engine.pattern_stats = self.pattern_stats.copy()
            temp_sim_engine.momentum_stats = self.momentum_stats.copy()
            temp_sim_engine.failed_pattern_instances = self.failed_pattern_instances.copy()


            # Get prediction for this simulated hand
            simulated_prediction_data = temp_sim_engine.predict_next()
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

    # --- Main function for predicting the next result ---
    def predict_next(self):
        """
        Main function for analyzing and predicting the next outcome.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        current_pb_history = self._get_pb_history(self.history)
        
        # Get backtest stats early, as they are used in multiple checks
        backtest_stats = self.backtest_accuracy()

        # --- 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที) ---
        if self.in_trap_zone(self.history):
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = "Trap Zone detected: High volatility, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": backtest_stats['accuracy_percent'],
                "risk": risk_level,
                "recommendation": recommendation,
                "active_patterns": [], # No patterns considered if avoiding
                "active_momentum": [] # No momentum considered if avoiding
            }

        # --- 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำกว่าเกณฑ์) ---
        score = self.confidence_score(self.history)
        if score < 60:
            recommendation = "Avoid ❌"
            risk_level = "Low Confidence"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%), recommending avoidance."
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
            developer_view = f"Drawdown exceeded 3 consecutive misses ({backtest_stats['max_drawdown']} misses), recommending avoidance."
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

        if patterns:
            developer_view_patterns_list = []
            for p_name, p_snapshot in patterns:
                developer_view_patterns_list.append(p_name)
                # Only add to active_patterns_for_learning if not a failed instance
                if not self._is_pattern_instance_failed(p_name, p_snapshot):
                    active_patterns_for_learning.append((p_name, p_snapshot))

                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self._is_pattern_instance_failed(p_name, p_snapshot):
                    developer_view += f" (Note: Pattern '{p_name}' instance previously failed. Skipping.)"
                    continue # Skip this pattern for prediction if it has failed before

                # ลอจิกการทำนายตาม Pattern ที่มั่นใจ
                if 'Dragon' in p_name:
                    prediction_result = current_pb_history[-1]
                    developer_view = f"DNA Pattern: {p_name} detected. Predicting last result."
                    break
                elif 'Pingpong' in p_name:
                    last = current_pb_history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    developer_view = f"DNA Pattern: {p_name} detected. Predicting opposite of last."
                    break
                elif p_name == 'Two-Cut':
                    if len(current_pb_history) >= 2:
                        last_two = current_pb_history[-2:]
                        if last_two[0] == last_two[1]:
                            prediction_result = 'P' if last_two[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
                elif p_name == 'Triple Cut':
                    if len(current_pb_history) >= 3:
                        last_three = current_pb_history[-3:]
                        if len(set(last_three)) == 1:
                            prediction_result = 'P' if last_three[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Triple Cut detected. Predicting opposite of last three."
                            break

            if developer_view_patterns_list and not developer_view:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            elif developer_view_patterns_list:
                developer_view += f" | Other patterns: {', '.join(developer_view_patterns_list)}."

        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if prediction_result == '?': # ถ้ายังไม่มีการทำนายจาก Pattern หลัก
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

        # Aggregate additional Developer View from Momentum
        if momentum:
            for m_name, m_snapshot in momentum:
                # Only add to active_momentum_for_learning if not a failed instance
                if not self._is_pattern_instance_failed(m_name, m_snapshot):
                    active_momentum_for_learning.append((m_name, m_snapshot))
            if developer_view: developer_view += " | "
            developer_view += f"Momentum: {', '.join([m[0] for m in momentum])}."

        # If nothing at all and still no prediction
        if not developer_view and prediction_result == '?':
            developer_view = "No strong patterns or intuition detected."

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": backtest_stats['accuracy_percent'],
            "risk": risk_level,
            "recommendation": recommendation,
            "active_patterns": active_patterns_for_learning, # Pass for learning
            "active_momentum": active_momentum_for_learning # Pass for learning
        }
