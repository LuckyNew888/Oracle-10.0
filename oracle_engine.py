# oracle_engine.py
import random

class OracleEngine:
    VERSION = "V2.0" # Version for the Oracle Engine logic itself
    PREDICTION_THRESHOLD = 15 # Minimum history needed for prediction

    def __init__(self):
        self.tam_sutr_wins = 0
        self.suan_sutr_wins = 0
        self.last_prediction_context = None # Stores context of the last prediction for learning
        self.patterns_data = {} # Conceptual storage for learned patterns
        self.momentum_data = {} # Conceptual storage for learned momentum
        self.last_dominant_pattern_id = None # Placeholder for a real pattern ID

    def detect_dna_patterns(self, history):
        """
        [Conceptual Method]
        This method would analyze the 'history' to identify recurring DNA patterns.
        In a real implementation, this would involve complex sequence analysis,
        hashing, or machine learning models trained on historical data.

        Returns:
            A dictionary of detected patterns and their strengths/ids.
        """
        # --- MOCK LOGIC FOR DEMONSTRATION ---
        # In a real scenario, this would be sophisticated pattern recognition.
        patterns = {}
        if len(history) >= 5:
            last_five = tuple(item['main_outcome'] for item in history[-5:])
            if last_five == ('P', 'P', 'B', 'P', 'P'):
                patterns['DoublePlayerRun'] = 0.8 # Example pattern with strength
                self.last_dominant_pattern_id = "DoublePlayerRun"
            elif last_five == ('B', 'B', 'P', 'B', 'B'):
                patterns['DoubleBankerRun'] = 0.8
                self.last_dominant_pattern_id = "DoubleBankerRun"
            else:
                self.last_dominant_pattern_id = "NoDominantPattern"
        else:
            self.last_dominant_pattern_id = "HistoryTooShort"

        # Simulate dynamic pattern learning
        if random.random() < 0.1: # 10% chance to "discover" a new pattern
            patterns[f"RandomPattern_{len(self.patterns_data) + 1}"] = random.uniform(0.1, 0.9)
        # --- END MOCK LOGIC ---
        return patterns

    def detect_momentum(self, history):
        """
        [Conceptual Method]
        This method analyzes recent trends to determine momentum (e.g., strong Player momentum, balanced).
        In a real implementation, this might involve counting recent streaks, analyzing win/loss ratios
        over a sliding window, or more advanced statistical analysis.

        Returns:
            A dictionary describing the current momentum.
        """
        # --- MOCK LOGIC FOR DEMONSTRATION ---
        # In a real scenario, this would be a detailed momentum analysis.
        momentum = {"recent_trend": "Neutral"}
        if len(history) >= 10:
            last_ten_outcomes = [item['main_outcome'] for item in history[-10:] if item['main_outcome'] != 'T']
            num_p = last_ten_outcomes.count('P')
            num_b = last_ten_outcomes.count('B')

            if num_p > num_b + 2:
                momentum["recent_trend"] = "Strong Player Momentum"
            elif num_b > num_p + 2:
                momentum["recent_trend"] = "Strong Banker Momentum"
            else:
                momentum["recent_trend"] = "Balanced"
        # --- END MOCK LOGIC ---
        return momentum

    def calculate_confidence(self, patterns, momentum, history):
        """
        [Conceptual Method]
        Calculates a confidence score for the prediction based on detected patterns and momentum.
        A higher confidence might lead to a more assertive prediction, or a lower confidence
        might suggest abstaining from betting (e.g., '⚠️').
        """
        # --- MOCK LOGIC FOR DEMONSTRATION ---
        confidence = 0.5 # Base confidence
        
        # Boost confidence if strong patterns are detected
        if patterns:
            for pattern_name, strength in patterns.items():
                confidence += strength * 0.1 # Add a portion of pattern strength
        
        # Adjust confidence based on momentum alignment
        if momentum.get("recent_trend") != "Neutral":
            confidence += 0.1
        
        # Penalize confidence if history is very short (though handled by threshold)
        if len(history) < 20:
            confidence -= (20 - len(history)) * 0.01

        return max(0.1, min(0.9, confidence)) # Keep confidence between 0.1 and 0.9
        # --- END MOCK LOGIC ---

    def predict_next(self, history, is_backtest=False):
        """
        Predicts the next outcome (P, B, or ⚠️) based on historical data,
        pattern analysis, and momentum.
        """
        if len(history) < self.PREDICTION_THRESHOLD:
            # Not enough data to make a reliable prediction
            self.last_prediction_context = None # Clear context if not predicting
            return {
                'prediction': '?',
                'prediction_mode': None,
                'accuracy': 'N/A',
                'developer_view': f'Not enough data ({len(history)}/{self.PREDICTION_THRESHOLD})',
                'predicted_by': 'Initialization'
            }

        # Step 1: Analyze patterns and momentum from the current history
        current_patterns = self.detect_dna_patterns(history)
        current_momentum = self.detect_momentum(history)
        confidence = self.calculate_confidence(current_patterns, current_momentum, history)

        # Step 2: Determine the raw prediction based on a simplified rule for demo
        # For a real system, this would be based on complex algorithms, e.g.,
        # statistical models, machine learning, or proprietary pattern matching.
        
        prediction = '?'
        if history:
            last_non_tie = None
            for item in reversed(history):
                if item['main_outcome'] != 'T':
                    last_non_tie = item['main_outcome']
                    break
            
            if last_non_tie:
                # Simple alternating prediction if no strong pattern/momentum
                prediction = 'P' if last_non_tie == 'B' else 'B'
                
                # Apply conceptual logic: If strong Banker momentum, prefer Banker
                if current_momentum.get("recent_trend") == "Strong Banker Momentum" and confidence > 0.6:
                    prediction = 'B'
                # If strong Player momentum, prefer Player
                elif current_momentum.get("recent_trend") == "Strong Player Momentum" and confidence > 0.6:
                    prediction = 'P'
                
                # Check for conceptual "DoubleRun" pattern
                if "DoublePlayerRun" in current_patterns and confidence > 0.7:
                     prediction = 'P' # Predict P if DoublePlayerRun detected
                elif "DoubleBankerRun" in current_patterns and confidence > 0.7:
                     prediction = 'B' # Predict B if DoubleBankerRun detected

        # Step 3: Determine prediction mode ('ตาม' or 'สวน') based on conceptual rules
        prediction_mode = 'ตาม' # Default
        # For demo, let's say 'สวน' mode is triggered by a specific pattern or low confidence scenario
        if "DoublePlayerRun" in current_patterns or "DoubleBankerRun" in current_patterns:
            if confidence < 0.5: # If pattern is weak but still detected
                prediction_mode = 'สวน'
        elif confidence < 0.4: # Low confidence can also imply 'สวน' (counter) or '⚠️'
            prediction_mode = 'สวน'
        
        # Step 4: Final prediction based on confidence
        final_prediction = prediction
        predicted_by_logic = "Core Logic"

        if confidence < 0.35: # If confidence is very low, advise no bet
            final_prediction = '⚠️'
            prediction_mode = '⚠️' # Override mode to warning
            predicted_by_logic = "Low Confidence"
        elif "Intuition" in current_patterns: # Conceptual example: intuition can override
             final_prediction = 'B' if random.random() > 0.5 else 'P' # Intuition is less certain
             predicted_by_logic = "Intuition Override"
             # Also, intuition might lead to a different mode
             prediction_mode = 'ตาม' if random.random() > 0.5 else 'สวน'


        # Dummy accuracy calculation for display
        # In a real system, accuracy would be a result of backtesting or ongoing validation.
        accuracy_val = (self.tam_sutr_wins + self.suan_sutr_wins) / (len(history) - self.PREDICTION_THRESHOLD + 1) if (len(history) - self.PREDICTION_THRESHOLD + 1) > 0 else 0
        accuracy = f"{accuracy_val * 100:.2f}%"

        # Store context of this prediction for the next `update_learning_state` call
        self.last_prediction_context = {
            'prediction': final_prediction,
            'prediction_mode': prediction_mode,
            'patterns': current_patterns,
            'momentum': current_momentum,
            'intuition_applied': predicted_by_logic == "Intuition Override",
            'predicted_by': predicted_by_logic,
            'dominant_pattern_id_at_prediction': self.last_dominant_pattern_id,
            'confidence': confidence
        }

        # Prepare developer view information
        developer_view_str = (
            f"History Length: {len(history)}\n"
            f"Last Outcome: {history[-1]['main_outcome'] if history else 'N/A'}\n"
            f"Calculated Confidence: {confidence:.2f}\n"
            f"Detected Patterns: {current_patterns}\n"
            f"Detected Momentum: {current_momentum}\n"
            f"Predicted by: {predicted_by_logic}\n"
            f"Predicted mode: {prediction_mode}\n"
            f"Tam Sutr Wins: {self.tam_sutr_wins}\n"
            f"Suan Sutr Wins: {self.suan_sutr_wins}"
        )

        return {
            'prediction': final_prediction,
            'prediction_mode': prediction_mode,
            'accuracy': accuracy,
            'developer_view': developer_view_str,
            'predicted_by': predicted_by_logic
        }

    def update_learning_state(self, actual_outcome, current_history):
        """
        Updates the engine's internal learning state (e.g., win counts for strategies)
        based on the actual outcome of a hand.
        """
        if not self.last_prediction_context:
            return # No previous prediction was made, so no learning update

        predicted = self.last_prediction_context['prediction']
        mode = self.last_prediction_context['prediction_mode']
        
        # Only update win counts if a valid prediction (P or B) was made and the outcome is not a Tie
        if predicted in ['P', 'B'] and actual_outcome != 'T':
            if predicted == actual_outcome: # Prediction was correct
                if mode == 'ตาม':
                    self.tam_sutr_wins += 1
                elif mode == 'สวน':
                    self.suan_sutr_wins += 1
            # If incorrect, no increment to wins, but the losing streak is handled in app.py

        # In a real system, you might also update:
        # - Pattern recognition models
        # - Momentum analysis parameters
        # - Confidence calculation heuristics
        # - Self-correction mechanisms based on performance
