import random
from collections import Counter

class OracleEngine:
    __version__ = "1.0" # Added version for Streamlit compatibility

    def __init__(self):
        self.history = []
        self.pattern_stats = {} # Now just for tracking counts, not success rates directly
        self.momentum_stats = {} # Now just for tracking counts
        self.sequence_memory_stats = {} # This will track counts of outcomes for sequences
        self.failed_pattern_instances = {} # Tracks simple pattern failures - Ensure this is always a dict
        self.tie_prediction_score = 0.1 # This is simplified
        self.super6_occurrences = 0 # This is simplified

        # Simplified weights for basic score calculation
        self.pattern_weights = {
            'Pingpong': 1.0, 'Dragon': 1.0, 'Two-Cut': 1.0, 'Triple-Cut': 1.0,
            'One-Two Pattern': 1.0, 'Two-One Pattern': 1.0, 'Broken Pattern': 0.5,
            'FollowStreak': 1.0, # Added from previous versions
        }
        self.momentum_weights = {
            'B3+ Momentum': 1.0, 'P3+ Momentum': 1.0, 'Steady Repeat Momentum': 1.0,
            'Ladder Momentum (1-1-2-1-3)': 0.8, 'Ladder Momentum (X-Y-XX-Y)': 0.7, # Simplified
        }
        self.sequence_weights = { # Simplified sequence weighting
            3: 0.3, 4: 0.4, 5: 0.5, 6: 0.6, 7: 0.7, 8: 0.8,
        }
        
        self.confidence_threshold_play = 80 # Default for basic engine
        self.confidence_threshold_consider = 60 # For 'Consider' recommendation


    def reset_history(self):
        # This will re-initialize the entire engine, clearing all learning states
        self.__init__()

    def reset_learning_states_on_undo(self): # For partial reset
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.failed_pattern_instances = {} # Ensure reset to empty dict
        self.tie_prediction_score = 0.1
        self.super6_occurrences = 0


    def _get_recent_results(self, n, full_history_list):
        """Extracts only P and B outcomes from the last n hands of full_history_list."""
        pb_history = []
        for item in full_history_list[-n:]:
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

    def detect_patterns(self, history, big_road_data_dummy): # big_road_data is a dummy here
        results = self._get_recent_results(10, history) # Pass full history
        patterns = []

        if len(results) < 4: # Need at least 4 for most patterns
            return patterns

        # Pingpong (Alternating P/B pattern)
        if len(results) >= 6 and all(results[i] != results[i+1] for i in range(len(results)-1)):
            patterns.append("Pingpong")
        
        # Dragon (3+ consecutive) - simple check
        if len(set(results[-3:])) == 1:
            patterns.append("Dragon")
        
        # Two-Cut (BB-PP) - simple check
        if len(results) >= 4 and results[-2:] == results[-4:-2] and results[-2] != results[-4]:
            patterns.append("Two-Cut")

        # Simplified: Triple-Cut, One-Two, Two-One, Broken Pattern, FollowStreak for v1.0
        # These are much more complex in the advanced engine.
        if len(results) >= 6:
            if len(set(results[-6:-3])) == 1 and len(set(results[-3:])) == 1 and results[-6] != results[-3]:
                patterns.append("Triple-Cut")
        
        if len(results) >= 4:
            # One-Two (B-PP-B)
            if results[-4:] == ['B','P','P','B'] or results[-4:] == ['P','B','B','P']:
                patterns.append("One-Two Pattern")
            # Two-One (BB-P-BB)
            if results[-4:] == ['B','B','P','B'] or results[-4:] == ['P','P','B','P']:
                patterns.append("Two-One Pattern")
        
        if len(results) >= 7 and ("BPBPPBP" in "".join(results[-7:]) or "PBPBBBP" in "".join(results[-7:])):
            patterns.append("Broken Pattern")

        return patterns

    def detect_momentum(self, history, big_road_data_dummy): # big_road_data is a dummy here
        results = self._get_recent_results(10, history) # Pass full history
        momentum = []

        if len(results) < 3: return momentum # Need at least 3 for basic momentum

        streak = 1
        for i in range(len(results)-2, -1, -1):
            if results[i] == results[i+1]:
                streak += 1
            else:
                break
        if streak >= 3:
            side = results[-1]
            momentum.append(f"{side}3+ Momentum")
        
        # Simplified Steady Repeat & Ladder for v1.0
        if len(results) >= 7:
            if all(results[i] != results[i+1] for i in range(len(results)-1)):
                momentum.append("Steady Repeat Momentum")
        
        return momentum

    def _detect_sequences(self, history):
        # This version uses simpler sequence tracking (Counter of recent outcomes)
        return Counter([x['main_outcome'] for x in history[-6:] if x['main_outcome'] in ['P', 'B']]) # Only P/B for primary sequences

    def confidence_score(self, history, big_road_data_dummy): # big_road_data is a dummy here
        patterns = self.detect_patterns(history, big_road_data_dummy)
        momentum = self.detect_momentum(history, big_road_data_dummy)
        sequences_counts = self._detect_sequences(history) # Get counts like {'P': 3, 'B': 2}

        conf = 0.0
        
        # Add score based on patterns
        for p in patterns:
            conf += self.pattern_weights.get(p, 0)
        
        # Add score based on momentum
        for m in momentum:
            conf += self.momentum_weights.get(m, 0)
        
        # Add score based on sequence counts (simple scaling by count)
        for outcome, count in sequences_counts.items():
            # Apply a simple increasing weight based on count for P/B
            if outcome in ['P', 'B']:
                if count == 3: conf += 0.5
                elif count == 4: conf += 1.0
                elif count >= 5: conf += 1.5

        # Simplified Trap Zone check for v1.0
        if self._is_in_trap_zone(history):
            conf -= 1.0 # Reduce confidence if in trap zone

        # Scale final confidence to 0-100 range (adjusted multiplier for simplified weights)
        # Assuming max possible score from patterns/momentum/sequences might be around 5-6 points
        return max(0, min(100, round(conf * 10, 2))) # Adjusted multiplier

    def _is_in_trap_zone(self, history):
        """Simple trap zone: 3+ alternating or rapid changes."""
        results = self._get_recent_results(4, history) # Last 4 P/B only
        if len(results) < 4: return False
        
        # Check for rapid alternation (e.g., PBPB)
        if results[-1] != results[-2] and results[-2] != results[-3] and results[-3] != results[-4]:
            return True
        return False

    def predict_next(self, current_live_drawdown=0):
        if len(self.history) < 1: # Need at least 1 hand to predict anything
            return {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Insufficient Data', 'confidence': 0, 'developer_view': 'No history yet.'}

        # Simplified prediction based on recent P/B counts
        pb_counts = self._detect_sequences(self.history) # Uses Counter, simplified sequences
        
        # Basic prediction based on highest count in recent history
        if 'P' in pb_counts and 'B' in pb_counts:
            if pb_counts['P'] > pb_counts['B']:
                prediction_result = 'P'
            elif pb_counts['B'] > pb_counts['P']:
                prediction_result = 'B'
            else: # Equal counts, fallback to last result
                prediction_result = self._get_recent_results(1,self.history)[-1] if self._get_recent_results(1,self.history) else 'B' # Default B if no history
        elif 'P' in pb_counts:
            prediction_result = 'P'
        elif 'B' in pb_counts:
            prediction_result = 'B'
        else: # No P/B in last 6, default to B
            prediction_result = 'B' 

        # Calculate confidence score
        confidence = self.confidence_score(self.history, [])

        recommendation = "Avoid ❌"
        risk = "Normal"
        
        if confidence >= self.confidence_threshold_play: # 80%
            recommendation = "Play ✅"
        elif confidence >= self.confidence_threshold_consider: # 60%
            recommendation = "Consider ⚠️"
            risk = "Moderate"
        else:
            risk = "High"


        # Drawdown Protection (Highest Priority)
        DRAWDOWN_LIMIT_FOR_AVOID = 4 # If live_drawdown hits 4 or more, force Avoid
        if current_live_drawdown >= DRAWDOWN_LIMIT_FOR_AVOID:
            prediction_result = '?' # No specific prediction
            risk = f"High Drawdown ({current_live_drawdown} misses)"
            recommendation = "Avoid ❌ (ป้องกันแพ้ติดกัน)"
            
        developer_view_lines = []
        developer_view_lines.append(f"Confidence: {confidence}%")
        developer_view_lines.append(f"Patterns: {self.detect_patterns(self.history, [])}")
        developer_view_lines.append(f"Momentum: {self.detect_momentum(self.history, [])}")
        developer_view_lines.append(f"Recent PB Counts: {pb_counts}")
        developer_view_lines.append(f"Is in Trap Zone: {self._is_in_trap_zone(self.history)}")


        return {
            'prediction': prediction_result,
            'confidence': confidence,
            'recommendation': recommendation,
            'risk': risk,
            'developer_view': "\n".join(developer_view_lines)
        }

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected_dummy, momentum_detected_dummy, sequences_detected_dummy):
        """
        Simplified learning update for v1.0.
        This version only tracks basic counts and ties/super6 occurrences.
        """
        # Note: pattern_stats, momentum_stats, sequence_memory_stats are not updated here in this simplified version
        # as they are based on simpler logic (e.g. counts in detect_patterns directly)
        
        # Simplified Tie/Super6 tracking
        if actual_outcome == 'T':
            self.tie_prediction_score = min(1.0, self.tie_prediction_score + 0.05)
        else:
            self.tie_prediction_score = max(0.1, self.tie_prediction_score * 0.95)
        
        if actual_outcome == 'S6':
            self.super6_occurrences += 1
        
        # Track simple pattern failures (if pred != actual)
        if predicted_outcome != actual_outcome:
             for p in self.detect_patterns(self.history, []): # Re-detect patterns from current history
                 self.failed_pattern_instances[p] = self.failed_pattern_instances.get(p, 0) + 1
