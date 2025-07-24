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
    VERSION = "Final V1.0 (Hotfix)" # System version identifier - Updated

    def __init__(self):
        # Performance tracking for patterns and momentum
        # { 'pattern_name': {'success': count, 'fail': count} }
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
        if len(history) < 4:
            return patterns

        # Get last 15 outcomes for robust pattern detection, excluding Ties
        seq = ''.join([item['main_outcome'] for item in history[-15:] if item['main_outcome'] != 'T']) 
        if len(seq) < 4: return patterns # Need enough non-tie outcomes

        # Dragon (e.g., BBBBB..., PPPPP... - at least 4 consecutive)
        if len(seq) >= 4:
            if seq.endswith('BBBB'): patterns.append('Dragon')
            if seq.endswith('PPPP'): patterns.append('Dragon')
        
        # Pingpong (B-P-B-P - at least 3 alternations)
        if len(seq) >= 6 and (seq.endswith('PBPBPB') or seq.endswith('BPBPBP')):
            patterns.append('Pingpong')
        elif len(seq) >= 4 and (seq.endswith('PBPB') or seq.endswith('BPBP')):
            patterns.append('Pingpong')

        # Two-Cut (BB-PP-BB-PP - at least 2 pairs)
        if len(seq) >= 4:
            if seq.endswith('BBPP'): patterns.append('Two-Cut')
            if seq.endswith('PPBB'): patterns.append('Two-Cut')
        
        # Triple-Cut (BBB-PPP or PPP-BBB - at least 3 pairs)
        if len(seq) >= 6:
            if seq.endswith('BBBPPP'): patterns.append('Triple-Cut')
            if seq.endswith('PPPBBB'): patterns.append('Triple-Cut')

        # One-Two Pattern (P-BB-P-BB or B-PP-B-PP) - simplified linear detection
        # Re-check logic for better detection
        if len(seq) >= 5: 
            if seq.endswith('PBB') and len(seq) >= 5 and seq[-5] == 'P' and seq[-4] == seq[-3] == 'B': patterns.append('One-Two Pattern') # P-BB-P
            if seq.endswith('BPP') and len(seq) >= 5 and seq[-5] == 'B' and seq[-4] == seq[-3] == 'P': patterns.append('One-Two Pattern') # B-PP-B

        # Two-One Pattern (PP-B-PP-B or BB-P-BB-P) - simplified linear detection
        # Re-check logic for better detection
        if len(seq) >= 5: 
            if seq.endswith('BPP') and len(seq) >= 5 and seq[-5:-3] == 'PP' and seq[-2] == 'B': patterns.append('Two-One Pattern') # PP-B-P
            if seq.endswith('PBB') and len(seq) >= 5 and seq[-5:-3] == 'BB' and seq[-2] == 'P': patterns.append('Two-One Pattern') # BB-P-B
        
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
        if len(history) < 3:
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
        if len(relevant_history) >= 6:
            recent_seq = ''.join(relevant_history[-6:])
            if recent_seq == 'PBPBPB' or recent_seq == 'BPBPBP':
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
                self.hands_to_skip_due_to_trap_timer = self.TRAP_TIMER_THRESHOLD
                self.trap_zone_active = True
                return 'Trap Timer Activated (Skip 2 bets)'

        # General Trap Zone conditions (P1-B1, B3-P1, Pingpong Breaking)
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
        
        # Look at last 20 non-tie outcomes for bias
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

        # Apply Trap Zone penalty
        if self.trap_zone_active:
            confidence_base *= 0.5 # Halve confidence if in a trap zone

        # If intuition logic was the primary driver, adjust confidence
        if intuition_applied and primary_prediction_logic and "Intuition" in primary_prediction_logic:
            # Get success rate of that specific intuition rule
            intuition_key = primary_prediction_logic.replace("Intuition (", "").replace(")", "")
            intuition_success_rate = self.get_success_rate(self.intuition_performance, intuition_key)
            # Mix intuition's success with current pattern/momentum confidence, but with lower overall weight for intuition
            confidence_base = (confidence_base * 0.7 + intuition_success_rate * 0.3) # 70% from pattern/momentum, 30% from intuition
            confidence_base *= 0.8 # Apply a general penalty for relying on intuition solely

        # If in a Bias Zone, and prediction aligns with bias, slightly boost confidence (or just avoid penalty)
        # If prediction counters bias, confidence should be lower, but this is handled by risk/recommendation
        # For confidence calculation, we mainly apply penalties.

        return round(confidence_base * 100)

    # --- Blacklist Pattern (Memory Logic) ---
    def apply_memory_logic(self, detected_patterns, detected_momentum, prediction_candidate_outcome):
        """
        Checks if the current prediction should be blocked based on past failures
        of the active patterns/momentum in this 'room' (Blacklist).
        Args:
            detected_patterns (list): Patterns identified for the current prediction.
            detected_momentum (list): Momentum identified for the current prediction.
            prediction_candidate_outcome (str): The outcome being considered for prediction.
        Returns:
            bool: True if the prediction should be blocked, False otherwise.
        """
        active_indicators = detected_patterns + detected_momentum
        
        for indicator in active_indicators:
            # If this indicator has failed at least MEMORY_BLOCK_THRESHOLD times
            # and the predicted outcome is the same as the outcome that failed before
            # This would require storing (indicator, failed_outcome) in memory_blocked_patterns
            # For simplicity, if the indicator itself is blocked, we block.
            if self.memory_blocked_patterns.get(indicator, 0) >= self.MEMORY_BLOCK_THRESHOLD:
                # We can make this more specific: block only if this pattern led to a fail for THIS prediction candidate
                # (e.g., if "Dragon" failed when predicting 'B', don't block Dragon when predicting 'P')
                # For now, a general block on the pattern is applied.
                return True
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

    # --- DNA Backtest Simulation ---
    def _run_backtest_simulation(self, full_history):
        """
        Performs a backtest simulation on the history from hand #11 onwards.
        This re-runs predictions and updates learning for the backtest period
        to calculate accuracy and drawdown.
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
        max_drawdown_alert = False # True if drawdown >= 3 misses

        # Populate initial 10 hands for BASE and learning
        for i in range(10):
            # No prediction yet for initial hands, just update learning to build stats
            temp_engine.update_learning_state_for_backtest(full_history[i]['main_outcome'], None, [], [], False) 

        # Start backtesting from hand #11 (index 10)
        for i in range(10, len(full_history)):
            history_for_prediction = full_history[:i] # History up to the hand BEFORE the current one
            actual_outcome = full_history[i]['main_outcome']

            # Make a prediction with the temp_engine based on available history
            prediction_result = temp_engine.predict_next(history_for_prediction, is_backtest=True)
            predicted_outcome = prediction_result['prediction']

            # Extract info from developer_view string to update learning for backtest
            # This parsing is brittle; ideally, predict_next would return a structured dict for learning.
            dev_view_str = prediction_result['developer_view']
            patterns_in_dev = []
            momentum_in_dev = []
            intuition_applied_in_dev = False

            patterns_match = [p.strip() for p in dev_view_str.split('DNA Patterns: ')[1].split(';')[0].split(',') if p.strip() != 'None'] if 'DNA Patterns: ' in dev_view_str else []
            momentum_match = [m.strip() for m in dev_view_str.split('Momentum: ')[1].split(';')[0].split(',') if m.strip() != 'None'] if 'Momentum: ' in dev_view_str else []
            if 'Intuition' in dev_view_str:
                intuition_applied_in_dev = True
            
            # Update learning state of the temp_engine for the actual outcome of this hand
            temp_engine.update_learning_state_for_backtest(actual_outcome, predicted_outcome, patterns_match, momentum_match, intuition_applied_in_dev)

            # Compare prediction with actual outcome for backtest metrics
            if predicted_outcome not in ['?', '⚠️'] and actual_outcome != 'T': # Only count if a valid prediction was made and not a Tie
                if predicted_outcome == actual_outcome:
                    hit_count += 1
                    current_drawdown = 0 # Reset drawdown on a hit
                else:
                    miss_count += 1
                    current_drawdown += 1
                    if current_drawdown >= 3: # Alert if 3 or more consecutive misses
                        max_drawdown_alert = True
            
        total_predictions = hit_count + miss_count
        accuracy = (hit_count / total_predictions * 100) if total_predictions > 0 else 0.0

        return f"{accuracy:.1f}% ({hit_count}/{total_predictions})", hit_count, miss_count, max_drawdown_alert

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
        # Ensure enough data for meaningful analysis
        if len(history) < 20: 
            if not is_backtest: 
                self.last_prediction_context = {'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None}
            return {
                'prediction': '?',
                'recommendation': 'Avoid ❌',
                'risk': 'Not enough data',
                'developer_view': 'Not enough data for full analysis. Requires at least 20 hands.',
                'accuracy': 'N/A',
                'confidence': 'N/A'
            }
        
        # --- Dynamic Prediction Adjustment (Re-analyze every time) ---
        # Recalculate all states based on the current history
        patterns = self.detect_dna_patterns(history)
        momentum = self.detect_momentum(history)
        trap_zone_name = self.detect_trap_zone(history) 
        bias_zone_active, bias_towards = self.detect_bias_zone(history)

        # Identify a 'dominant' pattern or state for New Pattern Confirmation
        current_dominant_pattern_id = "NoClearPattern" 
        if 'Dragon' in patterns: current_dominant_pattern_id = 'Dragon'
        elif 'Pingpong' in patterns: current_dominant_pattern_id = 'Pingpong'
        elif bias_zone_active: current_dominant_pattern_id = f"Bias-{bias_towards}"
        elif len(momentum) > 0 and (('B3+ Momentum' in momentum and history[-1]['main_outcome'] == 'B') or ('P3+ Momentum' in momentum and history[-1]['main_outcome'] == 'P')):
            current_dominant_pattern_id = f"{history[-1]['main_outcome']}Streak" 
        elif len(patterns) > 0: 
            current_dominant_pattern_id = patterns[0] 

        # Initialize prediction variables for this round
        prediction = '?'
        recommendation = 'Avoid ❌'
        risk = 'Normal'
        predicted_by_logic = "None"
        intuition_applied_flag = False
        confidence = 0 # Initialize confidence as 0

        # --- Priority Decision Flow ---

        # 1. Trap Timer Override
        if self.hands_to_skip_due_to_trap_timer > 0:
            prediction = '⚠️'
            recommendation = 'Avoid ❌'
            risk = f"Trap Timer ({self.hands_to_skip_due_to_trap_timer} skips left)"
            predicted_by_logic = "Trap Timer Active"
        
        # 2. New Pattern Confirmation & First Bet Avoidance
        elif not is_backtest: # Only apply in main app mode, not backtest
            # If dominant pattern changed from last round, reset confirmation and set skip flag
            if self.last_dominant_pattern_id is not None and self.last_dominant_pattern_id != current_dominant_pattern_id:
                self.skip_first_bet_of_new_pattern_flag = True 
                self.new_pattern_confirmation_count = 0 
                
            if self.skip_first_bet_of_new_pattern_flag: # If this is the hand where we skip the first bet of new pattern
                prediction = '⚠️'
                recommendation = 'Avoid ❌'
                risk = 'New Pattern: First Bet Avoidance'
                predicted_by_logic = "New Pattern - First Bet Avoidance"
            elif self.new_pattern_confirmation_count < self.NEW_PATTERN_CONFIRMATION_REQUIRED:
                prediction = '⚠️'
                recommendation = 'Avoid ❌'
                risk = f"New Pattern: Awaiting {self.NEW_PATTERN_CONFIRMATION_REQUIRED - self.new_pattern_confirmation_count} Confirmation(s)"
                predicted_by_logic = "New Pattern - Awaiting Confirmation"
        
        # 3. Trap Zone (General) Override (if not already skipped by Timer/New Pattern)
        if prediction == '?' and self.trap_zone_active: # Only if prediction is still undecided
            prediction = '⚠️'
            recommendation = 'Avoid ❌'
            risk = f"Trap Zone: {trap_zone_name}"
            predicted_by_logic = "Trap Zone Active"
        
        # If prediction is still undecided after high-priority overrides, proceed with core logic
        if prediction == '?':
            # Calculate Confidence based on currently detected features
            confidence = self.calculate_confidence(patterns, momentum, intuition_applied_flag, predicted_by_logic, bias_zone_active)

            # 4. Confidence Threshold (Relaxed: allow prediction even if <60, but recommendation will be Avoid)
            # Old logic: if confidence < 60, set prediction to '⚠️'
            # New logic: calculate prediction, then let recommendation logic handle confidence < 60
            
            last_outcome = history[-1]['main_outcome']
            
            # Core Prediction Logic based on Pattern Priority
            # Prioritize Dragon/FollowStreak if they exist, then Pingpong, then Cuts
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
                else: prediction = last_outcome 
                predicted_by_logic = "Two-Cut"
            elif 'Triple-Cut' in patterns:
                if len(history) >= 3 and history[-1]['main_outcome'] == history[-2]['main_outcome'] == history[-3]['main_outcome']:
                    prediction = 'B' if history[-1]['main_outcome'] == 'P' else 'P' 
                else: prediction = last_outcome 
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
            
            # Blacklist Pattern (Memory Logic) - applies AFTER initial pattern prediction
            # If the best prediction comes from a blocked pattern, reconsider or avoid.
            if prediction not in ['?', '⚠️']: # Only apply memory logic if a prediction was made
                if self.apply_memory_logic(patterns, momentum, prediction): # Pass current patterns/momentum
                    prediction = '⚠️' # Blocked by memory logic
                    risk = 'Memory Blocked'
                    recommendation = 'Avoid ❌'
                    predicted_by_logic = "Memory Logic Block"
            
            # Intuition Logic (If no strong pattern or blocked by memory)
            if prediction in ['?', '⚠️'] or predicted_by_logic == "Memory Logic Block": 
                intuition_result = self.apply_intuition_logic(history)
                if intuition_result:
                    prediction = intuition_result['prediction']
                    intuition_applied_flag = True
                    predicted_by_logic = f"Intuition ({intuition_result['reason']})"
                    # Confidence re-evaluation if intuition takes over
                    confidence = self.calculate_confidence(patterns, momentum, True, predicted_by_logic, bias_zone_active)
                    # Even if intuition gives a prediction, if confidence is low, still avoid
                    if confidence < 50: # Slightly relaxed confidence for intuition predictions
                        prediction = '⚠️'
                        risk = 'Low Confidence (Intuition)'
                        recommendation = 'Avoid ❌'
                        predicted_by_logic = "Low Confidence (Intuition)"
            
            # Final Fallback if no specific logic applies
            if prediction == '?':
                # If still no prediction, base on a simple majority in recent history (non-ties)
                recent_nontie = [item['main_outcome'] for item in history[-10:] if item['main_outcome'] != 'T']
                if recent_nontie:
                    p_count = recent_nontie.count('P')
                    b_count = recent_nontie.count('B')
                    if p_count > b_count: prediction = 'P'
                    elif b_count > p_count: prediction = 'B'
                    else: prediction = random.choice(['P', 'B']) # If tie, pick randomly
                    predicted_by_logic = "Majority Fallback"
                    risk = "Low Confidence / Majority"
                    recommendation = "Avoid ❌"
                else:
                    prediction = random.choice(['P', 'B']) # If no non-ties, truly random
                    predicted_by_logic = "Random Fallback (No Data)"
                    risk = "Low Confidence / Random"
                    recommendation = "Avoid ❌"

        # --- Adjust risk/recommendation based on Bias Zone (after prediction is made) ---
        if bias_zone_active and prediction not in ['?', '⚠️']:
            if prediction == bias_towards:
                risk = f"Bias Zone ({bias_towards} Favored)"
                # Recommendation remains Play, as it aligns with bias
            elif prediction != bias_towards: # If predicted outcome is AGAINST the bias
                risk = f"Bias Zone (Counter {bias_towards})"
                recommendation = 'Avoid ❌' # Strongly recommend avoiding if countering a strong bias
                predicted_by_logic = f"Counter Bias ({bias_towards})"

        # --- Final Recommendation Logic (Consolidate) ---
        # This block ensures recommendation is consistent based on final risk and prediction.
        if prediction == '⚠️':
            recommendation = 'Avoid ❌'
        elif risk in ['Trap Timer', 'New Pattern: First Bet Avoidance', 'New Pattern: Awaiting Confirmation(s)', 'Memory Blocked', 'Low Confidence', 'Drawdown Alert']:
            recommendation = 'Avoid ❌'
        elif 'Bias Zone (Counter' in risk: # If explicitly countering a bias
            recommendation = 'Avoid ❌'
        elif prediction in ['P', 'B']: # If a valid prediction is made and no high risks
            recommendation = 'Play ✅'
        else: # Should not happen if logic is complete, but for safety
            recommendation = 'Avoid ❌'

        # --- Store context for next learning step (only in main app loop) ---
        if not is_backtest:
            self.last_prediction_context = {
                'prediction': prediction,
                'patterns': patterns,
                'momentum': momentum,
                'intuition_applied': intuition_applied_flag,
                'predicted_by': predicted_by_logic,
                'dominant_pattern_id_at_prediction': current_dominant_pattern_id 
            }

        # --- DNA Backtest Simulation (run once per full prediction cycle) ---
        accuracy_str, hit_count, miss_count, drawdown_alert = self._run_backtest_simulation(history)
        if drawdown_alert:
            risk = "Drawdown Alert" 
            recommendation = "Avoid ❌"

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
            f"Backtest Accuracy: {accuracy_str}"
        )

        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'developer_view': developer_view_str,
            'accuracy': accuracy_str,
            'confidence': confidence 
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
        dominant_pattern_at_prediction = self.last_prediction_context['dominant_pattern_id_at_prediction']

        # Handle Trap Timer decrement first
        if self.hands_to_skip_due_to_trap_timer > 0:
            self.hands_to_skip_due_to_trap_timer -= 1
            # If skipping due to timer, don't update prediction performance or new pattern count
            # Reset New Pattern confirmation to force re-evaluation after skip period
            self.new_pattern_confirmation_count = 0 
            self.last_dominant_pattern_id = None 
            self.skip_first_bet_of_new_pattern_flag = False # Clear any pending new pattern skips

            # Clear context for next round, as no meaningful prediction was made for learning
            self.last_prediction_context = {
                'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
            }
            return # Exit early if skipping

        # Handle New Pattern First Bet Avoidance flag
        # If this hand was skipped due to new pattern first bet avoidance
        if self.skip_first_bet_of_new_pattern_flag:
            self.skip_first_bet_of_new_pattern_flag = False # Turn off the flag after this hand
            self.new_pattern_confirmation_count = 1 # Start confirmation count from 1 after the first skip
            self.last_dominant_pattern_id = dominant_pattern_at_prediction # Set for future comparisons
            
            # Clear context for next round, as no meaningful prediction for learning performance was made
            self.last_prediction_context = {
                'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
            }
            return # Exit early if skipping due to new pattern

        # Update New Pattern Confirmation count if not skipped
        # This needs to be based on the actual *current* dominant pattern, not the one from last_prediction_context
        # We need to re-evaluate the current dominant pattern here
        # For simplicity, if the dominant pattern matched the one when prediction was made, increment.
        # Otherwise, reset to 1 (new pattern detected by predict_next in next cycle will set the flag)
        if dominant_pattern_at_prediction is not None and dominant_pattern_at_prediction == self.last_dominant_pattern_id:
             self.new_pattern_confirmation_count += 1
        else:
             self.new_pattern_confirmation_count = 1 # New dominant pattern, reset count to 1

        self.last_dominant_pattern_id = dominant_pattern_at_prediction # Update for next round


        # Only update learning if a valid prediction was made (not '?' or '⚠️')
        if predicted_outcome not in ['?', '⚠️']:
            if actual_outcome == predicted_outcome:
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

        # Clear context after learning, this context applies to the prediction *just made*
        self.last_prediction_context = {
            'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
        }

    def update_learning_state_for_backtest(self, actual_outcome, predicted_outcome_for_backtest, patterns_detected, momentum_detected, intuition_applied):
        """
        Simplified update for backtesting.
        """
        # Backtest does not manage new pattern flags directly in this update function, as it re-evaluates
        # the entire state for each prediction point.

        if predicted_outcome_for_backtest not in ['?', '⚠️']:
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
