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
    VERSION = "Final V1.14" # System version identifier - Reliable Counter

    def __init__(self):
        # Performance tracking for patterns and momentum
        self.pattern_performance = {
            'Pingpong': {'success': 0, 'fail': 0}, 'Dragon': {'success': 0, 'fail': 0},
            'Two-Cut': {'success': 0, 'fail': 0}, 'Triple-Cut': {'success': 0, 'fail': 0},
            'One-Two Pattern': {'success': 0, 'fail': 0}, 'Two-One Pattern': {'success': 0, 'fail': 0},
            'Broken Pattern': {'success': 0, 'fail': 0}, 'FollowStreak': {'success': 0, 'fail': 0},
            'Fake Alternating': {'success': 0, 'fail': 0},
            'DragonBreak': {'success': 0, 'fail': 0}, # New: For reliable counter
            'PingpongBreak': {'success': 0, 'fail': 0} # New: For reliable counter
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
            'Broken Pattern': 0.6, 'Fake Alternating': 0.5,
            'DragonBreak': 0.85, # New weight for counter pattern
            'PingpongBreak': 0.8 # New weight for counter pattern
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
            'dominant_pattern_id_at_prediction': None,
            'prediction_mode': None # Added: 'ตาม' or 'สวน' or '⚠️'
        }

        self.trap_zone_active = False # General Trap Zone flag
        
        # Performance related caching for Backtest
        self._cached_accuracy_str = "N/A"
        self._cached_hit_count = 0
        self._cached_miss_count = 0
        self._cached_drawdown_alert = False

        # Counters for 'ตามสูตรชนะ' and 'สวนสูตรชนะ'
        self.tam_sutr_wins = 0
        self.suan_sutr_wins = 0


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
            'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 
            'predicted_by': None, 'dominant_pattern_id_at_prediction': None, 'prediction_mode': None
        }
        self.trap_zone_active = False
        self._cached_accuracy_str = "N/A"
        self._cached_hit_count = 0
        self._cached_miss_count = 0
        self._cached_drawdown_alert = False
        self.tam_sutr_wins = 0 # Reset new counters
        self.suan_sutr_wins = 0 # Reset new counters


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
        if len(history) < 3: 
            return patterns

        seq = ''.join([item['main_outcome'] for item in history[-12:] if item['main_outcome'] != 'T']) 
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

        # One-Two Pattern (1/2) - Corrected: PBB PBB or BPP BPP
        if len(seq) >= 6:
            if seq[-6:] == 'PBBPBB': patterns.append('One-Two Pattern') # P-BB-P-BB
            if seq[-6:] == 'BPPBPP': patterns.append('One-Two Pattern') # B-PP-B-PP

        # Two-One Pattern (2/1) - Corrected: PPB PPB or BBP BBP
        if len(seq) >= 6: 
            if seq[-6:] == 'PPBPPB': patterns.append('Two-One Pattern') # PP-B-PP
            if seq[-6:] == 'BBPBBP': patterns.append('Two-One Pattern') # BB-P-BB
        
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

        relevant_history = [item['main_outcome'] for item in history[-12:] if item['main_outcome'] != 'T'] 
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

        # Steady Repeat Momentum (e.g., PBPBPB -> expect P)
        if len(relevant_history) >= 4: 
            recent_seq = ''.join(relevant_history[-4:])
            if recent_seq == 'PBPB' or recent_seq == 'BPBP':
                momentum.append('Steady Repeat Momentum')

        return list(set(momentum))

    # --- New: Reversal Pattern Detection for Reliable Counter ---
    def detect_reversal_patterns(self, history):
        reversal_patterns = []
        if len(history) < 5: # Need at least 5 for a streak break
            return reversal_patterns
        
        seq_nontie = ''.join([item['main_outcome'] for item in history[-10:] if item['main_outcome'] != 'T']) # Look at last 10 non-tie hands
        if len(seq_nontie) < 5: return reversal_patterns

        # DragonBreak: Long streak (4 or more) followed by an opposite outcome
        # e.g., BBBBP, PPPPBB
        if len(seq_nontie) >= 5:
            if (seq_nontie[-5:-1] == 'BBBB' and seq_nontie[-1] == 'P') or \
               (seq_nontie[-5:-1] == 'PPPP' and seq_nontie[-1] == 'B'):
                reversal_patterns.append('DragonBreak')
        
        # PingpongBreak: Pingpong pattern broken by a repeated outcome
        # e.g., PBPBPB then P (instead of B) OR BPBPBP then B (instead of P)
        if len(seq_nontie) >= 7: # Need at least 6 for pingpong + 1 for break
            if (seq_nontie[-7:-1] == 'PBPBPB' and seq_nontie[-1] == 'P') or \
               (seq_nontie[-7:-1] == 'BPBPBP' and seq_nontie[-1] == 'B'):
                reversal_patterns.append('PingpongBreak')

        return list(set(reversal_patterns))


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
        # Note: PingpongBreak for counter is specifically when PBPBPB -> P (a double P)
        # This one is when PBPBPB -> then B (a break to opposite)
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
        
        relevant_history = [item['main_outcome'] for item in history[-20:] if item['main_outcome'] != 'T']
        if len(relevant_history) < 10: 
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

        confidence_base = (total_weighted_score / total_weight_sum) if total_weight_sum > 0 else 0.5 
        
        if intuition_applied and primary_prediction_logic and "Intuition" in primary_prediction_logic:
            intuition_key = primary_prediction_logic.replace("Intuition (", "").replace(")", "")
            intuition_success_rate = self.get_success_rate(self.intuition_performance, intuition_key)
            confidence_base = (confidence_base * 0.7 + intuition_success_rate * 0.3) 
            confidence_base *= 0.8 

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
        
        seq_nontie = ''.join([item['main_outcome'] for item in history[-5:] if item['main_outcome'] != 'T']) 
        if len(seq_nontie) < 3: return None

        # PBP -> P (Double Confirmed)
        if seq_nontie.endswith('PBP'):
            return {'prediction': 'P', 'reason': 'PBP -> P'}
        # BBPBB -> B (Reverse Trap)
        if seq_nontie.endswith('BBPBB'):
            return {'prediction': 'B', 'reason': 'BBPBB -> B'}
        # PPBPP -> P (Zone Flow)
        if seq_nontie.endswith('PPBPP'):
            return {'prediction': 'P', 'reason': 'PPBPP -> P'}

        # Steady Outcome Guess: If the last few outcomes are mostly one type, and it's not a strong streak
        if len(seq_nontie) >= 4: 
            p_count = seq_nontie.count('P')
            b_count = seq_nontie.count('B')
            
            if p_count >= len(seq_nontie) - 1 and b_count <= 1: 
                return {'prediction': 'P', 'reason': 'Steady Outcome Guess (P)'}
            if b_count >= len(seq_nontie) - 1 and p_count <= 1: 
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

        temp_engine = OracleEngine()
        hit_count = 0
        miss_count = 0
        current_drawdown = 0
        max_drawdown_alert = False 

        for i in range(min(10, len(full_history))): 
            temp_engine.update_learning_state_for_backtest(full_history[i]['main_outcome'], None, [], [], False) 

        for i in range(10, len(full_history)):
            history_for_prediction = full_history[:i] 
            actual_outcome = full_history[i]['main_outcome']

            prediction_result = temp_engine.predict_next(history_for_prediction, is_backtest=True)
            predicted_outcome = prediction_result['prediction']

            dev_view_str = prediction_result['developer_view']
            patterns_match_str = self._extract_dev_view_part(dev_view_str, "DNA Patterns:")
            momentum_match_str = self._extract_dev_view_part(dev_view_str, "Momentum:")
            
            patterns_match = [p.strip() for p in patterns_match_str.split(',') if p.strip() != 'None'] if patterns_match_str else []
            momentum_match = [m.strip() for m in momentum_match_str.split(',') if m.strip() != 'None'] if momentum_match_str else []
            intuition_applied_in_dev = 'Intuition (' in dev_view_str
            
            temp_engine.update_learning_state_for_backtest(actual_outcome, predicted_outcome, patterns_match, momentum_match, intuition_applied_in_dev)

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
            dict: Contains prediction, recommendation, risk, developer_view, accuracy, confidence, prediction_mode.
        """
        # Core Avoid Condition 1: Not Enough Data (Now 15 hands)
        if len(history) < 15: 
            if not is_backtest: 
                self.last_prediction_context = {
                    'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 
                    'predicted_by': None, 'dominant_pattern_id_at_prediction': None, 'prediction_mode': None
                }
            return {
                'prediction': '?',
                'recommendation': 'Avoid ❌', 
                'risk': 'Not enough data', 
                'developer_view': f'Not enough data for full analysis. Requires at least 15 hands. (Current: {len(history)} hands)',
                'accuracy': self._cached_accuracy_str, 
                'confidence': 'N/A',
                'prediction_mode': None 
            }
        
        # --- Dynamic Prediction Adjustment (Re-analyze every time) ---
        patterns = self.detect_dna_patterns(history)
        momentum = self.detect_momentum(history)
        reversal_patterns = self.detect_reversal_patterns(history) # New: Detect reversal patterns
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

        prediction = '?' 
        risk = 'Normal' 
        predicted_by_logic = "None"
        intuition_applied_flag = False
        confidence = 0 
        prediction_mode = 'ตาม' # Default prediction mode is 'ตาม' (ตามสูตร)

        # Calculate confidence first
        confidence = self.calculate_confidence(patterns, momentum, False, None, bias_zone_active)

        # --- Core Prediction Logic (Attempt to get P/B) ---
        last_nontie_outcome = None
        for i in range(len(history) - 1, -1, -1):
            if history[i]['main_outcome'] != 'T':
                last_nontie_outcome = history[i]['main_outcome']
                break

        # NEW: Reliable Counter Logic (Higher priority than general patterns if reversal detected)
        if len(reversal_patterns) > 0 and last_nontie_outcome:
            # If reversal pattern is strong enough (e.g., confidence for this pattern is high, or just presence)
            # For simplicity, we trigger counter if any reversal pattern is present AND confidence is above 40%
            # You can tune this confidence threshold for 'สวน' mode
            if confidence >= 40: # Example threshold for reliable counter
                prediction = 'B' if last_nontie_outcome == 'P' else 'P'
                risk = f'High Risk: Countering Reversal ({",".join(reversal_patterns)})'
                predicted_by_logic = f"Counter (Reversal: {','.join(reversal_patterns)})"
                prediction_mode = 'สวน'
            else: # Reversal pattern present, but overall confidence too low to even counter reliably
                prediction = '⚠️'
                risk = f'Low Confidence ({confidence}%) - Reversal detected but too risky to counter'
                predicted_by_logic = f"Avoid (Confidence {confidence}%)"
                prediction_mode = '⚠️'

        elif confidence < 50: # Standard Low Confidence Avoid (if no reliable counter pattern)
            prediction = '⚠️'
            risk = f'Low Confidence ({confidence}%)'
            predicted_by_logic = f"Avoid (Confidence {confidence}%)"
            prediction_mode = '⚠️'
        else: # Confidence >= 50, proceed with normal 'ตามสูตร' pattern prediction
            
            # Prioritize strongest patterns/momentum
            if 'Dragon' in patterns:
                prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P', 'B']) 
                predicted_by_logic = "Dragon"
            elif 'FollowStreak' in patterns:
                prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P', 'B'])
                predicted_by_logic = "FollowStreak"
            elif 'Pingpong' in patterns:
                prediction = 'B' if last_nontie_outcome == 'P' else 'P' if last_nontie_outcome else random.choice(['P', 'B'])
                predicted_by_logic = "Pingpong"
            elif 'Two-Cut' in patterns:
                relevant_nontie_history = [item['main_outcome'] for item in history if item['main_outcome'] != 'T']
                if len(relevant_nontie_history) >= 2 and relevant_nontie_history[-1] == relevant_nontie_history[-2]:
                    prediction = 'B' if relevant_nontie_history[-1] == 'P' else 'P' 
                else: 
                    prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P','B'])
                predicted_by_logic = "Two-Cut"
            elif 'Triple-Cut' in patterns:
                relevant_nontie_history = [item['main_outcome'] for item in history if item['main_outcome'] != 'T']
                if len(relevant_nontie_history) >= 3 and relevant_nontie_history[-1] == relevant_nontie_history[-2] == relevant_nontie_history[-3]:
                    prediction = 'B' if relevant_nontie_history[-1] == 'P' else 'P' 
                else:
                    prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P','B'])
                predicted_by_logic = "Triple-Cut"
            elif 'B3+ Momentum' in momentum and last_nontie_outcome == 'B':
                prediction = 'B'
                predicted_by_logic = "B3+ Momentum"
            elif 'P3+ Momentum' in momentum and last_nontie_outcome == 'P':
                prediction = 'P'
                predicted_by_logic = "P3+ Momentum"
            elif 'Steady Repeat Momentum' in momentum: 
                prediction = 'P' if last_nontie_outcome == 'B' else 'B' if last_nontie_outcome else random.choice(['P','B'])
                predicted_by_logic = "Steady Repeat Momentum"
            
            elif 'One-Two Pattern' in patterns:
                relevant_nontie_history = [item['main_outcome'] for item in history if item['main_outcome'] != 'T']
                if len(relevant_nontie_history) >= 3 and relevant_nontie_history[-1] == relevant_nontie_history[-2] and relevant_nontie_history[-1] != relevant_nontie_history[-3]: 
                    prediction = relevant_nontie_history[-3] 
                else:
                    prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P','B'])
                predicted_by_logic = "One-Two Pattern"
            
            elif 'Two-One Pattern' in patterns:
                relevant_nontie_history = [item['main_outcome'] for item in history if item['main_outcome'] != 'T']
                if len(relevant_nontie_history) >= 3 and relevant_nontie_history[-1] != relevant_nontie_history[-2] and relevant_nontie_history[-2] == relevant_nontie_history[-3]: 
                    prediction = relevant_nontie_history[-1] 
                else:
                    prediction = last_nontie_outcome if last_nontie_outcome else random.choice(['P','B'])
                predicted_by_logic = "Two-One Pattern"

            # Intuition Logic (If no specific pattern prediction yet)
            if prediction == '?': 
                intuition_result = self.apply_intuition_logic(history)
                if intuition_result:
                    prediction = intuition_result['prediction']
                    intuition_applied_flag = True
                    predicted_by_logic = f"Intuition ({intuition_result['reason']})"
            
            # Final Fallback if still no prediction from patterns/momentum/intuition
            if prediction == '?':
                if last_nontie_outcome: 
                    prediction = last_nontie_outcome
                    predicted_by_logic = "Last Outcome Fallback"
                else: 
                    prediction = random.choice(['P', 'B']) 
                    predicted_by_logic = "Random Fallback (No Non-Tie Data)"

        # --- Set Risk Flags based on conditions (for developer_view) ---
        if self.hands_to_skip_due_to_trap_timer > 0:
            if risk == 'Normal': risk = f"Trap Timer ({self.hands_to_skip_due_to_trap_timer} skips left)"
            else: risk += f", Trap Timer ({self.hands_to_skip_due_to_trap_timer} skips left)"
        
        if not is_backtest and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"] and prediction != '⚠️': 
            if self.last_dominant_pattern_id is not None and self.last_dominant_pattern_id != current_dominant_pattern_id:
                self.skip_first_bet_of_new_pattern_flag = True 
                self.new_pattern_confirmation_count = 0 
                
            if self.skip_first_bet_of_new_pattern_flag: 
                if risk == 'Normal': risk = 'New Pattern: First Bet Avoidance'
                else: risk += ', New Pattern: First Bet Avoidance'
            elif self.new_pattern_confirmation_count < self.NEW_PATTERN_CONFIRMATION_REQUIRED:
                if risk == 'Normal': risk = f"New Pattern: Awaiting {self.NEW_PATTERN_CONFIRMATION_REQUIRED - self.new_pattern_confirmation_count} Confirmation(s)"
                else: risk += f", New Pattern: Awaiting {self.NEW_PATTERN_CONFIRMATION_REQUIRED - self.new_pattern_confirmation_count} Confirmation(s)"

        if self.trap_zone_active and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"] and prediction != '⚠️':
            if risk == 'Normal': risk = f"Trap Zone: {trap_zone_name}"
            else: risk += f", Trap Zone: {trap_zone_name}"

        if self.apply_memory_logic(patterns, momentum) and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"] and prediction != '⚠️':
            if risk == 'Normal': risk = 'Memory Blocked'
            else: risk += ', Memory Blocked'

        if bias_zone_active and predicted_by_logic not in [f"Avoid (Confidence {confidence}%)"] and prediction != '⚠️':
            if prediction != bias_towards: 
                if risk == 'Normal': risk = f"Bias Zone (Counter {bias_towards})"
                else: risk += f", Bias Zone (Counter {bias_towards})"
            else: 
                if risk == 'Normal': risk = f"Bias Zone ({bias_towards} Favored)"
                else: risk += f", Bias Zone ({bias_towards} Favored)"
        
        if self._cached_drawdown_alert:
            if risk == 'Normal': risk = "Drawdown Alert"
            else: risk += ", Drawdown Alert"

        recommendation = 'Play ✅' # Default for P/B prediction
        if prediction == '⚠️':
            recommendation = 'Avoid ❌' 

        if not is_backtest:
            self.last_prediction_context = {
                'prediction': prediction, 
                'patterns': patterns,
                'momentum': momentum,
                'intuition_applied': intuition_applied_flag,
                'predicted_by': predicted_by_logic,
                'dominant_pattern_id_at_prediction': current_dominant_pattern_id,
                'prediction_mode': prediction_mode 
            }

        dev_view_patterns = ', '.join(patterns) if patterns else 'None'
        dev_view_momentum = ', '.join(momentum) if momentum else 'None'
        dev_view_reversal_patterns = ', '.join(reversal_patterns) if reversal_patterns else 'None' # Added to dev view
        dev_view_trap = trap_zone_name if trap_zone_name else 'None'
        dev_view_bias = f"Active ({bias_towards})" if bias_zone_active else 'None'
        
        developer_view_str = (
            f"Current History: {''.join([item['main_outcome'] for item in history[-10:]])}; "
            f"DNA Patterns: {dev_view_patterns}; "
            f"Momentum: {dev_view_momentum}; "
            f"Reversal Patterns: {dev_view_reversal_patterns}; " # Added to dev view
            f"Trap Zone: {dev_view_trap}; "
            f"Bias Zone: {dev_view_bias}; "
            f"Confidence: {confidence}%; " 
            f"Predicted by: {predicted_by_logic}; "
            f"Prediction Mode: {prediction_mode}; " 
            f"Backtest Accuracy: {self._cached_accuracy_str}; "
            f"Risk Flags: {risk}; " # Added risk flags to dev view for full context
            f"Recommendation: {recommendation}" # Added recommendation to dev view for full context
        )

        return {
            'prediction': prediction,
            'recommendation': recommendation, 
            'risk': risk, 
            'developer_view': developer_view_str,
            'accuracy': self._cached_accuracy_str, 
            'confidence': confidence,
            'prediction_mode': prediction_mode 
        }

    def update_learning_state(self, actual_outcome, history_for_backtest_calc=None):
        """
        Updates the engine's learning states based on the actual outcome of the previous hand.
        This method is called by the Streamlit app after each result is added.
        Args:
            actual_outcome (str): The actual outcome of the hand (P, B, or T).
            history_for_backtest_calc (list): The full current history, used for optional backtest calculation.
        """
        predicted_outcome_context = self.last_prediction_context['prediction'] 
        patterns_detected = self.last_prediction_context['patterns']
        momentum_detected = self.last_prediction_context['momentum']
        intuition_applied = self.last_prediction_context['intuition_applied']
        predicted_by = self.last_prediction_context['predicted_by']
        dominant_pattern_at_prediction = self.last_prediction_context['dominant_pattern_id_at_prediction']
        prediction_mode_at_context = self.last_prediction_context['prediction_mode'] 

        # Handle Trap Timer decrement first
        if self.hands_to_skip_due_to_trap_timer > 0:
            self.hands_to_skip_due_to_trap_timer -= 1
        
        # New pattern confirmation flags should still be managed regardless of Trap Timer.
        if dominant_pattern_at_prediction is not None: 
            if dominant_pattern_at_prediction == self.last_dominant_pattern_id:
                self.new_pattern_confirmation_count += 1
            else:
                self.new_pattern_confirmation_count = 1 
            self.last_dominant_pattern_id = dominant_pattern_at_prediction 
        else: 
            self.new_pattern_confirmation_count = 0 
            self.last_dominant_pattern_id = None

        if self.skip_first_bet_of_new_pattern_flag:
            self.skip_first_bet_of_new_pattern_flag = False 

        if predicted_outcome_context in ['P', 'B']: 
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

                # NEW: Update ตามสูตรชนะ / สวนสูตรชนะ counters
                if actual_outcome != 'T': 
                    if prediction_mode_at_context == 'ตาม':
                        self.tam_sutr_wins += 1
                    elif prediction_mode_at_context == 'สวน':
                        self.suan_sutr_wins += 1

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
                
                for indicator in patterns_detected + momentum_detected:
                    self.memory_blocked_patterns[indicator] = self.memory_blocked_patterns.get(indicator, 0) + 1

        # Recalculate Backtest metrics AFTER learning for this hand
        if history_for_backtest_calc and len(history_for_backtest_calc) >= 20:
            self._cached_accuracy_str, self._cached_hit_count, self._cached_miss_count, self._cached_drawdown_alert = \
                self.calculate_backtest_metrics(history_for_backtest_calc)
        
        self.last_prediction_context = {
            'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 
            'predicted_by': None, 'dominant_pattern_id_at_prediction': None, 'prediction_mode': None
        }

    def update_learning_state_for_backtest(self, actual_outcome, predicted_outcome_for_backtest, patterns_detected, momentum_detected, intuition_applied):
        """
        Simplified update for backtesting.
        """
        if predicted_outcome_for_backtest in ['P', 'B']: 
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
