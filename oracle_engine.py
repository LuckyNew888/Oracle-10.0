import pandas as pd
import numpy as np
import google.generativeai as genai
import os
import json
import streamlit as st

# Define the current expected version of the OracleEngine
CURRENT_ENGINE_VERSION = "1.12" 

# --- Gemini API Key Configuration ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # print("Gemini API key configured from Streamlit secrets.") # Suppress for cleaner output
    elif "GEMINI_API_KEY" in os.environ:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        # print("Gemini API key configured from environment variables.") # Suppress for cleaner output
    else:
        genai.configure(api_key="DUMMY_KEY_FOR_TESTING_ONLY")
        st.warning("⚠️ Gemini API key not found. Gemini AI analysis will not work.")
except Exception as e:
    st.error(f"Error configuring Gemini API key: {e}")
    genai.configure(api_key="DUMMY_KEY_FOR_TESTING_ONLY_ERROR")


# --- Gemini Model Initialization ---
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" 
GEMINI_MODEL = None
try:
    if genai.get_default_configured_api_key() and genai.get_default_configured_api_key() != "DUMMY_KEY_FOR_TESTING_ONLY":
        GEMINI_MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
        # print(f"Gemini model '{GEMINI_MODEL_NAME}' initialized.") # Suppress for cleaner output
    else:
        # print("Gemini model not initialized: API key not properly configured or is a dummy key.") # Suppress for cleaner output
        pass
except Exception as e:
    # print(f"Could not initialize Gemini model '{GEMINI_MODEL_NAME}': {e}") # Suppress for cleaner output
    GEMINI_MODEL = None 


# --- Cached function for backtest accuracy ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def _cached_backtest_accuracy(history_data_for_hash): # Renamed to clarify its purpose in caching
    """
    Calculates historical prediction accuracy based on a given history.
    This function should simulate predictions over the history to evaluate accuracy.
    It takes a hashable representation of history (e.g., tuple of tuples)
    """
    if not history_data_for_hash or len(history_data_for_hash) < 3:
        return {"overall_accuracy": 0.0, "player_accuracy": 0.0, "banker_accuracy": 0.0, "s6_accuracy": 0.0, "total_bets": 0}

    # Create a temporary engine instance for backtesting to not mess with current session's engine state
    # This is crucial for avoiding the UnhashableParamError
    temp_engine = OracleEngine() 

    total_correct = 0
    total_player_bets = 0
    player_correct = 0
    total_banker_bets = 0
    banker_correct = 0
    total_s6_bets = 0
    s6_correct = 0
    total_predictions_made = 0

    simulated_history = []
    for i, current_hand_data in enumerate(history_data_for_hash):
        if i < 2: # Need at least 2 hands to make a prediction (3rd hand)
            simulated_history.append(current_hand_data)
            continue

        # Build big road data up to the current hand for prediction context
        sim_big_road_data = _build_big_road_data(simulated_history)
        
        # Simulate prediction BEFORE adding the current hand's actual result
        sim_prediction_output = temp_engine.predict_next(
            current_live_drawdown=0, # Drawdown logic is complex for backtesting, assume 0 or handle separately
            current_big_road_data=sim_big_road_data,
            history_for_prediction=simulated_history # Pass the simulated history for prediction context
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
        simulated_history.append(current_hand_data)
        
        # Manually update temp_engine's learning states (a simplified version)
        if sim_predicted_side != '?': # Only if a prediction was actually made for this hand
            temp_engine._update_learning(
                predicted_outcome=sim_predicted_side,
                actual_outcome=current_hand_data['main_outcome'],
                patterns_detected={}, # Placeholder, as full detection is expensive in loop
                momentum_detected={}, # Placeholder
                sequences_detected={} # Placeholder
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
        is_natural = entry['is_any_natural'] 

        if outcome == 'T':
            if big_road and big_road[-1]:
                # Find the last actual P/B/S6 entry in the last column
                last_valid_entry_in_last_col_idx = -1
                for i in reversed(range(len(big_road[-1]))):
                    if big_road[-1][i] is not None:
                        if big_road[-1][i][0] in ['P', 'B', 'S6']: # Only attach ties to P, B, S6
                            last_valid_entry_in_last_col_idx = i
                            break
                
                if last_valid_entry_in_last_col_idx != -1:
                    old_outcome, old_ties, old_natural = big_road[-1][last_valid_entry_in_last_col_idx]
                    big_road[-1][last_valid_entry_in_last_col_idx] = (old_outcome, old_ties + 1, old_natural)
                    continue 
            else:
                continue 

        # For P, B, S6 outcomes:
        if not big_road: # First entry in the shoe
            big_road.append([(outcome, ties, is_natural)])
        else:
            last_main_outcome_in_big_road = None
            if big_road[-1]: 
                for entry_in_col in reversed(big_road[-1]):
                    if entry_in_col is not None:
                        last_main_outcome_in_big_road = entry_in_col[0]
                        break
            
            effective_last_outcome = last_main_outcome_in_big_road
            if effective_last_outcome == 'S6': effective_last_outcome = 'B'
            
            effective_current_outcome = outcome
            if effective_current_outcome == 'S6': effective_current_outcome = 'B'

            if effective_current_outcome == effective_last_outcome:
                current_col_idx = len(big_road) - 1
                appended = False
                for r_idx in range(6): 
                    if r_idx >= len(big_road[current_col_idx]) or big_road[current_col_idx][r_idx] is None:
                        if r_idx < 6: 
                            if r_idx < len(big_road[current_col_idx]) and big_road[current_col_idx][r_idx] is None:
                                big_road[current_col_idx][r_idx] = (outcome, ties, is_natural)
                            else: 
                                big_road[current_col_idx].append((outcome, ties, is_natural))
                            appended = True
                            break
                if not appended: 
                     big_road.append([(outcome, ties, is_natural)])
            else:
                big_road.append([(outcome, ties, is_natural)])
                
    # Ensure all columns are padded to 6 rows consistently for display
    padded_big_road = []
    for col in big_road:
        valid_entries = [entry for entry in col if entry is not None]
        padded_col = valid_entries + [None] * (6 - len(valid_entries))
        padded_big_road.append(padded_col)

    return padded_big_road


class OracleEngine:
    __version__ = CURRENT_ENGINE_VERSION 

    def __init__(self):
        self.learning_states = {
            'player_streaks': 0,
            'banker_streaks': 0,
            'tie_count': 0,
            'total_predictions': 0,
            'correct_predictions': 0,
            'player_predictions': 0, 
            'banker_predictions': 0, 
            's6_predictions': 0,     
            'player_correct': 0,
            'banker_correct': 0,
            's6_correct': 0,
            'last_outcome': None, 
            'last_prediction': None, 
            'accuracy_history': [] 
        }
        self.patterns_history = [] 
        self.momentum_history = []
        self.sequences_history = []

    def reset_history(self):
        """Resets all learning states and history for a new shoe."""
        self.__init__() 

    def reset_learning_states_on_undo(self):
        """
        Resets learning states that might be directly affected by an 'undo' operation.
        """
        self.learning_states['last_outcome'] = None
        self.learning_states['last_prediction'] = None

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        """
        Updates the internal learning states based on the actual outcome of the hand.
        """
        self.learning_states['total_predictions'] += 1
        self.learning_states['accuracy_history'].append((predicted_outcome, actual_outcome))

        if predicted_outcome == 'P': self.learning_states['player_predictions'] += 1
        elif predicted_outcome == 'B': self.learning_states['banker_predictions'] += 1
        elif predicted_outcome == 'S6': self.learning_states['s6_predictions'] += 1

        if predicted_outcome != '?': 
            is_prediction_correct = False
            if predicted_outcome == actual_outcome:
                is_prediction_correct = True
            elif predicted_outcome == 'B' and actual_outcome == 'S6': 
                is_prediction_correct = True

            if is_prediction_correct:
                self.learning_states['correct_predictions'] += 1
                if predicted_outcome == 'P': self.learning_states['player_correct'] += 1
                elif predicted_outcome == 'B': self.learning_states['banker_correct'] += 1
                elif predicted_outcome == 'S6': self.learning_states['s6_correct'] += 1

        self.learning_states['last_outcome'] = actual_outcome
        self.learning_states['last_prediction'] = predicted_outcome

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
            'choppy_pattern': False, 
            'dragon_pattern_player': False, 
            'dragon_pattern_banker': False, 
            'two_out_of_three_pattern': False, 
            'four_in_a_row_P': False,
            'four_in_a_row_B': False,
            'three_in_a_row_P': False,
            'three_in_a_row_B': False
        }

        if not history:
            return patterns

        last_main_outcome = history[-1]['main_outcome']
        
        current_streak_outcome = last_main_outcome
        current_streak_length = 0
        for i in reversed(range(len(history))):
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
        elif current_streak_outcome == 'B' or current_streak_outcome == 'S6': 
            patterns['banker_streak_length'] = current_streak_length

        if len(history) >= 4:
            last_four_main_outcomes = [h['main_outcome'] for h in history[-4:]]
            normalized_last_four = ['B' if o == 'S6' else o for o in last_four_main_outcomes]
            
            if (normalized_last_four == ['P', 'B', 'P', 'B'] or \
                normalized_last_four == ['B', 'P', 'B', 'P']):
                patterns['choppy_pattern'] = True

        if patterns['player_streak_length'] >= 5:
            patterns['dragon_pattern_player'] = True
        if patterns['banker_streak_length'] >= 5:
            patterns['dragon_pattern_banker'] = True

        if patterns['player_streak_length'] >= 3:
            patterns['three_in_a_row_P'] = True
        if patterns['player_streak_length'] >= 4:
            patterns['four_in_a_row_P'] = True
        if patterns['banker_streak_length'] >= 3:
            patterns['three_in_a_row_B'] = True
        if patterns['banker_streak_length'] >= 4:
            patterns['four_in_a_row_B'] = True
                
        if big_road_data and len(big_road_data) >= 3:
            col_lengths = [len([item for item in col if item is not None]) for col in big_road_data]
            
            if len(col_lengths) >= 3:
                if col_lengths[-1] == 2 and col_lengths[-2] == 1 and col_lengths[-3] == 2:
                    patterns['two_out_of_three_pattern'] = True

        return patterns

    def detect_momentum(self, history, big_road_data):
        """
        Detects momentum in the game (e.g., recent win/loss trends, swings).
        Returns a dictionary of momentum indicators.
        """
        momentum = {
            'recent_player_dominance': 0, 
            'recent_banker_dominance': 0, 
            'swing_detected': False, 
            'volatility_score': 0.0 
        }

        if not history:
            return momentum

        last_n_hands = 10 
        recent_outcomes = [h['main_outcome'] for h in history[-last_n_hands:]]

        p_count = recent_outcomes.count('P')
        b_s6_count = recent_outcomes.count('B') + recent_outcomes.count('S6') 

        momentum['recent_player_dominance'] = p_count
        momentum['recent_banker_dominance'] = b_s6_count

        changes = 0
        filtered_outcomes = [o for o in recent_outcomes if o != 'T'] 
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

        if len(history) >= 20: 
            first_half_outcomes = [h['main_outcome'] for h in history[-20:-10]] 
            second_half_outcomes = [h['main_outcome'] for h in history[-10:]] 

            p1 = first_half_outcomes.count('P')
            b1 = first_half_outcomes.count('B') + first_half_outcomes.count('S6')
            p2 = second_half_outcomes.count('P')
            b2 = second_half_outcomes.count('B') + second_half_outcomes.count('S6')

            if (p1 > b1 + 2 and b2 > p2 + 2) or (b1 > p1 + 2 and p2 > b2 + 2):
                momentum['swing_detected'] = True

        return momentum

    def _detect_sequences(self, history):
        """
        Detects specific short sequences of outcomes.
        Returns a dictionary of detected sequences.
        """
        sequences = {
            'alternating_p_b': False, 
            'double_p_double_b': False, 
            'triple_p_triple_b': False, 
            'last_three_pbb': False, 
            'last_three_bpp': False 
        }

        if len(history) >= 4:
            last_four_outcomes_main = [h['main_outcome'] for h in history[-4:]]
            normalized_last_four = ['B' if o == 'S6' else o for o in last_four_outcomes_main]
            
            if (normalized_last_four == ['P', 'B', 'P', 'B'] or \
                normalized_last_four == ['B', 'P', 'B', 'P']):
                sequences['alternating_p_b'] = True

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
            if last_three_outcomes_main == ['P', 'B', 'B']:
                sequences['last_three_pbb'] = True
            if last_three_outcomes_main == ['B', 'P', 'P']:
                sequences['last_three_bpp'] = True

        return sequences;

    def predict_next(self, current_live_drawdown, current_big_road_data, history_for_prediction=None):
        """
        Predicts the next outcome (P, B, S6, T) and provides a recommendation based on
        current history, patterns, momentum, and drawdown.
        Returns a dictionary with 'prediction', 'recommendation', 'risk', 'overall_confidence'.
        """
        history_to_use = history_for_prediction if history_for_prediction is not None else st.session_state.history
        history_len = len(history_to_use) 

        if history_len < 3: 
            return {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Low History', 'overall_confidence': 0}

        patterns = self.detect_patterns(history_to_use, current_big_road_data)
        momentum = self.detect_momentum(history_to_use, current_big_road_data)
        sequences = self._detect_sequences(history_to_use)

        prediction = '?'
        confidence = 0
        recommendation = 'Avoid ❌'
        risk = 'Normal'

        last_outcome = history_to_use[-1]['main_outcome']

        # --- Rule-Based Prediction Logic (Prioritized) ---

        # 1. Strong Streak Following (High Confidence)
        if patterns['player_streak_length'] >= 3:
            prediction = 'P'
            confidence = min(patterns['player_streak_length'] * 15, 80) 
            risk = 'Low' if patterns['player_streak_length'] >= 4 else 'Normal'
            recommendation = 'Play ✅'
        elif patterns['banker_streak_length'] >= 3:
            prediction = 'B'
            confidence = min(patterns['banker_streak_length'] * 15, 80) 
            risk = 'Low' if patterns['banker_streak_length'] >= 4 else 'Normal'
            recommendation = 'Play ✅'
        
        # 2. Choppy/Alternating Pattern (Medium Confidence)
        if patterns['choppy_pattern'] and confidence < 60: 
            if last_outcome == 'P':
                prediction = 'B'
            elif last_outcome == 'B' or last_outcome == 'S6':
                prediction = 'P'
            else: 
                pass 
            if prediction != '?':
                confidence = max(confidence, 55) 
                risk = 'Normal'
                recommendation = 'Play ✅'

        # 3. Two out of three pattern (Medium Confidence) - from Big Road structure
        if patterns['two_out_of_three_pattern'] and confidence < 50:
            pass 

        # 4. Momentum (Lower-Medium Confidence)
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
        if prediction == 'B' and confidence > 60: 
            s6_chance = False
            recent_s6_count = sum(1 for h in history_to_use[-20:] if h['main_outcome'] == 'S6')
            if recent_s6_count >= 1: 
                s6_chance = True
            
            if patterns['banker_streak_length'] >= 4:
                s6_chance = True

            if s6_chance:
                prediction = 'S6'
                confidence = min(confidence + 10, 95) 
                risk = 'High' 
                recommendation = 'Play ✅' 


        # --- Adjustments based on Drawdown ---
        if current_live_drawdown >= 2: 
            if current_live_drawdown >= 3 and recommendation == 'Play ✅': 
                recommendation = 'Avoid ❌'
                risk = 'Critical'
                confidence = max(0, confidence - 20) 
                if confidence < 50: 
                    prediction = '?'
        
        # --- Final Recommendation and Confidence Thresholds ---
        if confidence < 30: 
            prediction = '?'
            recommendation = 'Avoid ❌'
            risk = 'Uncertainty'
            confidence = 0 

        if prediction == '?':
            if history_len >= 1:
                if last_outcome == 'P': prediction = 'B' 
                elif last_outcome == 'B' or last_outcome == 'S6': prediction = 'P' 
                elif last_outcome == 'T' and history_len >= 2: 
                     second_last_main_outcome_before_tie = history_to_use[-2]['main_outcome']
                     if second_last_main_outcome_before_tie == 'P': prediction = 'B'
                     elif second_last_main_outcome_before_tie == 'B' or second_last_main_outcome_before_tie == 'S6': prediction = 'P'
                else: 
                    prediction = 'P' 
            
            recommendation = 'Avoid ❌'
            risk = 'Uncertainty'
            confidence = 0

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
        if len(history) < 5: 
            return {'prediction': '?', 'confidence': 0, 'reason': 'ประวัติไม่เพียงพอ'}

        tie_count_recent = sum(1 for h in history[-10:] if h['main_outcome'] == 'T') 
        total_hands_recent = len(history[-10:])
        
        if total_hands_recent > 0 and (tie_count_recent / total_hands_recent) > 0.12: 
            confidence = min(tie_count_recent * 15, 80) 
            return {'prediction': 'T', 'confidence': confidence, 'reason': f'พบ Tie บ่อยขึ้นในช่วง {total_hands_recent} ตาหลัง ({tie_count_recent} ครั้ง)'}
        
        if len(history) >= 3:
            last_three_main = [h['main_outcome'] for h in history[-3:]]
            if (last_three_main == ['P', 'B', 'P'] or last_three_main == ['B', 'P', 'B']):
                return {'prediction': 'T', 'confidence': 40, 'reason': 'รูปแบบ P-B-P หรือ B-P-B อาจนำไปสู่ Tie'}

        return {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่พบโอกาส Tie ที่ชัดเจน'}


# --- Asynchronous function for Gemini API calls ---
async def get_gemini_analysis(current_history):
    """
    Sends the current game history to Gemini for a deeper analysis and pattern detection.
    This is an asynchronous function to avoid blocking the UI.
    """
    global GEMINI_MODEL 

    if GEMINI_MODEL is None:
        return "⚠️ Gemini AI ไม่พร้อมใช้งาน: API Key ไม่ถูกต้องหรือไม่ได้รับการตั้งค่า."

    formatted_history = []
    for i, h in enumerate(current_history):
        outcome_str = h['main_outcome']
        if h['ties'] > 0:
            outcome_str += f" (จำนวน Tie: {h['ties']})" 
        if h['is_any_natural']: 
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
        chat = GEMINI_MODEL.start_chat(history=[])
        response = await chat.send_message_async(prompt)
        return response.text
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการเรียกใช้ Gemini API: {e}. โปรดตรวจสอบ API Key, โควต้า, หรือการเชื่อมต่ออินเทอร์เน็ต."
