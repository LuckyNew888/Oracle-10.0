import random

class OracleEngine:
    """
    The core prediction engine for ORACLE Baccarat, enhanced with "Final (Advanced Logic)".
    This engine analyzes historical outcomes to detect complex patterns, momentum,
    trap zones (including Trap Timer), bias zones, and applies strategic rules
    like new pattern confirmation and first bet avoidance.
    It uses a stateless approach for history management, relying on the caller
    (e.g., Streamlit app) to provide the full history.
    """
    VERSION = "Final V1.6 (Latest 12)" # System version identifier - Faster detection, single avoid criteria, latest 12 hands

    def __init__(self):
        # Performance tracking for patterns and momentum
        self.pattern_performance = {
            'Pingpong': {'success': 0, 'fail': 0}, 'Dragon': {'success': 0, 'fail': 0},
            'Two-Cut': {'success': 0, 'fail': 0}, 'Triple-Cut': {'success': 0, 'fail': 0},
            'One-Two Pattern': {'success': 0, 'fail': 0}, 'Two-One Pattern': {'success': 0, 'fail': 0},
            'Broken Pattern': {'success': 0, 'fail': 0}, 'FollowStreak': {'success': 0, 'fail': 0},
            'Fake Alternating': {'success': 0, 'fail': 0} 
        }
        self.momentum_performance = {
            'B3+ Momentum': {'success': 0, 'fail': 0}, 'P3+ Momentum': {'success': 0, 'fail': 0},
            'Steady Repeat Momentum': {'success': 0, 'fail': 0},
            'Ladder Momentum (1-2-3)': {'success': 0, 'fail': 0}, 
            'Ladder Momentum (X-Y-XX-Y)': {'success': 0, 'fail': 0} 
        }
        self.intuition_performance = {
            'PBP -> P': {'success': 0, 'fail': 0}, 'BBPBB -> B': {'success': 0, 'fail': 0},
            'PPBPP -> P': {'success': 0, 'fail': 0}, 'Steady Outcome Guess (P)': {'success': 0, 'fail': 0},
            'Steady Outcome Guess (B)': {'success': 0, 'fail': 0}
        }

        # Weights for different analysis modules
        self.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Broken Pattern': 0.6, 'Fake Alternating': 0.5
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6
        }
        
        # Memory Logic (Blacklist Pattern)
        self.memory_blocked_patterns = {}
        self.MEMORY_BLOCK_THRESHOLD = 2 # Block pattern if it failed this many times

        # Trap Timer specific state
        self.hands_to_skip_due_to_trap_timer = 0 # Number of hands to skip
        self.TRAP_TIMER_THRESHOLD = 2 # Skip 2 hands

        # New Pattern Confirmation & First Bet Avoidance state
        self.last_dominant_pattern_id = None 
        self.new_pattern_confirmation_count = 0 
        self.NEW_PATTERN_CONFIRMATION_REQUIRED = 2 # Need 2 confirmations
        self.skip_first_bet_of_new_pattern_flag = False 

        # Bias Zone state
        self.bias_zone_active = False
        self.bias_towards_outcome = None 

        # Context from the last prediction attempt for learning
        self.last_prediction_context = {
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False,
            'predicted_by': None,
            'dominant_pattern_id_at_prediction': None
        }

        self.trap_zone_active = False # General Trap Zone flag
        
        # Performance related caching for Backtest
        self._cached_accuracy_str = "N/A"
        self._cached_hit_count = 0
        self._cached_miss_count = 0
        self._cached_drawdown_alert = False


    def reset_history(self):
        """Resets all learning states and prediction contexts."""
        for perf_dict in [self.pattern_performance, self.momentum_performance, self.intuition_performance]:
            for key in perf_dict:
                perf_dict[key]['success'] = 0
                perf_dict[key]['fail'] = 0
        self.memory_blocked_patterns.clear()
        self.hands_to_skip_due_to_trap_timer = 0
        self.last_dominant_pattern_id = None
        self.new_pattern_confirmation_count = 0
        self.skip_first_bet_of_new_pattern_flag = False
        self.bias_zone_active = False
        self.bias_towards_outcome = None
        self.last_prediction_context = {
            'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
        }
        self.trap_zone_active = False
        self._cached_accuracy_str = "N/A"
        self._cached_hit_count = 0
        self._cached_miss_count = 0
        self._cached_drawdown_alert = False


    def get_success_rate(self, perf_dict, key):
        """Calculates success rate for a given pattern/momentum."""
        stats = perf_dict.get(key, {'success': 0, 'fail': 0})
        total = stats['success'] + stats['fail']
        return stats['success'] / total if total > 0 else 0.5 # Default to 0.5 if no data

    def get_weighted_success_rate(self, perf_dict, key, base_weight):
        """Calculates weighted success rate for confidence calculation."""
        success_rate = self.get_success_rate(perf_dict, key)
        return success_rate * base_weight

    # --- Multi-Pattern Detection (Enhanced DNA Pattern Analysis) ---
    def detect_dna_patterns(self, history):
        """
        Detects common Baccarat patterns in the history, including Multi-Pattern Detection.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            list: List of detected pattern names.
        """
        patterns = []
        # Changed min history from 4 to 3 for faster initial detection
        if len(history) < 3: 
            return patterns

        # Get last 12 outcomes for robust pattern detection, excluding Ties (Changed from 15 to 12)
        seq = ''.join([item['main_outcome'] for item in history[-12:] if item['main_outcome'] != 'T']) 
        # Changed min seq length from 4 to 3
        if len(seq) < 3: return patterns 

        # Dragon (e.g., BBB, PPP - at least 3 consecutive for faster detection)
        if len(seq) >= 3:
            if seq.endswith('BBB'): patterns.append('Dragon')
            if seq.endswith('PPP'): patterns.append('Dragon')
        
        # Pingpong (B-P-B-P - at least 3 alternations for faster detection)
        if len(seq) >= 3 and (seq.endswith('PBP') or seq.endswith('BPB')):
            patterns.append('Pingpong')
        
        # Two-Cut (BB-PP-BB-PP - at least 2 pairs)
        if len(seq) >= 4:
            if seq.endswith('BBPP'): patterns.append('Two-Cut')
            if seq.endswith('PPBB'): patterns.append('Two-Cut')
        
        # Triple-Cut (BBB-PPP or PPP-BBB - at least 3 pairs)
        if len(seq) >= 6:
            if seq.endswith('BBBPPP'): patterns.append('Triple-Cut')
            if seq.endswith('PPPBBB'): patterns.append('Triple-Cut')

        # One-Two Pattern (P-BB-P-BB or B-PP-B-PP) - improved linear detection
        if len(seq) >= 5: 
            if seq[-5:] == 'PBB P': patterns.append('One-Two Pattern') # P-BB-P
            if seq[-5:] == 'BPP B': patterns.append('One-Two Pattern') # B-PP-B

        # Two-One Pattern (PP-B-PP-B or BB-P-BB-P) - improved linear detection
        if len(seq) >= 5: 
            if seq[-5:] == 'PPB PP': patterns.append('Two-One Pattern') # PP-B-PP
            if seq[-5:] == 'BBP BB': patterns.append('Two-One Pattern') # BB-P-BB
        
        # Broken Pattern (e.g., PPPPBB, BBPPBB) - indicates disruption in streak/pattern
        if len(seq) >= 4:
            if 'PPPB' in seq or 'BBBP' in seq:
                patterns.append('Broken Pattern')
        
        # FollowStreak (Simple continuation, often implies trend following)
        if len(seq) >= 3 and (seq[-1] == seq[-2] == seq[-3]):
            patterns.append('FollowStreak')
        
        # Fake Alternating (สลับเทียม) - e.g., P B P B B P (looks like pingpong then breaks)
        if len(seq) >= 5 and (seq[-5:-1] == 'PBPB' or seq[-5:-1] == 'BPBP') and seq[-1] != seq[-3]:
            patterns.append('Fake Alternating')

        return list(set(patterns))

    # --- Momentum Scan (Enhanced Momentum Tracker) ---
    def detect_momentum(self, history):
        """
        Detects momentum in the history.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            list: List of detected momentum names.
        """
        momentum = []
        if len(history) < 3: # Keep 3 as X3+ Momentum needs it
            return momentum

        # Exclude Ties for streak calculation
        relevant_history = [item['main_outcome'] for item in history[-12:] if item['main_outcome'] != 'T'] # Changed from 15 to 12
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

        # Steady Repeat Momentum (e.g., PBPBPB -> expect P) - reduced length for faster detection
        if len(relevant_history) >= 4: # Changed from 6 to 4 for PBPB/BPBP
            recent_seq = ''.join(relevant_history[-4:])
            if recent_seq == 'PBPB' or recent_seq == 'BPBP':
                momentum.append('Steady Repeat Momentum')

        return list(set(momentum))

    # --- Trap Zone Detection (Includes Trap Timer) ---
    def detect_trap_zone(self, history):
        """
        Detects unstable or risky patterns (Trap Zones) and activates Trap Timer.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            str or None: Name of the trap zone if detected, otherwise None.
        """
        self.trap_zone_active = False # Reset general flag
        trap_name = None

        if len(history) < 3:
            return None
        
        # Look at last 6 non-tie outcomes for Trap Timer
        recent_nontie_outcomes = [item['main_outcome'] for item in history[-6:] if item['main_outcome'] != 'T']
        
        # Trap Timer: If side changes >= 4 times in 6 recent non-tie hands
        if len(recent_nontie_outcomes) >= 6:
            changes = 0
            for i in range(len(recent_nontie_outcomes) - 1):
                if recent_nontie_outcomes[i] != recent_nontie_outcomes[i+1]:
                    changes += 1
            if changes >= 4:
                # Trap Timer now only sets the skip counter, does not force '⚠️' prediction directly
                self.hands_to_skip_due_to_trap_timer = self.TRAP_TIMER_THRESHOLD
                self.trap_zone_active = True
                return 'Trap Timer Activated (Skip 2 bets)'

        # General Trap Zone conditions (P1-B1, B3-P1, Pingpong Breaking) - Still detected for risk string
        seq_last_3_nontie = ''.join(recent_nontie_outcomes[-3:]) if len(recent_nontie_outcomes) >= 3 else ''
        seq_last_4_nontie = ''.join(recent_nontie_outcomes[-4:]) if len(recent_nontie_outcomes) >= 4 else ''
        seq_last_7_nontie = ''.join(recent_nontie_outcomes[-7:]) if len(recent_nontie_outcomes) >= 7 else ''

        # P1-B1 or B1-P1 (highly unstable, alternating singles) - more specific: PBP
        if seq_last_3_nontie == 'PBP': 
            self.trap_zone_active = True
            trap_name = 'P1-B1 Trap (Unstable)'
        # BPPB (B-P-P-B)
        if seq_last_4_nontie == 'BPPB' or seq_last_4_nontie == 'PBBP': # Alternating double
            self.trap_zone_active = True
            trap_name = 'Alternating Double Trap'
        
        # B3-P1 or P3-B1 (strong streak suddenly broken, high risk of reversal)
        if len(seq_last_4_nontie) >= 4:
            if seq_last_4_nontie == 'BBBP':
                self.trap_zone_active = True
                trap_name = 'B3-P1 Trap (Reversal Risk)'
            if seq_last_4_nontie == 'PPPB':
                self.trap_zone_active = True
                trap_name = 'P3-B1 Trap (Reversal Risk)'
        
        # Pingpong Breaking (e.g., PBPBPB -> then P or B, breaking the pingpong)
        if len(seq_last_7_nontie) >= 7:
            if (seq_last_7_nontie[:-1] == 'PBPBPB' and seq_last_7_nontie[-1] == 'B') or \
               (seq_last_7_nontie[:-1] == 'BPBPBP' and seq_last_7_nontie[-1] == 'P'):
                self.trap_zone_active = True
                trap_name = 'Pingpong Breaking Trap'
        
        return trap_name

    # --- Zone Detection (Bias Zone) ---
    def detect_bias_zone(self, history):
        """
        Detects if the room has a strong bias towards Player or Banker.
        Args:
            history (list): List of dicts, each with 'main_outcome' (P, B, or T).
        Returns:
            tuple (bool, str or None): (is_bias_active, bias_towards_outcome)
        """
        self.bias_zone_active = False
        self.bias_towards_outcome = None

        if len(history) < 10: # Need at least 10 hands for meaningful bias
            return False, None
        
        # Look at last 20 non-tie outcomes for bias (This is for overall bias, not affected by 12 recent hands)
        relevant_history = [item['main_outcome'] for item in history[-20:] if item['main_outcome'] != 'T']
        if len(relevant_history) < 10: # If not enough non-tie outcomes
            return False, None
        
        p_count = relevant_history.count('P')
        b_count = relevant_history.count('B')
        total_pb = p_count + b_count

        if total_pb == 0: return False, None

        p_ratio = p_count / total_pb
        b_ratio = b_count / total_pb

        BIAS_THRESHOLD = 0.70 # e.g., if one side is >= 70% of non-ties

        if p_ratio >= BIAS_THRESHOLD:
            self.bias_zone_active = True
            self.bias_towards_outcome = 'P'
        elif b_ratio >= BIAS_THRESHOLD:
            self.bias_zone_active = True
            self.bias_towards_outcome = 'B'
        
        return self.bias_zone_active, self.bias_towards_outcome

    # --- Confidence Threshold (Enhanced Confidence Engine) ---
    def calculate_confidence(self, detected_patterns, detected_momentum, intuition_applied=False, primary_prediction_logic=None, bias_zone_active=False):
        """
        Calculates a confidence score based on detected patterns, momentum, trap zone, and intuition.
        Uses actual success rates of detected indicators.
        Args:
            detected_patterns (list): List of detected patterns.
            detected_momentum (list): List of detected momentum.
            intuition_applied (bool): True if intuition logic was used for prediction.
            primary_prediction_logic (str): The specific pattern/logic that drove the prediction.
            bias_zone_active (bool): True if currently in a bias zone.
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

        # Base confidence calculation
        confidence_base = (total_weighted_score / total_weight_sum) if total_weight_sum > 0 else 0.5 # Default 50% if no relevant patterns/momentum
        
        # Apply Trap Zone penalty (this penalty affects the *base* confidence)
        if self.trap_zone_active:
            confidence_base *= 0.5 # Halve confidence if in a trap zone

        # If intuition logic was the primary driver, adjust confidence
        if intuition_applied and primary_prediction_logic and "Intuition" in primary_prediction_logic:
            intuition_key = primary_prediction_logic.replace("Intuition (", "").replace(")", "")
            intuition_success_rate = self.get_success_rate(self.intuition_performance, intuition_key)
            confidence_base = (confidence_base * 0.7 + intuition_success_rate * 0.3) 
            confidence_base *= 0.8 # Apply a general penalty for relying on intuition solely

        return round(confidence_base * 100)

    # --- Blacklist Pattern (Memory Logic) ---
    def apply_memory_logic(self, detected_patterns, detected_momentum):
        """
        Checks if any active pattern/momentum is in the blacklist due to past failures.
        Args:
            detected_patterns (list): Patterns identified for the current prediction.
            detected_momentum (list): Momentum identified for the current prediction.
        Returns:
            bool: True if any active indicator is blocked, False otherwise.
        """
        active_indicators = detected_patterns + detected_momentum
        for indicator in active_indicators:
            if self.memory_blocked_patterns.get(indicator, 0) >= self.MEMORY_BLOCK_THRESHOLD:
                return True # Indicate that this prediction is affected by memory block
        return False

    # --- Intuition Logic ---
    def apply_intuition_logic(self, history):
        """
        Applies advanced intuition logic when no clear strong patterns are found.
        Args:
            history (list): List of dicts, each with 'main_outcome'.
        Returns:
            dict or None: {'prediction': outcome, 'reason': reason_str} if intuition applies, otherwise None.
        """
        if len(history) < 3:
            return None
        
        seq_nontie = ''.join([item['main_outcome'] for item in history[-5:] if item['main_outcome'] != 'T']) # Last 5 non-tie outcomes
        if len(seq_nontie) < 3: return None

        # PBP -> P (Double Confirmed)
        if seq_nontie.endswith('PBP'):
            return {'prediction': 'P', 'reason': 'PBP -> P'}
        # BBPBB -> B (Reverse Trap) - indicates a strong trend overcoming a single anomaly
        if seq_nontie.endswith('BBPBB'):
            return {'prediction': 'B', 'reason': 'BBPBB -> B'}
        # PPBPP -> P (Zone Flow) - similar to BBPBB but for P
        if seq_nontie.endswith('PPBPP'):
            return {'prediction': 'P', 'reason': 'PPBPP -> P'}

        # Steady Outcome Guess: If the last few outcomes are mostly one type, and it's not a strong streak
        if len(seq_nontie) >= 4: # Look at last 4-5 non-ties
            p_count = seq_nontie.count('P')
            b_count = seq_nontie.count('B')
            
            if p_count >= len(seq_nontie) - 1 and b_count <= 1: # e.g., PPPB -> guess P
                return {'prediction': 'P', 'reason': 'Steady Outcome Guess (P)'}
            if b_count >= len(seq_nontie) - 1 and p_count <= 1: # e.g., BBBP -> guess B
                return {'prediction': 'B', 'reason': 'Steady Outcome Guess (B)'}

        return None

    # --- DNA Backtest Simulation (Now called externally for performance) ---
    def calculate_backtest_metrics(self, full_history):
        """
        Calculates backtest metrics (accuracy, drawdown) *once* when called.
        This method is now separated from predict_next for performance.
        Args:
            full_history (list): The complete history of outcomes.
        Returns:
            tuple: (accuracy_percentage_str, hit_count, miss_count, max_drawdown_alert)
        """
        if len(full_history) < 20:
            return "N/A", 0, 0, False

        # Create a temporary, clean engine for backtesting
        temp_engine = OracleEngine()
        hit_count = 0
        miss_count = 0
        current_drawdown = 0
        max_drawdown_alert = False 

        # Populate initial 10 hands for BASE and learning
        # Note: In backtest, we don't trigger New Pattern confirmation flags, etc.
        # Just pure learning of pattern/momentum performance.
        for i in range(min(10, len(full_history))): # Handle cases where history < 10
            temp_engine.update_learning_state_for_backtest(full_history[i]['main_outcome'], None, [], [], False) 

        # Start backtesting from hand #11 (index 10)
        for i in range(10, len(full_history)):
            history_for_prediction = full_history[:i] 
            actual_outcome = full_history[i]['main_outcome']

            prediction_result = temp_engine.predict_next(history_for_prediction, is_backtest=True)
            predicted_outcome = prediction_result['prediction']

            # Extract info for learning: patterns, momentum, intuition_applied
            # This parsing needs to be robust as developer_view is a string
            dev_view_str = prediction_result['developer_view']
            patterns_match_str = self._extract_dev_view_part(dev_view_str, "DNA Patterns:")
            momentum_match_str = self._extract_dev_view_part(dev_view_str, "Momentum:")
            
            patterns_match = [p.strip() for p in patterns_match_str.split(',') if p.strip() != 'None'] if patterns_match_str else []
            momentum_match = [m.strip() for m in momentum_match_str.split(',') if m.strip() != 'None'] if momentum_match_str else []
            intuition_applied_in_dev = 'Intuition (' in dev_view_str
            
            temp_engine.update_learning_state_for_backtest(actual_outcome, predicted_outcome, patterns_match, momentum_match, intuition_applied_in_dev)

            # Compare prediction with actual outcome for backtest metrics
            if predicted_outcome not in ['?', '⚠️'] and actual_outcome != 'T': 
                if predicted_outcome == actual_outcome:
                    hit_count += 1
                    current_drawdown = 0 
                else:
                    miss_count += 1
                    current_drawdown += 1
                    if current_drawdown >= 3: 
                        max_drawdown_alert = True
            
        total_predictions = hit_count + miss_count
        accuracy = (hit_count / total_predictions * 100) if total_predictions > 0 else 0.0

        return f"{accuracy:.1f}% ({hit_count}/{total_predictions})", hit_count, miss_count, max_drawdown_alert

    def _extract_dev_view_part(self, dev_view_str, label):
        """Helper to extract parts from developer_view string."""
        start_idx = dev_view_str.find(label)
        if start_idx == -1: return ""
        start_idx += len(label)
        end_idx = dev_view_str.find(';', start_idx)
        if end_idx == -1: return dev_view_str[start_idx:].strip()
        return dev_view_str[start_idx:end_idx].strip()

    # --- Final Decision (Main Prediction Logic) ---
    def predict_next(self, history, is_backtest=False):
        """
        Analyzes the given history and predicts the next outcome based on Advanced Logic.
        Args:
            history (list): The complete history of outcomes up to the current point.
            is_backtest (bool): Flag to indicate if this call is part of a backtest simulation.
        Returns:
            dict: Contains prediction, recommendation, risk, developer_view, accuracy, confidence.
        """
        # Core Avoid Condition 1: Not Enough Data
        if len(history) < 20: 
            if not is_backtest: 
                self.last_prediction_context = {'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None}
            return {
                'prediction': '?',
                'recommendation': 'Avoid ❌', 
                'risk': 'Not enough data',
                'developer_view': 'Not enough data for full analysis. Requires at least 20 hands.',
                'accuracy': self._cached_accuracy_str, 
                'confidence': 'N/A'
            }
        
        # --- Dynamic Prediction Adjustment (Re-analyze every time) ---
        patterns = self.detect_dna_patterns(history)
        momentum = self.detect_momentum(history)
        trap_zone_name = self.detect_trap_zone(history) 
        bias_zone_active, bias_towards = self.detect_bias_zone(history)

        current_dominant_pattern_id = "NoClearPattern" 
        if 'Dragon' in patterns: current_dominant_pattern_id = 'Dragon'
        elif 'Pingpong' in patterns: current_dominant_pattern_id = 'Pingpong'
        elif bias_zone_active: current_dominant_pattern_id = f"Bias-{bias_towards}"
        elif len(momentum) > 0 and (('B3+ Momentum' in momentum and history[-1]['main_outcome'] == 'B') or ('P3+ Momentum' in momentum and history[-1]['main_outcome'] == 'P')):
            current_dominant_pattern_id = f"{history[-1]['main_outcome']}Streak" 
        elif len(patterns) > 0: 
            current_dominant_pattern_id = patterns[0] 

        prediction = '?' # Default to unknown, will be set by logic below
        risk = 'Normal' # Default risk, will be updated
        predicted_by_logic = "None"
        intuition_applied_flag = False
        confidence = 0 # Initialize confidence

        # --- High Priority Overrides (Forces Prediction to '⚠️') ---
        # ONLY Low Confidence makes prediction ⚠️ now. Other risks only affect Risk string.
        
        # Core Avoid Condition 2: Confidence Threshold Override (<60%)
        # Calculate confidence first
        confidence = self.calculate_confidence(patterns, momentum, False, None, bias_zone_active)
        if confidence < 60: # Threshold is 60% as per request
             prediction = '⚠️'
             risk = f'Low Confidence (<60%)'
             predicted_by_logic = f"Avoid (Confidence {confidence}%)"


        # --- Core Prediction Logic (Attempt to get P/B, if not already '⚠️') ---
        if prediction == '?': # Only if not already forced to '⚠️' by low confidence
            last_outcome = history[-1]['main_outcome']
            
            # Prioritize strongest patterns/momentum
            if 'Dragon' in patterns:
                prediction = last_outcome
                predicted_by_logic = "Dragon"
            elif 'FollowStreak' in patterns:
                prediction = last_outcome
                predicted_by_logic = "FollowStreak"
            elif 'Pingpong' in patterns:
                prediction = 'B' if last_outcome == 'P' else 'P'
                predicted_by_logic = "Pingpong"
            elif 'Two-Cut' in patterns:
                if len(history) >= 2 and history[-1]['main_outcome'] == history[-2]['main_outcome']:
                    prediction = 'B' if history[-1]['main_outcome'] == 'P' else 'P' 
                else: 
                    prediction = last_outcome
                predicted_by_logic = "Two-Cut"
            elif 'Triple-Cut' in patterns:
                if len(history) >= 3 and history[-1]['main_outcome'] == history[-2]['main_outcome'] == history[-3]['main_outcome']:
                    prediction = 'B' if history[-1]['main_outcome'] == 'P' else 'P' 
                else: 
                    prediction = last_outcome 
                predicted_by_logic = "Triple-Cut"
            elif 'B3+ Momentum' in momentum and last_outcome == 'B':
                prediction = 'B'
                predicted_by_logic = "B3+ Momentum"
            elif 'P3+ Momentum' in momentum and last_outcome == 'P':
                prediction = 'P'
                predicted_by_logic = "P3+ Momentum"
            elif 'Steady Repeat Momentum' in momentum:
                prediction = 'P' if last_outcome == 'B' else 'B' 
                predicted_by_logic = "Steady Repeat Momentum"
            
            # Intuition Logic (If no specific pattern prediction yet)
            if prediction == '?': 
                intuition_result = self.apply_intuition_logic(history)
                if intuition_result:
                    prediction = intuition_result['prediction']
                    intuition_applied_flag = True
                    predicted_by_logic = f"Intuition ({intuition_result['reason']})"
            
            # Final Fallback if still no prediction from patterns/momentum/intuition
            if prediction == '?':
                recent_nontie = [item['main_outcome'] for item in history[-10:] if item['main_outcome'] != 'T']
                if recent_nontie:
                    p_count = recent_nontie.count('P')
                    b_count = recent_nontie.count('B')
                    if p_count > b_count: prediction = 'P'
                    elif b_count > p_count: prediction = 'B'
                    else: prediction = random.choice(['P', 'B']) 
                    predicted_by_logic = "Majority Fallback"
                else:
                    prediction = random.choice(['P', 'B']) 
                    predicted_by_logic = "Random Fallback (No Data)"

        # --- Set Risk Flags based on conditions (applies to P/B/⚠️ predictions) ---
        # These flags are for informative purposes in 'risk' string.
        # They no longer force 'Avoid' recommendation, unless prediction is '⚠️' (only by Low Confidence)

        # Trap Timer (Risk only, no longer forces ⚠️ prediction directly)
        if self.hands_to_skip_due_to_trap_timer > 0:
            risk = f"Trap Timer ({self.hands_to_skip_due_to_trap_timer} skips left)"
            #predicted_by_logic = "Trap Timer Active" # Keep predicted_by_logic from actual prediction
        
        # New Pattern Confirmation & First Bet Avoidance
        if not is_backtest and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"]:
            if self.last_dominant_pattern_id is not None and self.last_dominant_pattern_id != current_dominant_pattern_id:
                self.skip_first_bet_of_new_pattern_flag = True 
                self.new_pattern_confirmation_count = 0 
                
            if self.skip_first_bet_of_new_pattern_flag: 
                if risk == 'Normal': risk = 'New Pattern: First Bet Avoidance'
                else: risk += ', New Pattern: First Bet Avoidance'
            elif self.new_pattern_confirmation_count < self.NEW_PATTERN_CONFIRMATION_REQUIRED:
                if risk == 'Normal': risk = f"New Pattern: Awaiting {self.NEW_PATTERN_CONFIRMATION_REQUIRED - self.new_pattern_confirmation_count} Confirmation(s)"
                else: risk += f", New Pattern: Awaiting {self.NEW_PATTERN_CONFIRMATION_REQUIRED - self.new_pattern_confirmation_count} Confirmation(s)"

        # Trap Zone (General)
        if self.trap_zone_active and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"]:
            if risk == 'Normal': risk = f"Trap Zone: {trap_zone_name}"
            else: risk += f", Trap Zone: {trap_zone_name}"

        # Blacklist Pattern (Memory Logic)
        if self.apply_memory_logic(patterns, momentum) and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"]:
            if risk == 'Normal': risk = 'Memory Blocked'
            else: risk += ', Memory Blocked'

        # Bias Zone (Countering Bias)
        if bias_zone_active and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"]:
            if prediction != bias_towards: # If predicting counter to bias
                if risk == 'Normal': risk = f"Bias Zone (Counter {bias_towards})"
                else: risk += f", Bias Zone (Counter {bias_towards})"
            else: # If predicting with bias
                if risk == 'Normal': risk = f"Bias Zone ({bias_towards} Favored)"
                else: risk += f", Bias Zone ({bias_towards} Favored)"
        
        # Drawdown Alert (from cached backtest results)
        if self._cached_drawdown_alert:
            if risk == 'Normal': risk = "Drawdown Alert"
            else: risk += ", Drawdown Alert"

        # --- Final Recommendation Logic (Based ONLY on prediction type) ---
        recommendation = 'Play ✅' # Default for P/B prediction
        if prediction == '⚠️':
            recommendation = 'Avoid ❌' # Only '⚠️' leads to Avoid recommendation

        # --- Store context for next learning step (only in main app loop) ---
        if not is_backtest:
            self.last_prediction_context = {
                'prediction': prediction, # Store the FINAL prediction (can be P/B/⚠️)
                'patterns': patterns,
                'momentum': momentum,
                'intuition_applied': intuition_applied_flag,
                'predicted_by': predicted_by_logic,
                'dominant_pattern_id_at_prediction': current_dominant_pattern_id 
            }

        # --- Developer View ---
        dev_view_patterns = ', '.join(patterns) if patterns else 'None'
        dev_view_momentum = ', '.join(momentum) if momentum else 'None'
        dev_view_trap = trap_zone_name if trap_zone_name else 'None'
        dev_view_bias = f"Active ({bias_towards})" if bias_zone_active else 'None'
        
        developer_view_str = (
            f"Current History: {''.join([item['main_outcome'] for item in history[-10:]])}; "
            f"DNA Patterns: {dev_view_patterns}; "
            f"Momentum: {dev_view_momentum}; "
            f"Trap Zone: {dev_view_trap}; "
            f"Bias Zone: {dev_view_bias}; "
            f"Confidence: {confidence}%; " 
            f"Predicted by: {predicted_by_logic}; "
            f"Backtest Accuracy: {self._cached_accuracy_str}" 
        )

        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'developer_view': developer_view_str,
            'accuracy': self._cached_accuracy_str, 
            'confidence': confidence 
        }

    def update_learning_state(self, actual_outcome, history_for_backtest_calc=None):
        """
        Updates the engine's learning states based on the actual outcome of the previous hand.
        This method is called by the Streamlit app after each result is added.
        Args:
            actual_outcome (str): The actual outcome of the hand (P, B, or T).
            history_for_backtest_calc (list): The full current history, used for optional backtest calculation.
        """
        predicted_outcome_context = self.last_prediction_context['prediction'] # The prediction the system actually made
        patterns_detected = self.last_prediction_context['patterns']
        momentum_detected = self.last_prediction_context['momentum']
        intuition_applied = self.last_prediction_context['intuition_applied']
        predicted_by = self.last_prediction_context['predicted_by']
        dominant_pattern_at_prediction = self.last_prediction_context['dominant_pattern_id_at_prediction']

        # Handle Trap Timer decrement first
        if self.hands_to_skip_due_to_trap_timer > 0:
            self.hands_to_skip_due_to_trap_timer -= 1
        
        # New pattern confirmation flags should still be managed regardless of Trap Timer.
        # This logic determines if the new pattern count increments or resets.
        # It's not directly related to the prediction outcome but to pattern recognition continuity.
        if dominant_pattern_at_prediction is not None: # Ensure a pattern was identified
            if dominant_pattern_at_prediction == self.last_dominant_pattern_id:
                self.new_pattern_confirmation_count += 1
            else:
                self.new_pattern_confirmation_count = 1 # New dominant pattern, reset count to 1
            self.last_dominant_pattern_id = dominant_pattern_at_prediction # Update for next round
        else: # No clear dominant pattern in this round's context
            self.new_pattern_confirmation_count = 0 # Reset if no dominant pattern
            self.last_dominant_pattern_id = None


        # Clear the skip_first_bet_of_new_pattern_flag after one hand if it was active.
        if self.skip_first_bet_of_new_pattern_flag:
            self.skip_first_bet_of_new_pattern_flag = False 
            # If it was skipped, the new pattern confirmation might have just started
            # We already handled new_pattern_confirmation_count above.

        # Only update learning for success/fail if a valid prediction (P/B) was made
        # and it wasn't due to fundamental data insufficiency or critically low confidence.
        if predicted_outcome_context in ['P', 'B']: # Only learn if the system actually predicted P or B
            if actual_outcome == predicted_outcome_context:
                # Prediction was correct
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['success'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['success'] += 1
                if intuition_applied and predicted_by and "Intuition" in predicted_by:
                    key = predicted_by.replace("Intuition (", "").replace(")", "")
                    if key in self.intuition_performance: self.intuition_performance[key]['success'] += 1
                    else: self.intuition_performance[key] = {'success': 1, 'fail': 0}

                # If successful, reduce memory blocked count for associated indicators (decay)
                for indicator in patterns_detected + momentum_detected:
                    if indicator in self.memory_blocked_patterns:
                        self.memory_blocked_patterns[indicator] = max(0, self.memory_blocked_patterns[indicator] - 1)
            else:
                # Prediction was incorrect
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['fail'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['fail'] += 1
                if intuition_applied and predicted_by and "Intuition" in predicted_by:
                    key = predicted_by.replace("Intuition (", "").replace(")", "")
                    if key in self.intuition_performance: self.intuition_performance[key]['fail'] += 1
                    else: self.intuition_performance[key] = {'success': 0, 'fail': 1}
                
                # Add to memory blocked if it failed
                for indicator in patterns_detected + momentum_detected:
                    self.memory_blocked_patterns[indicator] = self.memory_blocked_patterns.get(indicator, 0) + 1

        # Recalculate Backtest metrics AFTER learning for this hand
        if history_for_backtest_calc and len(history_for_backtest_calc) >= 20:
            self._cached_accuracy_str, self._cached_hit_count, self._cached_miss_count, self._cached_drawdown_alert = \
                self.calculate_backtest_metrics(history_for_backtest_calc)
        
        # Clear context after learning, this context applies to the prediction *just made*
        self.last_prediction_context = {
            'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
        }

    def update_learning_state_for_backtest(self, actual_outcome, predicted_outcome_for_backtest, patterns_detected, momentum_detected, intuition_applied):
        """
        Simplified update for backtesting.
        """
        if predicted_outcome_for_backtest in ['P', 'B']: # Only learn if the simulated prediction was P or B
            if actual_outcome == predicted_outcome_for_backtest:
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['success'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['success'] += 1
                if intuition_applied:
                    pass 
                for indicator in patterns_detected + momentum_detected:
                    if indicator in self.memory_blocked_patterns:
                        self.memory_blocked_patterns[indicator] = max(0, self.memory_blocked_patterns[indicator] - 1)
            else:
                for p in patterns_detected:
                    if p in self.pattern_performance: self.pattern_performance[p]['fail'] += 1
                for m in momentum_detected:
                    if m in self.momentum_performance: self.momentum_performance[m]['fail'] += 1
                if intuition_applied:
                    pass
                for indicator in patterns_detected + momentum_detected:
                    self.memory_blocked_patterns[indicator] = self.memory_blocked_patterns.get(indicator, 0) + 1
