import random

class OracleEngine:
    """
    The core prediction engine for ORACLE Baccarat.
    This engine analyzes historical outcomes to detect patterns, momentum,
    and trap zones, calculates a confidence score, and provides a prediction
    along with risk assessment and recommendation.
    It uses a stateless approach for history management, relying on the caller
    (e.g., Streamlit app) to provide the full history.
    """
    def __init__(self):
        # Performance tracking for patterns and momentum
        # { 'pattern_name': {'success': count, 'fail': count} }
        self.pattern_performance = {
            'Pingpong': {'success': 0, 'fail': 0},
            'Dragon': {'success': 0, 'fail': 0},
            'Two-Cut': {'success': 0, 'fail': 0},
            'Triple-Cut': {'success': 0, 'fail': 0},
            'One-Two Pattern': {'success': 0, 'fail': 0},
            'Two-One Pattern': {'success': 0, 'fail': 0},
            'Broken Pattern': {'success': 0, 'fail': 0},
            'FollowStreak': {'success': 0, 'fail': 0} # Added FollowStreak here
        }
        self.momentum_performance = {
            'B3+ Momentum': {'success': 0, 'fail': 0},
            'P3+ Momentum': {'success': 0, 'fail': 0},
            'Steady Repeat Momentum': {'success': 0, 'fail': 0},
            'Ladder Momentum (1-2-3)': {'success': 0, 'fail': 0},
            'Ladder Momentum (X-Y-XX-Y)': {'success': 0, 'fail': 0}
        }
        self.intuition_performance = {
            'PBP -> P': {'success': 0, 'fail': 0},
            'BBPBB -> B': {'success': 0, 'fail': 0},
            'PPBPP -> P': {'success': 0, 'fail': 0},
            'Steady Outcome Guess': {'success': 0, 'fail': 0}
        }

        # Weights for different analysis modules
        self.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Broken Pattern': 0.6
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6
        }
        
        # Memory Logic: Stores patterns that have failed prediction
        # { 'pattern_name': count_of_failures_in_current_room }
        self.memory_blocked_patterns = {}
        self.MEMORY_BLOCK_THRESHOLD = 2 # Block pattern if it failed this many times

        # Context from the last prediction attempt for learning
        self.last_prediction_context = {
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False,
            'predicted_by': None # Store which specific pattern/logic made the prediction
        }

        self.trap_zone_active = False # Flag for trap zone detection

    def reset_history(self):
        """Resets all learning states and prediction contexts."""
        for perf_dict in [self.pattern_performance, self.momentum_performance, self.intuition_performance]:
            for key in perf_dict:
                perf_dict[key]['success'] = 0
                perf_dict[key]['fail'] = 0
        self.memory_blocked_patterns.clear()
        self.last_prediction_context = {
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False,
            'predicted_by': None
        }
        self.trap_zone_active = False

    def get_success_rate(self, perf_dict, key):
        """Calculates success rate for a given pattern/momentum."""
        stats = perf_dict.get(key, {'success': 0, 'fail': 0})
        total = stats['success'] + stats['fail']
        return stats['success'] / total if total > 0 else 0.5 # Default to 0.5 if no data

    def get_weighted_success_rate(self, perf_dict, key, base_weight):
        """Calculates weighted success rate for confidence calculation."""
        success_rate = self.get_success_rate(perf_dict, key)
        return success_rate * base_weight

    # --- 1. 🧬 DNA Pattern Analysis ---
    def detect_dna_patterns(self, history):
        """
        Detects common Baccarat patterns in the history.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            list: List of detected pattern names.
        """
        patterns = []
        if len(history) < 4: # Need at least 4 for basic patterns like Pingpong/Two-Cut
            return patterns

        # Get last 15 outcomes for pattern detection to be more robust
        seq = ''.join([item['main_outcome'] for item in history[-15:] if item['main_outcome'] != 'T']) # Exclude Ties for core patterns

        # Pingpong (e.g., PBPB, BPBP - at least 3 alternations)
        if len(seq) >= 6 and (seq.endswith('PBPBPB') or seq.endswith('BPBPBP')):
            patterns.append('Pingpong')
        elif len(seq) >= 4 and (seq.endswith('PBPB') or seq.endswith('BPBP')):
            patterns.append('Pingpong') # Shorter pingpong, lower confidence later

        # Dragon (e.g., BBBBB..., PPPPP... - at least 4 consecutive)
        if len(seq) >= 4:
            if seq.endswith('BBBB'): patterns.append('Dragon')
            if seq.endswith('PPPP'): patterns.append('Dragon')
        
        # Two-Cut (e.g., BBPP or PPBB - at least 2 pairs)
        if len(seq) >= 4:
            if seq.endswith('BBPP'): patterns.append('Two-Cut')
            if seq.endswith('PPBB'): patterns.append('Two-Cut')
        
        # Triple-Cut (e.g., BBBPPP or PPPBBB - at least 3 pairs)
        if len(seq) >= 6:
            if seq.endswith('BBBPPP'): patterns.append('Triple-Cut')
            if seq.endswith('PPPBBB'): patterns.append('Triple-Cut')

        # One-Two Pattern (e.g., P BB P BB or B PP B PP) - looks for alternating singles and doubles
        if len(seq) >= 5:
            if seq.endswith('PBBBB') or seq.endswith('BPBBB'): patterns.append('One-Two Pattern') # P-BB-P-BB
            if seq.endswith('BPPPP') or seq.endswith('PBPPH'): patterns.append('Two-One Pattern') # B-PP-B-PP

        # Broken Pattern (e.g., PPPPBB, BBPPBB) - indicates disruption in streak/pattern
        if len(seq) >= 4:
            if 'PPPB' in seq or 'BBBP' in seq: # A streak abruptly broken
                patterns.append('Broken Pattern')
        
        # FollowStreak (Simple continuation, often implies trend following)
        if len(seq) >= 3 and (seq[-1] == seq[-2] == seq[-3]):
            patterns.append('FollowStreak') # e.g. BBB, PPP
        
        return list(set(patterns)) # Return unique patterns

    # --- 2. 🚀 Momentum Tracker ---
    def detect_momentum(self, history):
        """
        Detects momentum in the history.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            list: List of detected momentum names.
        """
        momentum = []
        if len(history) < 3: # Need at least 3 for basic momentum
            return momentum

        # Exclude Ties for streak calculation
        relevant_history = [item['main_outcome'] for item in history if item['main_outcome'] != 'T']
        if len(relevant_history) < 3:
            return momentum

        last_outcome = relevant_history[-1]
        streak = 1
        for i in range(len(relevant_history)-2, -1, -1):
            if relevant_history[i] == last_outcome:
                streak += 1
            else:
                break
        
        # B3+ Momentum / P3+ Momentum (any streak >= 3)
        if streak >= 3:
            momentum.append(f"{last_outcome}{streak}+ Momentum")

        # Steady Repeat Momentum (e.g., PBPBPBP -> expect P)
        # This requires more advanced pattern recognition, not just streak
        # For a simplified linear check, if recent sequence is alternating and long, it's steady
        if len(relevant_history) >= 6:
            recent_seq = ''.join(relevant_history[-6:])
            if recent_seq == 'PBPBPB' or recent_seq == 'BPBPBP':
                momentum.append('Steady Repeat Momentum')

        # Ladder Momentum (1-2-3) e.g., P, PP, PPP
        # This is very complex to detect linearly without Big Road logic (columns)
        # We will skip direct linear detection for now, as it's unreliable without board view.
        # If implemented, it would check for increasing lengths of streaks/groups.

        return list(set(momentum)) # Return unique momentum indicators

    # --- 3. ⚠️ Trap Zone Detection ---
    def detect_trap_zone(self, history):
        """
        Detects unstable or risky patterns that indicate a trap zone.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            str or None: Name of the trap zone if detected, otherwise None.
        """
        self.trap_zone_active = False
        if len(history) < 3: # Need at least 3 hands for trap
            return None
        
        seq = ''.join([item['main_outcome'] for item in history[-3:] if item['main_outcome'] != 'T']) # Look at last 3 non-tie outcomes

        # P1-B1 or B1-P1 (highly unstable, alternating singles)
        if seq == 'PBP' or seq == 'BPPB' : # More robust detection for P1-B1
            self.trap_zone_active = True
            return 'P1-B1 Trap (Unstable)'
        
        # B3-P1 or P3-B1 (strong streak suddenly broken, high risk of reversal)
        if len(history) >= 4:
            recent_outcomes = [item['main_outcome'] for item in history[-4:] if item['main_outcome'] != 'T']
            if len(recent_outcomes) >= 4:
                if recent_outcomes == ['B', 'B', 'B', 'P']:
                    self.trap_zone_active = True
                    return 'B3-P1 Trap (Reversal Risk)'
                if recent_outcomes == ['P', 'P', 'P', 'B']:
                    self.trap_zone_active = True
                    return 'P3-B1 Trap (Reversal Risk)'
        
        # Pingpong Breaking (e.g., PBPBPB -> then P or B, breaking the pingpong)
        if len(history) >= 7:
            recent_seq_full = ''.join([item['main_outcome'] for item in history[-7:] if item['main_outcome'] != 'T'])
            if len(recent_seq_full) >= 7:
                # Check for a pingpong that just ended
                if (recent_seq_full[:-1] == 'PBPBPB' and recent_seq_full[-1] == 'B') or \
                   (recent_seq_full[:-1] == 'BPBPBP' and recent_seq_full[-1] == 'P'):
                    self.trap_zone_active = True
                    return 'Pingpong Breaking Trap'

        return None

    # --- 4. 🎯 Confidence Engine ---
    def calculate_confidence(self, detected_patterns, detected_momentum, intuition_applied=False):
        """
        Calculates a confidence score based on detected patterns, momentum, and trap zone.
        Uses actual success rates of detected indicators.
        Args:
            detected_patterns (list): List of detected patterns.
            detected_momentum (list): List of detected momentum.
            intuition_applied (bool): True if intuition logic was used for prediction.
        Returns:
            int: Confidence score (0-100).
        """
        total_weighted_score = 0
        total_weight_sum = 0

        # Patterns contribute to confidence
        for p in detected_patterns:
            if p in self.pattern_weights:
                weighted_rate = self.get_weighted_success_rate(self.pattern_performance, p, self.pattern_weights[p])
                total_weighted_score += weighted_rate
                total_weight_sum += self.pattern_weights[p]
        
        # Momentum contributes to confidence
        for m in detected_momentum:
            if m in self.momentum_weights:
                weighted_rate = self.get_weighted_success_rate(self.momentum_performance, m, self.momentum_weights[m])
                total_weighted_score += weighted_rate
                total_weight_sum += self.momentum_weights[m]

        # Intuition logic reduces confidence slightly if it was the primary predictor
        if intuition_applied:
            # Assign a lower "weight" to intuition itself, or apply a penalty
            # For simplicity, we can apply a flat penalty if intuition was the primary driver
            total_weighted_score *= 0.8 # Reduce score if intuition was the sole driver
            total_weight_sum = max(1, total_weight_sum) # Ensure no division by zero

        confidence_base = (total_weighted_score / total_weight_sum) if total_weight_sum > 0 else 0.5
        
        # Apply Trap Zone penalty
        if self.trap_zone_active:
            confidence_base *= 0.5 # Halve confidence if in a trap zone

        return round(confidence_base * 100)

    # --- 5. 🔁 Memory Logic ---
    def apply_memory_logic(self, detected_patterns, detected_momentum, predicted_outcome):
        """
        Checks if the current prediction should be blocked based on past failures
        of the active patterns/momentum in this 'room'.
        Args:
            detected_patterns (list): Patterns identified for the current prediction.
            detected_momentum (list): Momentum identified for the current prediction.
            predicted_outcome (str): The outcome that was initially predicted.
        Returns:
            bool: True if the prediction should be blocked, False otherwise.
        """
        active_indicators = detected_patterns + detected_momentum
        
        for indicator in active_indicators:
            # If this indicator has failed at least MEMORY_BLOCK_THRESHOLD times
            # and was part of the previous incorrect prediction
            if self.memory_blocked_patterns.get(indicator, 0) >= self.MEMORY_BLOCK_THRESHOLD:
                # This is a simplified memory logic. A more advanced one would
                # check if this specific indicator, when predicting 'X', failed 'Y' times.
                # For now, if any contributing indicator is blocked, we block the prediction.
                return True
        return False

    # --- 6. 🧠 Intuition Logic ---
    def apply_intuition_logic(self, history):
        """
        Applies advanced intuition logic when no clear patterns are found.
        Args:
            history (list): List of dicts, each with 'main_outcome'.
        Returns:
            str or None: Predicted outcome (P, B) if intuition applies, otherwise None.
        """
        if len(history) < 3: # Need at least 3 for intuition
            return None
        
        seq = ''.join([item['main_outcome'] for item in history[-5:] if item['main_outcome'] != 'T']) # Last 5 non-tie outcomes

        if len(seq) < 3: return None

        # PBP -> P (Double Confirmed)
        if seq.endswith('PBP') and len(seq) >= 3:
            return {'prediction': 'P', 'reason': 'PBP -> P'}
        # BBPBB -> B (Reverse Trap) - indicates a strong trend overcoming a single anomaly
        if seq.endswith('BBPBB') and len(seq) >= 5:
            return {'prediction': 'B', 'reason': 'BBPBB -> B'}
        # PPBPP -> P (Zone Flow) - similar to BBPBB but for P
        if seq.endswith('PPBPP') and len(seq) >= 5:
            return {'prediction': 'P', 'reason': 'PPBPP -> P'}

        # Steady Outcome Guess: If the last few outcomes are mostly one type, and it's not a strong streak
        # For instance, in the last 5 non-tie outcomes, if 4 are P and 1 is B, guess P.
        if len(seq) >= 5:
            p_count = seq.count('P')
            b_count = seq.count('B')
            if p_count >= 4 and b_count <= 1:
                return {'prediction': 'P', 'reason': 'Steady Outcome Guess (P)'}
            if b_count >= 4 and p_count <= 1:
                return {'prediction': 'B', 'reason': 'Steady Outcome Guess (B)'}

        return None

    # --- 7. 🔬 Backtest Simulation ---
    def _run_backtest_simulation(self, full_history):
        """
        Performs a backtest simulation on the history from hand #11 onwards.
        This re-runs predictions and updates learning for the backtest period
        to calculate accuracy and drawdown.
        Args:
            full_history (list): The complete history of outcomes.
        Returns:
            tuple: (accuracy_percentage, hit_count, miss_count, max_drawdown_alert)
        """
        if len(full_history) < 20: # Need at least 20 hands for meaningful backtest (10 for base, then 10 for backtest)
            return "N/A", 0, 0, False

        # Create a temporary, clean engine for backtesting
        temp_engine = OracleEngine()
        hit_count = 0
        miss_count = 0
        current_drawdown = 0
        max_drawdown_alert = False # True if drawdown >= 3 misses

        # Populate initial 10 hands for BASE
        for i in range(10):
            temp_engine.update_learning_state_for_backtest(full_history[i]['main_outcome'], None) # No prediction made yet

        # Start backtesting from hand #11 (index 10)
        for i in range(10, len(full_history)):
            history_for_prediction = full_history[:i] # History up to the hand BEFORE the current one
            actual_outcome = full_history[i]['main_outcome']

            # Make a prediction with the temp_engine based on available history
            prediction_result = temp_engine.predict_next(history_for_prediction, is_backtest=True)
            predicted_outcome = prediction_result['prediction']

            # Update learning state of the temp_engine for the actual outcome of this hand
            temp_engine.update_learning_state_for_backtest(actual_outcome, predicted_outcome, prediction_result.get('patterns', []), prediction_result.get('momentum', []), prediction_result.get('intuition_applied', False))

            # Compare prediction with actual outcome for backtest metrics
            if predicted_outcome != '?' and predicted_outcome != '⚠️' and actual_outcome != 'T': # Only count if a valid prediction was made and not a Tie
                if predicted_outcome == actual_outcome:
                    hit_count += 1
                    current_drawdown = 0 # Reset drawdown on a hit
                else:
                    miss_count += 1
                    current_drawdown += 1
                    if current_drawdown >= 3: # Alert if 3 or more consecutive misses
                        max_drawdown_alert = True
            
            # Reset temp_engine's last_prediction_context for the next iteration
            temp_engine.last_prediction_context = {
                'prediction': predicted_outcome,
                'patterns': prediction_result.get('patterns', []),
                'momentum': prediction_result.get('momentum', []),
                'intuition_applied': prediction_result.get('intuition_applied', False),
                'predicted_by': prediction_result.get('predicted_by', None)
            }


        total_predictions = hit_count + miss_count
        accuracy = (hit_count / total_predictions * 100) if total_predictions > 0 else 0.0

        return f"{accuracy:.1f}% ({hit_count}/{total_predictions})", hit_count, miss_count, max_drawdown_alert


    # --- Main Prediction Logic ---
    def predict_next(self, history, is_backtest=False):
        """
        Analyzes the given history and predicts the next outcome.
        Args:
            history (list): The complete history of outcomes up to the current point.
            is_backtest (bool): Flag to indicate if this call is part of a backtest simulation.
        Returns:
            dict: Contains prediction, recommendation, risk, developer_view, accuracy.
        """
        # Ensure enough data for meaningful analysis
        if len(history) < 20: # Requires at least 20 hands for full analysis and backtest
            return {
                'prediction': '?',
                'recommendation': 'Avoid ❌',
                'risk': 'Not enough data',
                'developer_view': 'Not enough data for full analysis. Requires at least 20 hands.',
                'accuracy': 'N/A'
            }
        
        # --- 1. DNA Pattern Analysis ---
        patterns = self.detect_dna_patterns(history)
        
        # --- 2. Momentum Tracker ---
        momentum = self.detect_momentum(history)

        # --- 3. Trap Zone Detection ---
        trap_zone_name = self.detect_trap_zone(history)
        self.trap_zone_active = (trap_zone_name is not None)

        # --- 4. 🎯 Confidence Engine ---
        # Calculate confidence based on currently detected patterns and momentum
        confidence = self.calculate_confidence(patterns, momentum)

        prediction = '?'
        recommendation = 'Avoid ❌'
        risk = 'Normal'
        predicted_by_logic = "None"
        intuition_applied_flag = False

        # --- Prediction Decision Flow ---
        if self.trap_zone_active:
            prediction = '⚠️' # No prediction, avoid
            recommendation = 'Avoid ❌'
            risk = f"Trap Zone: {trap_zone_name}"
            predicted_by_logic = "Trap Zone"
        elif confidence < 60: # If confidence is too low, avoid
            prediction = '⚠️'
            recommendation = 'Avoid ❌'
            risk = 'Low Confidence'
            predicted_by_logic = "Low Confidence"
        else:
            # Try to predict based on strong patterns/momentum
            last_outcome = history[-1]['main_outcome']
            
            # Prioritize Dragon/FollowStreak
            if 'Dragon' in patterns:
                prediction = last_outcome
                predicted_by_logic = "Dragon"
            elif 'FollowStreak' in patterns:
                prediction = last_outcome
                predicted_by_logic = "FollowStreak"
            elif 'Pingpong' in patterns:
                prediction = 'B' if last_outcome == 'P' else 'P'
                predicted_by_logic = "Pingpong"
            elif 'Two-Cut' in patterns: # Two-Cut (e.g., BBPP) predicts continuation of the pair
                # If last two were BB (from BBPP), predict P. If last two were PP (from PPBB), predict B.
                # This needs careful sequence analysis, assuming the current detection focuses on ending.
                # Simplified: if last two were same and part of two-cut, predict opposite of current outcome for next pair
                if len(history) >= 2 and history[-1]['main_outcome'] == history[-2]['main_outcome']:
                    prediction = 'B' if history[-1]['main_outcome'] == 'P' else 'P' # Predict for the next pair
                else:
                    prediction = last_outcome # Fallback
                predicted_by_logic = "Two-Cut"
            
            # --- 5. 🔁 Memory Logic ---
            # If a prediction was made, check against memory
            if prediction != '?' and prediction != '⚠️':
                if self.apply_memory_logic(patterns, momentum, prediction):
                    prediction = '⚠️' # Blocked by memory logic
                    risk = 'Memory Blocked'
                    recommendation = 'Avoid ❌'
                    predicted_by_logic = "Memory Logic Block"
            
            # --- 6. 🧠 Intuition Logic ---
            # If still no prediction or blocked by memory, try intuition
            if prediction == '?' or predicted_by_logic == "Memory Logic Block":
                intuition_result = self.apply_intuition_logic(history)
                if intuition_result:
                    prediction = intuition_result['prediction']
                    intuition_applied_flag = True
                    predicted_by_logic = f"Intuition ({intuition_result['reason']})"
                    # Confidence might need to be adjusted down for intuition, but not too low
                    confidence = min(confidence, 80) # Cap intuition confidence if it was high

            # Fallback to random if all else fails (should be rare if intuition is good)
            if prediction == '?':
                prediction = random.choice(['P', 'B']) # Simplified random for B or P
                predicted_by_logic = "Random Fallback"
                risk = "Low Confidence / Random"
                recommendation = "Avoid ❌"

            # Final check recommendation based on prediction and risk
            if prediction not in ['?', '⚠️']:
                if 'Memory Blocked' in risk or 'Low Confidence' in risk: # Only avoid if explicitly risky
                    recommendation = 'Avoid ❌'
                elif 'Drawdown Alert' in risk:
                    recommendation = 'Avoid ❌'
                else:
                    recommendation = 'Play ✅'
            else:
                recommendation = 'Avoid ❌' # If prediction is '?' or '⚠️', always avoid


        # --- Store context for next learning step ---
        # This is for the main app loop, not backtest.
        # Backtest uses its own update_learning_state_for_backtest
        if not is_backtest:
            self.last_prediction_context = {
                'prediction': prediction,
                'patterns': patterns,
                'momentum': momentum,
                'intuition_applied': intuition_applied_flag,
                'predicted_by': predicted_by_logic
            }

        # --- 7. 🔬 Backtest Simulation (run once per full prediction cycle) ---
        accuracy_str, hit_count, miss_count, drawdown_alert = self._run_backtest_simulation(history)
        if drawdown_alert:
            risk = "Drawdown Alert" # Override risk if drawdown is severe
            recommendation = "Avoid ❌"

        # --- Developer View ---
        # Construct developer view string
        dev_view_patterns = ', '.join(patterns) if patterns else 'None'
        dev_view_momentum = ', '.join(momentum) if momentum else 'None'
        dev_view_trap = trap_zone_name if trap_zone_name else 'None'

        developer_view_str = (
            f"Current History: {''.join([item['main_outcome'] for item in history[-10:]])}; "
            f"DNA Patterns: {dev_view_patterns}; "
            f"Momentum: {dev_view_momentum}; "
            f"Trap Zone: {dev_view_trap}; "
            f"Confidence: {confidence}%; "
            f"Predicted by: {predicted_by_logic}; "
            f"Backtest Accuracy: {accuracy_str}"
        )

        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'developer_view': developer_view_str,
            'accuracy': accuracy_str
        }

    def update_learning_state(self, actual_outcome):
        """
        Updates the engine's learning states based on the actual outcome of the previous hand.
        This method is called by the Streamlit app after each result is added.
        Args:
            actual_outcome (str): The actual outcome of the hand (P, B, or T).
        """
        predicted_outcome = self.last_prediction_context['prediction']
        patterns_detected = self.last_prediction_context['patterns']
        momentum_detected = self.last_prediction_context['momentum']
        intuition_applied = self.last_prediction_context['intuition_applied']
        predicted_by = self.last_prediction_context['predicted_by']

        # Only update learning if a valid prediction was made (not '?' or '⚠️')
        if predicted_outcome not in ['?', '⚠️']:
            if actual_outcome == predicted_outcome:
                # Prediction was correct
                for p in patterns_detected:
                    if p in self.pattern_performance:
                        self.pattern_performance[p]['success'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance:
                        self.momentum_performance[m]['success'] += 1
                if intuition_applied and predicted_by and "Intuition" in predicted_by:
                    key = predicted_by.replace("Intuition (", "").replace(")", "")
                    if key in self.intuition_performance:
                        self.intuition_performance[key]['success'] += 1
                    else: # Handle new intuition reasons
                        self.intuition_performance[key] = {'success': 1, 'fail': 0}

                # If successful, remove from memory blocked (decay)
                for indicator in patterns_detected + momentum_detected:
                    if indicator in self.memory_blocked_patterns:
                        self.memory_blocked_patterns[indicator] = max(0, self.memory_blocked_patterns[indicator] - 1) # Decay
            else:
                # Prediction was incorrect
                for p in patterns_detected:
                    if p in self.pattern_performance:
                        self.pattern_performance[p]['fail'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance:
                        self.momentum_performance[m]['fail'] += 1
                if intuition_applied and predicted_by and "Intuition" in predicted_by:
                    key = predicted_by.replace("Intuition (", "").replace(")", "")
                    if key in self.intuition_performance:
                        self.intuition_performance[key]['fail'] += 1
                    else: # Handle new intuition reasons
                        self.intuition_performance[key] = {'success': 0, 'fail': 1}
                
                # Add to memory blocked if it failed
                for indicator in patterns_detected + momentum_detected:
                    self.memory_blocked_patterns[indicator] = self.memory_blocked_patterns.get(indicator, 0) + 1

        # Clear context after learning
        self.last_prediction_context = {
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False,
            'predicted_by': None
        }

    def update_learning_state_for_backtest(self, actual_outcome, predicted_outcome_for_backtest, patterns_detected=[], momentum_detected=[], intuition_applied=False):
        """
        Simplified update for backtesting, as it takes prediction and patterns directly.
        Args:
            actual_outcome (str): The actual outcome of the hand.
            predicted_outcome_for_backtest (str): The outcome that was predicted for this hand during backtest.
            patterns_detected (list): Patterns that led to this prediction.
            momentum_detected (list): Momentum that led to this prediction.
            intuition_applied (bool): True if intuition was used.
        """
        if predicted_outcome_for_backtest not in ['?', '⚠️']:
            if actual_outcome == predicted_outcome_for_backtest:
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['success'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['success'] += 1
                if intuition_applied:
                    # Logic for intuition success in backtest needs to be specific to its reason
                    pass # Simplified, not tracking specific intuition reasons in backtest
                for indicator in patterns_detected + momentum_detected:
                    if indicator in self.memory_blocked_patterns:
                        self.memory_blocked_patterns[indicator] = max(0, self.memory_blocked_patterns[indicator] - 1)
            else:
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['fail'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['fail'] += 1
                if intuition_applied:
                    # Logic for intuition fail in backtest
                    pass # Simplified
                for indicator in patterns_detected + momentum_detected:
                    self.memory_blocked_patterns[indicator] = self.memory_blocked_patterns.get(indicator, 0) + 1
