import pandas as pd
import numpy as np
import google.generativeai as genai
import os
import json
import streamlit as st # Import Streamlit to access st.secrets for API key

# Define the current expected version of the OracleEngine
# This should be incremented whenever there are significant structural changes to the engine logic
CURRENT_ENGINE_VERSION = "1.12" 

# --- Gemini API Key Configuration ---
# This block attempts to configure the Gemini API key.
# It prioritizes Streamlit secrets (for deployment) then environment variables (for local dev).
# If neither is found, it will warn the user and disable Gemini functionality.
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        print("Gemini API key configured from Streamlit secrets.")
    elif "GEMINI_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        print("Gemini API key configured from environment variables.")
    else:
        # If no API key is found, set a dummy key to prevent `genai.configure` from failing
        # but the model initialization will still fail/warn.
        genai.configure(api_key="DUMMY_KEY_FOR_TESTING_ONLY")
        print("Warning: Gemini API key not found in Streamlit secrets or environment variables.")
except Exception as e:
    print(f"Error configuring Gemini API key: {e}")
    # Fallback in case of an unexpected error during configuration
    genai.configure(api_key="DUMMY_KEY_FOR_TESTING_ONLY_ERROR")


# --- Gemini Model Initialization ---
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" # Using the latest flash model for speed
GEMINI_MODEL = None
try:
    if genai.get_default_configured_api_key() and genai.get_default_configured_api_key() != "DUMMY_KEY_FOR_TESTING_ONLY":
        GEMINI_MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
        print(f"Gemini model '{GEMINI_MODEL_NAME}' initialized.")
    else:
        print("Gemini model not initialized: API key not properly configured or is a dummy key.")
except Exception as e:
    print(f"Could not initialize Gemini model '{GEMINI_MODEL_NAME}': {e}")
    GEMINI_MODEL = None # Ensure GEMINI_MODEL is None if initialization fails


# --- Cached function for backtest accuracy ---
# This function helps in calculating historical accuracy efficiently.
@st.cache_data(ttl=3600) # Cache for 1 hour
def _cached_backtest_accuracy(history_data, oracle_engine_instance_for_context):
    """
    Calculates historical prediction accuracy based on a given history and engine logic.
    This function should simulate predictions over the history to evaluate accuracy.
    Note: For a real-time app, this might be too heavy. Consider background processing
    or pre-calculation if history is very long.
    """
    if not history_data or len(history_data) < 3:
        return {"overall_accuracy": 0.0, "player_accuracy": 0.0, "banker_accuracy": 0.0, "s6_accuracy": 0.0, "total_bets": 0}

    # Create a temporary engine instance for backtesting to not mess with current session's engine state
    temp_engine = OracleEngine() # This creates a clean engine for simulation

    total_correct = 0
    total_player_bets = 0
    player_correct = 0
    total_banker_bets = 0
    banker_correct = 0
    total_s6_bets = 0
    s6_correct = 0
    total_predictions_made = 0

    simulated_history = []
    for i, current_hand_data in enumerate(history_data):
        if i < 2: # Need at least 2 hands to make a prediction (3rd hand)
            simulated_history.append(current_hand_data)
            continue

        # Build big road data up to the current hand for prediction context
        sim_big_road_data = _build_big_road_data(simulated_history)
        
        # Simulate prediction BEFORE adding the current hand's actual result
        sim_prediction_output = temp_engine.predict_next(
            current_live_drawdown=0, # Drawdown logic is complex for backtesting, assume 0 or handle separately
            current_big_road_data=sim_big_road_data
        )
        sim_predicted_side = sim_prediction_output.get('prediction')

        # Only evaluate if a specific prediction was made
        if sim_predicted_side != '?':
            total_predictions_made += 1
            actual_outcome = current_hand_data['main_outcome']

            if sim_predicted_side == 'P':
                total_player_bets += 1
                if actual_outcome == 'P':
                    player_correct += 1
                    total_correct += 1
            elif sim_predicted_side == 'B':
                total_banker_bets += 1
                if actual_outcome == 'B' or actual_outcome == 'S6': # Banker prediction correct if S6
                    banker_correct += 1
                    total_correct += 1
            elif sim_predicted_side == 'S6':
                total_s6_bets += 1
                if actual_outcome == 'S6':
                    s6_correct += 1
                    total_correct += 1
        
        # Now add the current hand's actual result to the simulated history for the next prediction
        # (This simulates how the engine learns/updates after each hand)
        simulated_history.append(current_hand_data)
        # Manually update temp_engine's learning states (a simplified version)
        if sim_predicted_side != '?':
            temp_engine._update_learning(
                predicted_outcome=sim_predicted_side,
                actual_outcome=current_hand_data['main_outcome'],
                patterns_detected=temp_engine.detect_patterns(simulated_history[:-1], _build_big_road_data(simulated_history[:-1])),
                momentum_detected=temp_engine.detect_momentum(simulated_history[:-1], _build_big_road_data(simulated_history[:-1])),
                sequences_detected=temp_engine._detect_sequences(simulated_history[:-1])
            )
            
    overall_accuracy = (total_correct / total_predictions_made) * 100 if total_predictions_made > 0 else 0.0
    player_accuracy = (player_correct / total_player_bets) * 100 if total_player_bets > 0 else 0.0
    banker_accuracy = (banker_correct / total_banker_bets) * 100 if total_banker_bets > 0 else 0.0
    s6_accuracy = (s6_correct / total_s6_bets) * 100 if total_s6_bets > 0 else 0.0

    return {
        "overall_accuracy": overall_accuracy,
        "player_accuracy": player_accuracy,
        "banker_accuracy": banker_accuracy,
        "s6_accuracy": s6_accuracy,
        "total_bets": total_predictions_made
    }


# --- Helper to build Big Road data ---
def _build_big_road_data(history):
    """
    Builds the Big Road representation from the history.
    Each column is a list of outcomes in that column.
    A column starts with a new outcome (P after B, B after P).
    Ties are attached to the previous P/B/S6.
    
    Example history: [{'main_outcome': 'B', 'ties': 0, 'is_any_natural': False}, ...]
    Output: [[('B', 0, False), ('B', 0, False)], [('P', 1, False)], ...]
    """
    big_road = []
    
    for entry in history:
        outcome = entry['main_outcome']
        ties = entry['ties']
        is_natural = entry['is_any_natural'] # Assuming this is correctly passed/stored

        # Special handling for 'T': Ties should be attached to the LAST main outcome.
        # If the last outcome was not P, B, or S6, a standalone T does not usually
        # create a new entry in Big Road (it's often just indicated on the side).
        # For simplicity in this Big Road representation, we only attach to P/B/S6.
        if outcome == 'T':
            if big_road and big_road[-1]:
                # Get the last non-None entry in the last column
                last_valid_entry_in_last_col = None
                for i in reversed(range(len(big_road[-1]))):
                    if big_road[-1][i] is not None:
                        last_valid_entry_in_last_col = big_road[-1][i]
                        break
                
                if last_valid_entry_in_last_col and last_valid_entry_in_last_col[0] in ['P', 'B', 'S6']:
                    last_col_idx = len(big_road) - 1
                    last_row_idx = big_road[-1].index(last_valid_entry_in_last_col) # Find its index

                    old_outcome, old_ties, old_natural = big_road[last_col_idx][last_row_idx]
                    # Update the ties count for the last entry. '+1' for the current Tie.
                    big_road[last_col_idx][last_row_idx] = (old_outcome, old_ties + 1, old_natural)
                    continue # Do not add a new cell for the tie, just update count
            else:
                # If 'T' is the very first hand or no P/B/S6 before it, it doesn't appear in the main Big Road.
                continue # Skip standalone 'T' for Big Road visualization if no prior P/B/S6

        # For P, B, S6 outcomes:
        if not big_road: # First entry in the shoe
            big_road.append([(outcome, ties, is_natural)])
        else:
            # Determine the "effective" last outcome for column breaking logic (S6 acts as B)
            last_main_outcome_in_big_road = None
            if big_road[-1]: # Check if the last column is not empty
                 # Find the last actual outcome in the current last column (skipping None padding)
                for entry_in_col in reversed(big_road[-1]):
                    if entry_in_col is not None:
                        last_main_outcome_in_big_road = entry_in_col[0]
                        break
            
            effective_last_outcome = last_main_outcome_in_big_road
            if effective_last_outcome == 'S6': effective_last_outcome = 'B'
            
            effective_current_outcome = outcome
            if effective_current_outcome == 'S6': effective_current_outcome = 'B'

            if effective_current_outcome == effective_last_outcome:
                # Same effective outcome, add to current column
                # Find the first None to insert into, or append if column is full
                current_col_idx = len(big_road) - 1
                appended = False
                for r_idx in range(6): # Big Road typically 6 rows deep
                    if r_idx >= len(big_road[current_col_idx]) or big_road[current_col_idx][r_idx] is None:
                        # Ensure column isn't already 6 entries deep (or more, if rules allow longer columns)
                        if r_idx < 6: # Standard max rows for Big Road
                            big_road[current_col_idx].insert(r_idx, (outcome, ties, is_natural))
                            # Fill with None if needed for lower rows to maintain 6-row structure
                            while len(big_road[current_col_idx]) < 6:
                                big_road[current_col_idx].append(None)
                            appended = True
                            break
                if not appended: # If column is already 6 entries or full by other means, start new column (unlikely in strict Big Road)
                     big_road.append([(outcome, ties, is_natural)] + [None]*5) # Start new column, pad to 6
            else:
                # Different effective outcome, start a new column
                big_road.append([(outcome, ties, is_natural)] + [None]*5) # Start new column, pad to 6
                
    # Ensure all columns are padded to 6 rows consistently for display
    padded_big_road = []
    for col in big_road:
        # Filter out existing None before padding to ensure valid entries are first
        valid_entries = [entry for entry in col if entry is not None]
        padded_col = valid_entries + [None] * (6 - len(valid_entries))
        padded_big_road.append(padded_col)

    return padded_big_road


class OracleEngine:
    __version__ = CURRENT_ENGINE_VERSION # Class attribute for version

    def __init__(self):
        # Initialize internal learning states
        self.learning_states = {
            'player_streaks': 0,
            'banker_streaks': 0,
            'tie_count': 0,
            'player_wins_after_banker_streak': 0, # Not used in current predict_next, but can be
            'banker_wins_after_player_streak': 0, # Not used in current predict_next, but can be
            'total_predictions': 0,
            'correct_predictions': 0,
            'player_predictions': 0, # How many times AI predicted Player
            'banker_predictions': 0, # How many times AI predicted Banker
            's6_predictions': 0,     # How many times AI predicted Super6
            'player_correct': 0,
            'banker_correct': 0,
            's6_correct': 0,
            'last_outcome': None, # The actual outcome of the previous hand
            'last_prediction': None, # The prediction made for the previous hand
            'accuracy_history': [] # Store (predicted, actual) for detailed backtesting
        }
        # Keep track of detected patterns/momentum/sequences for potential advanced learning
        self.patterns_history = [] 
        self.momentum_history = []
        self.sequences_history = []

    def reset_history(self):
        """Resets all learning states and history for a new shoe."""
        # Re-initialize the object to reset all states to their defaults
        self.__init__() 

    def reset_learning_states_on_undo(self):
        """
        Resets learning states that might be directly affected by an 'undo' operation.
        This is a simpler approach; a more robust system might store snapshots of states.
        For now, it clears stats that depend on the last hand, forcing re-evaluation.
        """
        # Clear specific stats that are highly dependent on the very last hand.
        # Streaks, last outcome, last prediction are often recalculated from history.
        # For simplicity, we mostly rely on recalculating from the (now shorter) history.
        self.learning_states['last_outcome'] = None
        self.learning_states['last_prediction'] = None
        # Clearing accuracy_history might be too broad if you want to keep overall session stats.
        # For this setup, we rely on _cached_backtest_accuracy to re-evaluate from scratch.
        # It's crucial that `_cached_backtest_accuracy.clear()` is called in the Streamlit app's undo function.


    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        """
        Updates the internal learning states based on the actual outcome of the hand.
        This function should be called AFTER the actual result is recorded and the history is updated.
        It uses the patterns/momentum/sequences that were detected *before* this hand's actual outcome.
        """
        self.learning_states['total_predictions'] += 1
        self.learning_states['accuracy_history'].append((predicted_outcome, actual_outcome))

        # Update prediction counts
        if predicted_outcome == 'P': self.learning_states['player_predictions'] += 1
        elif predicted_outcome == 'B': self.learning_states['banker_predictions'] += 1
        elif predicted_outcome == 'S6': self.learning_states['s6_predictions'] += 1

        # Update correct predictions based on the AI's actual prediction
        if predicted_outcome != '?': # Only count if a specific prediction was made
            is_prediction_correct = False
            if predicted_outcome == actual_outcome:
                is_prediction_correct = True
            elif predicted_outcome == 'B' and actual_outcome == 'S6': # Banker prediction is correct if S6 wins
                is_prediction_correct = True
            # Tie is considered neutral to P/B/S6 prediction, so not a direct hit for accuracy.

            if is_prediction_correct:
                self.learning_states['correct_predictions'] += 1
                if predicted_outcome == 'P': self.learning_states['player_correct'] += 1
                elif predicted_outcome == 'B': self.learning_states['banker_correct'] += 1
                elif predicted_outcome == 'S6': self.learning_states['s6_correct'] += 1

        # Update last outcome/prediction
        self.learning_states['last_outcome'] = actual_outcome
        self.learning_states['last_prediction'] = predicted_outcome

        # Store detected patterns/momentum/sequences for later analysis or re-learning
        self.patterns_history.append(patterns_detected)
        self.momentum_history.append(momentum_detected)
        self.sequences_history.append(sequences_detected)

    def detect_patterns(self, history, big_road_data):
        """
        Detects common Baccarat patterns (e.g., streaks, choppies, dragons).
        Returns a dictionary of detected patterns and their strengths/presence.
        """
        patterns = {
            'player_streak_length': 0,
            'banker_streak_length': 0,
            'choppy_pattern': False, # Alternating PBPB or BPBP
            'dragon_pattern_player': False, # Long Player streak (e.g., >= 5)
            'dragon_pattern_banker': False, # Long Banker streak (e.g., >= 5)
            'two_out_of_three_pattern': False, # e.g., P P B P P (column lengths 2, 1, 2)
            'four_in_a_row_P': False,
            'four_in_a_row_B': False,
            'three_in_a_row_P': False,
            'three_in_a_row_B': False
        }

        if not history:
            return patterns

        # Streak detection for the very last outcome
        last_main_outcome = history[-1]['main_outcome']
        
        current_streak_outcome = last_main_outcome
        current_streak_length = 0
        for i in reversed(range(len(history))):
            # Treat S6 as B for streak counting
            hist_outcome_for_streak = history[i]['main_outcome']
            if hist_outcome_for_streak == 'S6': hist_outcome_for_streak = 'B'
            
            check_outcome_for_streak = current_streak_outcome
            if check_outcome_for_streak == 'S6': check_outcome_for_streak = 'B'

            if hist_outcome_for_streak == check_outcome_for_streak:
                current_streak_length += 1
            else:
                break
        
        if current_streak_outcome == 'P':
            patterns['player_streak_length'] = current_streak_length
        elif current_streak_outcome == 'B' or current_streak_outcome == 'S6': # S6 contributes to Banker streak
            patterns['banker_streak_length'] = current_streak_length

        # Check for Choppy pattern (P B P B...)
        if len(history) >= 4:
            last_four_main_outcomes = [h['main_outcome'] for h in history[-4:]]
            # Normalize S6 to B for pattern checking
            normalized_last_four = ['B' if o == 'S6' else o for o in last_four_main_outcomes]
            
            if (normalized_last_four == ['P', 'B', 'P', 'B'] or \
                normalized_last_four == ['B', 'P', 'B', 'P']):
                patterns['choppy_pattern'] = True

        # Check for Dragon patterns (long streaks, e.g., 5+)
        if patterns['player_streak_length'] >= 5:
            patterns['dragon_pattern_player'] = True
        if patterns['banker_streak_length'] >= 5:
            patterns['dragon_pattern_banker'] = True

        # Check for N-in-a-row (e.g., three/four in a row)
        if patterns['player_streak_length'] >= 3:
            patterns['three_in_a_row_P'] = True
        if patterns['player_streak_length'] >= 4:
            patterns['four_in_a_row_P'] = True
        if patterns['banker_streak_length'] >= 3:
            patterns['three_in_a_row_B'] = True
        if patterns['banker_streak_length'] >= 4:
            patterns['four_in_a_row_B'] = True
                
        # "Two out of three" pattern from Big Road column lengths
        if big_road_data and len(big_road_data) >= 3:
            # Get lengths of the last few *non-empty* columns
            col_lengths = [len([item for item in col if item is not None]) for col in big_road_data]
            
            if len(col_lengths) >= 3:
                # Example: checking for a 2-1-2 pattern in column lengths
                # i.e., last column length is 2, column before that is 1, column before that is 2
                if col_lengths[-1] == 2 and col_lengths[-2] == 1 and col_lengths[-3] == 2:
                    patterns['two_out_of_three_pattern'] = True
                # You might add other common Big Road patterns here (e.g., single/double row patterns)

        return patterns

    def detect_momentum(self, history, big_road_data):
        """
        Detects momentum in the game (e.g., recent win/loss trends, swings).
        Returns a dictionary of momentum indicators.
        """
        momentum = {
            'recent_player_dominance': 0, # Count of P in last N hands
            'recent_banker_dominance': 0, # Count of B/S6 in last N hands
            'swing_detected': False, # Rapid change in dominant outcome
            'volatility_score': 0.0 # How often the outcome changes (0 to 1)
        }

        if not history:
            return momentum

        last_n_hands = 10 # Look at last 10 hands for recent dominance and volatility
        recent_outcomes = [h['main_outcome'] for h in history[-last_n_hands:]]

        p_count = recent_outcomes.count('P')
        b_s6_count = recent_outcomes.count('B') + recent_outcomes.count('S6') # S6 adds to Banker dominance

        momentum['recent_player_dominance'] = p_count
        momentum['recent_banker_dominance'] = b_s6_count

        # Simple volatility: number of outcome changes (excluding ties)
        changes = 0
        filtered_outcomes = [o for o in recent_outcomes if o != 'T'] # Ignore ties for volatility
        if len(filtered_outcomes) > 1:
            for i in range(1, len(filtered_outcomes)):
                prev_outcome = filtered_outcomes[i-1]
                curr_outcome = filtered_outcomes[i]
                
                if prev_outcome == 'S6': prev_outcome = 'B'
                if curr_outcome == 'S6': curr_outcome = 'B'

                if prev_outcome != curr_outcome:
                    changes += 1
            momentum['volatility_score'] = changes / (len(filtered_outcomes) - 1)
        else:
            momentum['volatility_score'] = 0.0

        # Swing detection (e.g., if P was dominant, now B is dominant, using a larger window)
        if len(history) >= 20: # Need enough history for meaningful swing detection
            first_half_outcomes = [h['main_outcome'] for h in history[-20:-10]] # e.g. previous 10 hands (before most recent 10)
            second_half_outcomes = [h['main_outcome'] for h in history[-10:]] # last 10 hands

            p1 = first_half_outcomes.count('P')
            b1 = first_half_outcomes.count('B') + first_half_outcomes.count('S6')
            p2 = second_half_outcomes.count('P')
            b2 = second_half_outcomes.count('B') + second_half_outcomes.count('S6')

            # Detect if dominance flipped significantly (e.g., diff > 2)
            if (p1 > b1 + 2 and b2 > p2 + 2) or (b1 > p1 + 2 and p2 > b2 + 2):
                momentum['swing_detected'] = True

        return momentum

    def _detect_sequences(self, history):
        """
        Detects specific short sequences of outcomes.
        Returns a dictionary of detected sequences.
        """
        sequences = {
            'alternating_p_b': False, # P, B, P, B... or B, P, B, P...
            'double_p_double_b': False, # P, P, B, B... or B, B, P, P...
            'triple_p_triple_b': False, # P P P B B B...
            'last_three_pbb': False, # P B B
            'last_three_bpp': False # B P P
        }

        if len(history) >= 4:
            # Check for PBPB or BPBP (normalized for S6)
            last_four_outcomes_main = [h['main_outcome'] for h in history[-4:]]
            normalized_last_four = ['B' if o == 'S6' else o for o in last_four_outcomes_main]
            
            if (normalized_last_four == ['P', 'B', 'P', 'B'] or \
                normalized_last_four == ['B', 'P', 'B', 'P']):
                sequences['alternating_p_b'] = True

            # Check for PPBB or BBPP (normalized for S6)
            if (normalized_last_four[0:2] == ['P', 'P'] and normalized_last_four[2:4] == ['B', 'B']) or \
               (normalized_last_four[0:2] == ['B', 'B'] and normalized_last_four[2:4] == ['P', 'P']):
                sequences['double_p_double_b'] = True
        
        if len(history) >= 6:
            last_six_outcomes_main = [h['main_outcome'] for h in history[-6:]]
            normalized_last_six = ['B' if o == 'S6' else o for o in last_six_outcomes_main]
            if (normalized_last_six[0:3] == ['P', 'P', 'P'] and normalized_last_six[3:6] == ['B', 'B', 'B']) or \
               (normalized_last_six[0:3] == ['B', 'B', 'B'] and normalized_last_six[3:6] == ['P', 'P', 'P']):
                sequences['triple_p_triple_b'] = True


        if len(history) >= 3:
            last_three_outcomes_main = [h['main_outcome'] for h in history[-3:]]
            # Use raw outcomes for these specific sequences
            if last_three_outcomes_main == ['P', 'B', 'B']:
                sequences['last_three_pbb'] = True
            if last_three_outcomes_main == ['B', 'P', 'P']:
                sequences['last_three_bpp'] = True

        return sequences

    def predict_next(self, current_live_drawdown, current_big_road_data):
        """
        Predicts the next outcome (P, B, S6, T) and provides a recommendation based on
        current history, patterns, momentum, and drawdown.
        Returns a dictionary with 'prediction', 'recommendation', 'risk', 'overall_confidence'.
        """
        history_len = len(st.session_state.history) # Always use the session state history

        if history_len < 3: # Need at least 3 hands to start seeing basic patterns for a reliable prediction
            return {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Low History', 'overall_confidence': 0}

        # Analyze current patterns, momentum, and sequences based on existing history
        patterns = self.detect_patterns(st.session_state.history, current_big_road_data)
        momentum = self.detect_momentum(st.session_state.history, current_big_road_data)
        sequences = self._detect_sequences(st.session_state.history)

        prediction = '?'
        confidence = 0
        recommendation = 'Avoid ❌'
        risk = 'Normal'

        last_outcome = st.session_state.history[-1]['main_outcome']
        # second_last_outcome = st.session_state.history[-2]['main_outcome'] # Not directly used in these rules, but can be

        # --- Rule-Based Prediction Logic (Prioritized) ---

        # 1. Strong Streak Following (High Confidence)
        if patterns['player_streak_length'] >= 3:
            prediction = 'P'
            confidence = min(patterns['player_streak_length'] * 15, 80) # Max 80% for streaks
            risk = 'Low' if patterns['player_streak_length'] >= 4 else 'Normal'
            recommendation = 'Play ✅'
        elif patterns['banker_streak_length'] >= 3:
            prediction = 'B'
            confidence = min(patterns['banker_streak_length'] * 15, 80) # Max 80% for streaks
            risk = 'Low' if patterns['banker_streak_length'] >= 4 else 'Normal'
            recommendation = 'Play ✅'
        
        # 2. Choppy/Alternating Pattern (Medium Confidence)
        # Only if no strong streak prediction or confidence is low
        if patterns['choppy_pattern'] and confidence < 60: 
            if last_outcome == 'P':
                prediction = 'B'
            elif last_outcome == 'B' or last_outcome == 'S6':
                prediction = 'P'
            else: # If last was Tie, look further back for the pattern
                # This needs a more sophisticated check for alternating with ties in between
                pass 
            if prediction != '?':
                confidence = max(confidence, 55) # Set confidence if this rule applies
                risk = 'Normal'
                recommendation = 'Play ✅'

        # 3. Two out of three pattern (Medium Confidence) - from Big Road structure
        # This implies a break of a single entry in a sequence of doubles
        if patterns['two_out_of_three_pattern'] and confidence < 50:
            # Need to determine which side is implied by the "two out of three"
            # Example: if Big Road is P, B, B, P, P (col lengths 1, 2, 2)
            # This is hard to derive solely from `patterns['two_out_of_three_pattern']` bool.
            # A more specific check on `big_road_data` itself would be needed here.
            # For now, let's keep this as a placeholder or remove if not implemented deeply.
            pass # Implement specific logic based on big_road_data structure if desired

        # 4. Momentum (Lower-Medium Confidence)
        # Only apply if no strong pattern prediction has overridden it
        if confidence < 40 and history_len >= 10:
            if momentum['recent_player_dominance'] > momentum['recent_banker_dominance'] + 3:
                prediction = 'P'
                confidence = max(confidence, 35)
                risk = 'Normal'
                recommendation = 'Play ✅'
            elif momentum['recent_banker_dominance'] > momentum['recent_player_dominance'] + 3:
                prediction = 'B'
                confidence = max(confidence, 35)
                risk = 'Normal'
                recommendation = 'Play ✅'

        # --- Super6 Specific Prediction Logic (Highly Speculative) ---
        # Super6 is usually predicted based on specific card counts or very rare road patterns.
        # Without card data, this is purely heuristic.
        # Only consider S6 if already predicting Banker with good confidence, and some weak S6 indicator
        if prediction == 'B' and confidence > 60: # If we are already strongly predicting Banker
            s6_chance = False
            # Heuristic 1: If Banker has won by 6 recently (but history doesn't track margin)
            # Heuristic 2: If there's been an S6 in the last 10-20 hands, indicating it's "in play"
            recent_s6_count = sum(1 for h in st.session_state.history[-20:] if h['main_outcome'] == 'S6')
            if recent_s6_count >= 1: # At least one S6 in recent memory
                s6_chance = True
            
            # Heuristic 3: If Banker streak is long (e.g., >= 4)
            if patterns['banker_streak_length'] >= 4:
                s6_chance = True

            if s6_chance:
                # If conditions align, boost Banker prediction to S6
                prediction = 'S6'
                confidence = min(confidence + 10, 95) # Boost confidence slightly
                risk = 'High' # S6 is inherently high risk due to odds
                recommendation = 'Play ✅' # Only recommend if confidence is very high for S6


        # --- Adjustments based on Drawdown ---
        # If drawdown is high, become more conservative or avoid.
        if current_live_drawdown >= 2: # Starting to hit drawdown, reduce confidence for "Play"
            if current_live_drawdown >= 3 and recommendation == 'Play ✅': # Serious drawdown, strongly consider avoiding
                recommendation = 'Avoid ❌'
                risk = 'Critical'
                confidence = max(0, confidence - 20) # Significantly reduce confidence
                if confidence < 50: # If confidence drops too low due to drawdown, revert prediction to '?'
                    prediction = '?'
        
        # --- Final Recommendation and Confidence Thresholds ---
        if confidence < 30: # General threshold for recommending a specific bet
            prediction = '?'
            recommendation = 'Avoid ❌'
            risk = 'Uncertainty'
            confidence = 0 # Reset confidence if avoiding

        # Fallback if prediction is still '?'
        if prediction == '?':
            # Simple alternating or follow the trend, but with low confidence and avoid recommendation
            if history_len >= 1:
                if last_outcome == 'P': prediction = 'B' 
                elif last_outcome == 'B' or last_outcome == 'S6': prediction = 'P' 
                elif last_outcome == 'T' and history_len >= 2: 
                     second_last_main_outcome_before_tie = st.session_state.history[-2]['main_outcome']
                     if second_last_main_outcome_before_tie == 'P': prediction = 'B'
                     elif second_last_main_outcome_before_tie == 'B' or second_last_main_outcome_before_tie == 'S6': prediction = 'P'
                else: 
                    prediction = 'P' # Arbitrary default for very short/unclear history
            
            # Even with fallback, if no strong signal, recommendation is still Avoid.
            recommendation = 'Avoid ❌'
            risk = 'Uncertainty'
            confidence = 0

        # Debugging output (can be logged or stored in a debug_log session state)
        # print(f"Patterns: {patterns}")
        # print(f"Momentum: {momentum}")
        # print(f"Sequences: {sequences}")
        # print(f"Prediction: {prediction}, Recommendation: {recommendation}, Confidence: {confidence:.1f}, Risk: {risk}")

        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'overall_confidence': confidence
        }

    def get_tie_opportunity_analysis(self, history):
        """
        Analyzes history for potential Tie opportunities.
        Returns a dict with 'prediction', 'confidence', 'reason'.
        """
        if len(history) < 5: # Need a minimum number of hands for any meaningful analysis
            return {'prediction': '?', 'confidence': 0, 'reason': 'ประวัติไม่เพียงพอ'}

        tie_count_recent = sum(1 for h in history[-10:] if h['main_outcome'] == 'T') # Count Ties in last 10 hands
        total_hands_recent = len(history[-10:])
        
        # Heuristic 1: Higher than average tie frequency recently
        # Average Baccarat tie rate is around 9.5%
        if total_hands_recent > 0 and (tie_count_recent / total_hands_recent) > 0.12: # If > 12% in recent hands
            confidence = min(tie_count_recent * 15, 80) # Scale confidence based on tie count
            return {'prediction': 'T', 'confidence': confidence, 'reason': f'พบ Tie บ่อยขึ้นในช่วง {total_hands_recent} ตาหลัง ({tie_count_recent} ครั้ง)'}
        
        # Heuristic 2: Tie after specific sequences (e.g., P, B, P followed by Tie)
        # This is more speculative and harder to define without a lot of historical data.
        if len(history) >= 3:
            last_three_main = [h['main_outcome'] for h in history[-3:]]
            # If the last three hands were P, B, P or B, P, B and no tie happened in this sequence
            if (last_three_main == ['P', 'B', 'P'] or last_three_main == ['B', 'P', 'B']):
                return {'prediction': 'T', 'confidence': 40, 'reason': 'รูปแบบ P-B-P หรือ B-P-B อาจนำไปสู่ Tie'}

        return {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่พบโอกาส Tie ที่ชัดเจน'}


# --- Asynchronous function for Gemini API calls ---
async def get_gemini_analysis(current_history):
    """
    Sends the current game history to Gemini for a deeper analysis and pattern detection.
    This is an asynchronous function to avoid blocking the UI.
    """
    global GEMINI_MODEL # Access the global GEMINI_MODEL

    if GEMINI_MODEL is None:
        return "⚠️ Gemini AI ไม่พร้อมใช้งาน: API Key ไม่ถูกต้องหรือไม่ได้รับการตั้งค่า."

    # Convert history to a more human-readable format for the LLM
    formatted_history = []
    for i, h in enumerate(current_history):
        outcome_str = h['main_outcome']
        if h['ties'] > 0:
            outcome_str += f" (จำนวน Tie: {h['ties']})" # Clarify 'ties' as number of ties
        if h['is_any_natural']: # Assuming this field is populated
            outcome_str += " (Natural)"
        formatted_history.append(f"ตาที่ {i+1}: {outcome_str}")

    history_text = "\n".join(formatted_history)
    
    prompt = f"""
    คุณคือผู้เชี่ยวชาญด้าน Baccarat AI โปรดวิเคราะห์ประวัติการเล่น Baccarat ต่อไปนี้อย่างละเอียด:

    ประวัติการเล่น (แต่ละตาคือผลลัพธ์หลัก, จำนวน Tie หากมี, และมี Natural หรือไม่):
    {history_text}

    จากประวัติข้างต้น:
    1.  **รูปแบบ (Patterns) ที่สังเกตเห็นได้:** ระบุและอธิบายรูปแบบที่ชัดเจน (เช่น มังกร (Dragon), ปิงปอง (Ping Pong/Alternating), คู่ (Pairs), คี่ (Odds), สามตัวตัด, สี่ตัวตัด, หรือรูปแบบเฉพาะที่เห็นใน Big Road)
    2.  **แนวโน้ม (Momentum) หรือกระแสของเกม:** วิเคราะห์ว่ากระแสกำลังไปทางไหน (เช่น Player มาแรง, Banker กำลังกลับมา, เกมมีการเปลี่ยนแปลงบ่อย)
    3.  **คำแนะนำสำหรับการลงเดิมพันในตาถัดไป:**
        * ระบุ 'Player', 'Banker', 'Tie', 'Super6' หรือ 'รอ (Avoid)'
        * ให้เหตุผลประกอบที่ชัดเจนและมีเหตุผลจากข้อมูลที่ให้มา
        * ระบุระดับความมั่นใจเป็นเปอร์เซ็นต์ (Confidence Level %)
        * ระบุระดับความเสี่ยง (Risk Level: ต่ำ, ปานกลาง, สูง, วิกฤต)
    4.  **การวิเคราะห์ Drawdown (หากมี):** หากมีช่วงที่แพ้ติดต่อกัน (เช่น 3 ครั้งขึ้นไป) โปรดวิเคราะห์ว่ารูปแบบเดิมพันใดที่อาจทำให้เกิด Drawdown และแนะนำการปรับกลยุทธ์เพื่อลดความเสี่ยง
    5.  **สรุปความเสี่ยงโดยรวมของสถานการณ์ปัจจุบัน:**
        
    ตอบกลับเป็นภาษาไทย ในรูปแบบข้อความที่อ่านง่าย ใช้หัวข้อและข้อความที่เป็นธรรมชาติ ไม่ต้องใส่ JSON block.
    """

    try:
        # It's good practice to start a new chat history for each analysis request
        # to ensure the model focuses only on the current prompt.
        chat = GEMINI_MODEL.start_chat(history=[])
        response = await chat.send_message_async(prompt)
        return response.text
    except Exception as e:
        # More specific error handling if possible (e.g., rate limits, invalid input)
        return f"❌ เกิดข้อผิดพลาดในการเรียกใช้ Gemini API: {e}. โปรดตรวจสอบ API Key, โควต้า, หรือการเชื่อมต่ออินเทอร์เน็ต."
