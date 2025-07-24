import streamlit as st
import pandas as pd
import math
import json # Import json for parsing structured responses from LLM
import asyncio # For running async functions

# Import OracleEngine and helper functions (note: _cached_backtest_accuracy and _build_big_road_data are global)
# Make sure oracle_engine.py is in the same directory or accessible via PYTHONPATH
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data, get_gemini_analysis

# Define the current expected version of the OracleEngine
# Increment this value whenever OracleEngine.py has significant structural changes
# that might cause caching issues.
CURRENT_ENGINE_VERSION = "1.12" # This must match OracleEngine.__version__ in oracle_engine.py

# --- Streamlit App Setup and CSS ---
st.set_page_config(page_title="🔮 Oracle AI v3.0", layout="centered") 

st.markdown("""
    <style>
    /* CSS for the main title */
    .custom-title {
        font-family: 'Georgia', serif;
        font-size: 2rem; /* Adjusted main title size */
        text-align: center;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    /* New style for version text */
    .version-text {
        font-size: 0.6em; /* Smaller relative to parent */
        vertical-align: super; /* Raise it slightly */
        opacity: 0.7; /* Make it a bit less prominent */
        font-weight: normal; /* Less bold for version */
    }
    /* Reduce overall spacing of Streamlit elements */
    .stApp > header {
        display: none;
    }
    .stApp {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .st-emotion-cache-z5fcl4 {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* CSS for labels of st.number_input, st.selectbox, st.text_input */
    .stNumberInput > label, .stSelectbox > label, .stTextInput > label {
        font-size: 0.95rem;
        font-weight: bold;
        margin-bottom: 0.1rem;
    }
    /* CSS for numbers in st.number_input fields */
    .stNumberInput div[data-baseweb="input"] input {
        font-size: 0.95rem;
    }
    /* CSS for h4 headings to be smaller and more compact */
    h4 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 1.25rem;
    }
    /* CSS for prediction result (larger) */
    .prediction-text {
        font-size: 2rem;
        font-weight: bold;
        color: #4CAF50; /* Default green, will be overridden by specific classes */
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .prediction-text.player {
        color: #007bff; /* Blue for Player */
    }
    .prediction-text.banker {
        color: #dc3545; /* Red for Banker */
    }
    .prediction-text.super6 {
        color: #FF8C00; /* Orange for Super6 */
    }
    .prediction-text.no-prediction {
        color: #999; /* Grey for no prediction */
    }

    .tie-opportunity-text {
        font-size: 1.5rem; /* Slightly smaller than main prediction */
        font-weight: bold;
        color: #28a745; /* Green for Tie */
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .tie-opportunity-text.no-recommendation {
        color: #999; /* Grey for no Tie recommendation */
    }


    /* Reduce button margin */
    div.stButton > button {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }
    /* Reduce st.columns margin */
    div.stColumns > div {
        padding-top: 0.1rem;
        padding-bottom: 0.1rem;
    }
    /* Reduce margin of info/warning boxes */
    .stAlert {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* --- Big Road Specific CSS --- */
    .big-road-container {
        display: flex;
        overflow-x: auto;
        padding: 5px; /* Adjusted padding */
        background-color: #1a1a1a;
        border-radius: 8px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        /* Calculate min-height based on 6 rows of 24px cells + 5px top/bottom padding */
        min-height: calc(6 * 24px + 10px); 
        align-items: flex-start;
        border: 1px solid #333;
    }

    .big-road-column {
        display: flex;
        flex-direction: column;
        min-width: 26px;
        margin-right: 1px;
    }

    .big-road-cell {
        width: 24px;
        height: 24px;
        display: flex;
        justify-content: center;
        align-items: center;
        position: relative;
        margin-bottom: 0px; /* Adjusted margin-bottom to be flush */
        box-sizing: border-box;
    }

    .big-road-circle {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.6em;
        font-weight: bold;
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
        box-sizing: border-box;
        box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.4);
    }

    .player-circle {
        background-color: #007bff;
    }

    .banker-circle {
        background-color: #dc3545;
    }
    /* New CSS for Tie circle if you want 'T' inside */
    .tie-circle {
        background-color: #28a745; /* Green for Tie */
    }

    .tie-oval {
        position: absolute;
        top: -4px;
        right: -4px;
        background-color: #28a745;
        color: white;
        font-size: 0.55em;
        font-weight: bold;
        padding: 0px 3px;
        border-radius: 6px;
        line-height: 1;
        z-index: 3;
        border: 1px solid rgba(255,255,255,0.3);
        box-shadow: 0px 0px 2px rgba(0, 0, 0, 0.5);
    }

    .natural-indicator {
        position: absolute;
        bottom: 0px;
        right: 0px;
        font-size: 0.55em;
        color: #FFD700;
        font-weight: bold;
        line-height: 1;
        z-index: 2;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<div class="custom-title">🔮 Oracle AI <span class="version-text">v3.0</span></div>', unsafe_allow_html=True) # Updated display title with smaller version text

# --- OracleEngine Caching ---
@st.cache_resource(ttl=None)
def get_oracle_engine_cached(): # Renamed to avoid conflict with OracleEngine class name
    return OracleEngine()


# --- Session State Initialization (Consolidated for robustness) ---
# FIX: Consolidated all session state initialization into one block at the beginning
if "history" not in st.session_state:
    st.session_state.history = []
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []
if "last_prediction_data" not in st.session_state or st.session_state.last_prediction_data is None:
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
if "live_drawdown" not in st.session_state:
    st.session_state.live_drawdown = 0
if "gemini_analysis_result" not in st.session_state:
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
if "tie_opportunity_data" not in st.session_state:
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'}
if "hands_since_last_gemini_analysis" not in st.session_state:
    st.session_state.hands_since_last_gemini_analysis = 0
if "gemini_continuous_analysis_mode" not in st.session_state:
    st.session_state.gemini_continuous_analysis_mode = False
# FIX: Ensure debug_log is initialized first before any appends
if "debug_log" not in st.session_state: # Moved this up for guaranteed initialization
    st.session_state.debug_log = []

# Initialize engine after all basic session states
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = get_oracle_engine_cached()


# --- Robust Cache compatibility check using __version__ ---
# This ensures that if a cached OracleEngine instance is loaded from a previous version,
# it gets re-initialized.
reinitialize_engine = False
if not hasattr(st.session_state.oracle_engine, '__version__') or \
   st.session_state.oracle_engine.__version__ != CURRENT_ENGINE_VERSION:
    reinitialize_engine = True

if reinitialize_engine:
    st.warning(f"⚠️ ตรวจพบโครงสร้าง AI เวอร์ชันเก่า (v{getattr(st.session_state.oracle_engine, '__version__', 'Unknown')}) ไม่เข้ากันกับเวอร์ชันปัจจุบัน (v{CURRENT_ENGINE_VERSION})! ระบบกำลังรีเซ็ตข้อมูลเพื่อความถูกต้อง.")
    st.session_state.oracle_engine = OracleEngine() # Create a new instance
    st.session_state.oracle_engine.reset_history()
    # Explicitly reset all relevant session state variables when engine is reinitialized
    st.session_state.history = []
    st.session_state.bet_log = []
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'}
    st.session_state.hands_since_last_gemini_analysis = 0
    st.session_state.gemini_continuous_analysis_mode = False
    st.session_state.debug_log = [] # Clear debug log on reinit


# --- Callback Functions for History and Betting Management ---
def remove_last_from_history():
    st.session_state.debug_log.append(f"--- UNDO initiated ---")
    st.session_state.debug_log.append(f"  UNDO: History length before pop: {len(st.session_state.history)}")
    
    if not st.session_state.bet_log:
        st.session_state.debug_log.append(f"  UNDO: No bet log entries. Full reset.")
        reset_all_history() # If no bet log, perform full reset
        return # Exit the function

    # Retrieve last bet entry from bet_log
    last_bet_entry = st.session_state.bet_log.pop()
    st.session_state.debug_log.append(f"  UNDO: Bet log entry removed: {last_bet_entry}")
    
    # Revert live_drawdown to the state BEFORE the removed hand
    if "DrawdownBefore" in last_bet_entry:
        st.session_state.live_drawdown = last_bet_entry["DrawdownBefore"]
        st.session_state.debug_log.append(f"  UNDO: Drawdown reverted to {st.session_state.live_drawdown}.")
    else:
        st.session_state.debug_log.append(f"  UNDO: Drawdown reset to 0 (DrawdownBefore not found).")
        st.session_state.live_drawdown = 0 # Fallback

    # Revert history based on how it was recorded (main_outcome or tie_increment)
    if st.session_state.history:
        if "history_action" in last_bet_entry and last_bet_entry["history_action"] == "tie_increment":
            # If the last action was incrementing a tie, decrement the tie count on the *last* history entry
            if st.session_state.history[-1]['ties'] > 0:
                st.session_state.history[-1]['ties'] -= 1
                st.session_state.debug_log.append(f"  UNDO: Decremented tie count on last history entry. New ties: {st.session_state.history[-1]['ties']}")
            else: # Should not happen if history_action was accurate, but for safety
                st.session_state.debug_log.append(f"  UNDO: Tie increment action but no ties to decrement. Popping last anyway.")
                st.session_state.history.pop() # Fallback to pop if tie count already 0
        else: # Default: pop the last history entry (for P, B, S6, or standalone T)
            st.session_state.history.pop()
            st.session_state.debug_log.append(f"  UNDO: Popped last history entry. New length: {len(st.session_state.history)}")
    else:
        st.session_state.debug_log.append(f"  UNDO: History already empty.")


    if '_cached_backtest_accuracy' in globals() and callable(globals()['_cached_backtest_accuracy']):
        _cached_backtest_accuracy.clear() 
    st.session_state.oracle_engine.reset_learning_states_on_undo() # This should affect stats, not history structure
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'}
    st.session_state.hands_since_last_gemini_analysis = 0
    st.session_state.gemini_continuous_analysis_mode = False # Ensure continuous mode is off
    st.session_state.debug_log.append(f"--- UNDO finished ---")
    st.rerun() # Force rerun to refresh UI

def reset_all_history(): # This is now "Start New Shoe"
    st.session_state.history = []
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history() # Resets all learning states
    if '_cached_backtest_accuracy' in globals() and callable(globals()['_cached_backtest_accuracy']):
        _cached_backtest_accuracy.clear()
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0 # Reset live_drawdown on new shoe
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini" # Reset Gemini analysis
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'} # Reset Tie analysis
    st.session_state.hands_since_last_gemini_analysis = 0 # Reset Gemini counter on new shoe
    st.session_state.gemini_continuous_analysis_mode = False # Reset continuous analysis mode
    st.session_state.debug_log = [] # Clear debug log on full reset
    st.rerun() # Force rerun to refresh UI

def record_bet_result(actual_result): # Simplified signature
    # Retrieve predicted_side and recommendation_status from session state
    # Ensure last_prediction_data is set before accessing
    if "last_prediction_data" not in st.session_state or st.session_state.last_prediction_data is None:
        st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
        # FIX: Ensure debug_log is initialized safely before appending
        if "debug_log" not in st.session_state: st.session_state.debug_log = [] # Defensive check
        st.session_state.debug_log.append(f"RECORD: last_prediction_data was reset/initialized (first run).") 
    
    predicted_side = st.session_state.last_prediction_data['prediction']
    recommendation_status = st.session_state.last_prediction_data['recommendation']
    
    outcome_status = "Recorded" # Default outcome status for log
    history_action = "append_new" # Default action for history update

    # --- Store current drawdown BEFORE updating for this hand ---
    drawdown_before_this_hand = st.session_state.live_drawdown
    st.session_state.debug_log.append(f"--- RECORD initiated (Hand {len(st.session_state.history) + 1}) ---")
    st.session_state.debug_log.append(f"  Predicted: {predicted_side}, Actual: {actual_result}")
    st.session_state.debug_log.append(f"  Drawdown BEFORE calculation: {drawdown_before_this_hand}")

    # --- Update live_drawdown based on the actual outcome and AI's prediction ---
    # User's refined logic for live_drawdown:
    # Reset drawdown to 0 IF:
    # 1. Specific prediction (P/B/S6) was made AND actual result HIT
    # 2. Specific prediction (P/B/S6) was made AND actual result was T (Tie - neutral break for P/B/S6)
    # Increment drawdown BY 1 IF:
    # 1. Specific prediction (P/B/S6/T) was made AND actual result MISSED
    # Leave drawdown UNCHANGED IF:
    # 1. No specific prediction ('?') was made (AI recommended Avoid)

    if predicted_side != '?': # Only update drawdown if a specific prediction was made by AI
        is_hit_for_drawdown_reset = False
        # Check for HIT conditions that reset drawdown
        # HIT if actual_result == predicted_side OR (predicted Banker/S6 and actual S6) OR (predicted P/B/S6 and actual T)
        if actual_result == predicted_side: # Direct hit
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: Direct HIT ({predicted_side} == {actual_result}).")
        elif predicted_side == 'B' and actual_result == 'S6': # Banker hit by S6
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: Banker HIT by S6. ")
        elif predicted_side in ['P', 'B', 'S6'] and actual_result == 'T': # P/B/S6 hit by T (neutral break)
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: P/B/S6 HIT by T (neutral break).")
        # Note: The original code had `elif predicted_side == 'S6' and actual_outcome_of_current_hand == 'S6':`
        # `actual_outcome_of_current_hand` is undefined. It should be `actual_result`.
        # This condition is already covered by `actual_result == predicted_side` if `predicted_side` is 'S6'.
        # So, no change needed here, as `actual_result == predicted_side` already handles 'S6' hit.
            
        # If it's a hit, reset drawdown
        if is_hit_for_drawdown_reset:
            st.session_state.live_drawdown = 0
            st.session_state.debug_log.append(f"  Drawdown Logic: Drawdown reset to 0 (HIT).")
            st.session_state.gemini_continuous_analysis_mode = False # Exit continuous mode on a hit
        else: # Prediction was made but it was a MISS
            st.session_state.live_drawdown += 1
            st.session_state.debug_log.append(f"  Drawdown Logic: Drawdown incremented to {st.session_state.live_drawdown} (MISS).")
            # gemini_continuous_analysis_mode remains True if already active, or activates at drawdown 3
    else: # If predicted_side is '?', live_drawdown remains unchanged.
        st.session_state.debug_log.append(f"  Drawdown Logic: No specific prediction ('?'). Drawdown remains {st.session_state.live_drawdown}.")
    
    # --- Update History for Oracle Engine (and determine history_action) ---
    if actual_result == 'T':
        found_pb_for_tie = False
        # Loop in reverse to find the last P/B/S6 to attach the Tie to
        for i in reversed(range(len(st.session_state.history))):
            if st.session_state.history[i]['main_outcome'] in ['P', 'B', 'S6']:
                st.session_state.history[i]['ties'] += 1
                history_action = "tie_increment" # Action was incrementing ties on an existing entry
                found_pb_for_tie = True
                st.session_state.debug_log.append(f"  History Update: Tied 'T' to previous {st.session_state.history[i]['main_outcome']}. Tie count: {st.session_state.history[i]['ties']}")
                break
        if not found_pb_for_tie:
            # If no P/B/S6 found, add T as a standalone entry
            st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})
            history_action = "append_new" # Action was appending a new entry (standalone T)
            st.session_state.debug_log.append(f"  History Update: Added 'T' as standalone entry.")
    else:
        # For P, B, S6 results, always append a new entry
        st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})
        history_action = "append_new" # Action was appending a new entry
        st.session_state.debug_log.append(f"  History Update: Added '{actual_result}' as new entry.")

    # --- Record Bet Log (now includes history_action) ---
    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Recommendation": recommendation_status, # Log the recommendation
        "Outcome": outcome_status, # Simplified outcome
        "DrawdownBefore": drawdown_before_this_hand, # Store drawdown value BEFORE this hand's calculation
        "history_action": history_action # Store how history was modified (for UNDO)
    })
    st.session_state.debug_log.append(f"  Bet Log stored with history_action: {history_action}")


    # --- Update Oracle Engine's Learning States ---
    # Only update learning if a prediction was made (i.e., not '?' for predicted_side)
    if predicted_side != '?':
        # When updating learning, we use the history *before* the current result was added
        # to detect patterns that led to the prediction.
        history_for_pattern_detection = st.session_state.history[:-1] if len(st.session_state.history) > 0 else []
        # FIX: Ensure _build_big_road_data is used if available
        big_road_data_for_pattern_detection = [] # Default
        if '_build_big_road_data' in globals() and callable(globals()['_build_big_road_data']): # Check if _build_big_road_data is globally available
            big_road_data_for_pattern_detection = _build_big_road_data(history_for_pattern_detection)

        st.session_state.oracle_engine._update_learning(
            predicted_outcome=predicted_side,
            actual_outcome=actual_result,
            patterns_detected=st.session_state.oracle_engine.detect_patterns(history_for_pattern_detection, big_road_data_for_pattern_detection),
            momentum_detected=st.session_state.oracle_engine.detect_momentum(history_for_pattern_detection, big_road_data_for_pattern_detection),
            sequences_detected=st.session_state.oracle_engine._detect_sequences(history_for_pattern_detection)
        )
    
    # FIX: _cached_backtest_accuracy.clear() should be conditionally cleared based on its existence
    if '_cached_backtest_accuracy' in globals() and callable(globals()['_cached_backtest_accuracy']):
        _cached_backtest_accuracy.clear()

    # --- Auto-trigger Gemini Analysis Logic ---
    gemini_api_key_available = "GEMINI_API_KEY" in st.secrets # Check API key availability for auto-trigger

    if gemini_api_key_available and len(st.session_state.history) >= 20: # Ensure enough history for meaningful analysis
        # Condition 1: Trigger if live_drawdown hits 3, and activate continuous mode
        if st.session_state.live_drawdown == 3 and not st.session_state.gemini_continuous_analysis_mode:
            st.session_state.gemini_continuous_analysis_mode = True
            st.toast(f"✨ แพ้ติดกัน {st.session_state.live_drawdown} ครั้ง! กำลังให้ Gemini วิเคราะห์เชิงลึก...", icon="✨")
            st.session_state.gemini_analysis_result = asyncio.run(get_gemini_analysis(list(st.session_state.history)))
            st.session_state.hands_since_last_gemini_analysis = 0 # Reset 12-hand counter
        # Condition 2: Continue analysis if in continuous mode and still losing (drawdown > 0)
        elif st.session_state.gemini_continuous_analysis_mode and st.session_state.live_drawdown > 0:
            st.toast(f"✨ ยังคงวิเคราะห์ต่อเนื่อง (แพ้ติดกัน {st.session_state.live_drawdown} ครั้ง)...", icon="✨")
            st.session_state.gemini_analysis_result = asyncio.run(get_gemini_analysis(list(st.session_state.history)))
            st.session_state.hands_since_last_gemini_analysis = 0 # Reset 12-hand counter
        # Condition 3: Regular 12-hand auto-trigger (only if not in continuous mode)
        elif not st.session_state.gemini_continuous_analysis_mode:
            st.session_state.hands_since_last_gemini_analysis += 1
            if st.session_state.hands_since_last_gemini_analysis >= 12:
                st.toast("✨ กำลังให้ Gemini วิเคราะห์อัตโนมัติ (ทุก 12 ตา)...", icon="✨")
                st.session_state.gemini_analysis_result = asyncio.run(get_gemini_analysis(list(st.session_state.history)))
                st.session_state.hands_since_last_gemini_analysis = 0 # Reset counter after analysis
    st.session_state.debug_log.append(f"--- RECORD finished ---")
    st.rerun() # Force rerun to refresh UI


# --- Main App Layout ---

# Input Section
st.markdown("#### บันทึกผลลัพธ์")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("P (Player)"):
        record_bet_result('P')
with col2:
    if st.button("B (Banker)"):
        record_bet_result('B')
with col3:
    if st.button("T (Tie)"):
        record_bet_result('T')
with col4:
    if st.button("S6 (Super6)"):
        record_bet_result('S6')
with col5:
    if st.button("Undo", on_click=remove_last_from_history):
        pass # Handled by on_click
col_reset, col_analyze = st.columns([1, 2])
with col_reset:
    if st.button("เริ่มขอนใหม่", on_click=reset_all_history):
        pass # Handled by on_click


# --- Prediction and Recommendation Display ---
st.markdown("---")
st.markdown("#### การทำนายและคำแนะนำ")

# Before prediction, build big_road_data for the engine
# This part assumes _build_big_road_data is correctly defined and imported
big_road_data_for_prediction = []
if '_build_big_road_data' in globals() and callable(globals()['_build_big_road_data']):
    big_road_data_for_prediction = _build_big_road_data(st.session_state.history)

# Call the prediction function from OracleEngine
prediction_output = st.session_state.oracle_engine.predict_next(
    current_live_drawdown=st.session_state.live_drawdown,
    current_big_road_data=big_road_data_for_prediction # Pass big_road_data to predict_next if needed
)
st.session_state.last_prediction_data = prediction_output # Update session state with the latest prediction

# Display Prediction
predicted_side = st.session_state.last_prediction_data.get('prediction', '?')
recommendation = st.session_state.last_prediction_data.get('recommendation', 'Avoid ❌')
overall_confidence = st.session_state.last_prediction_data.get('overall_confidence', 0)
risk_level = st.session_state.last_prediction_data.get('risk', 'Uncertainty')

pred_class = "no-prediction"
if predicted_side == 'P':
    pred_class = "player"
elif predicted_side == 'B':
    pred_class = "banker"
elif predicted_side == 'S6':
    pred_class = "super6"

st.markdown(f"""
<div style="text-align: center;">
    <div class="prediction-text {pred_class}">
        ทำนาย: {predicted_side}
    </div>
    <div style="font-size: 1.2rem; font-weight: bold; color: {'green' if recommendation == 'Play ✅' else 'orange'};">
        คำแนะนำ: {recommendation} ({overall_confidence:.1f}% Confidence)
    </div>
    <div style="font-size: 0.9rem; color: #bbb;">
        ระดับความเสี่ยง: {risk_level}
    </div>
</div>
""", unsafe_allow_html=True)


# --- Tie/Super6 Opportunity Display ---
st.markdown("---")
st.markdown("#### โอกาส Tie / Super6")
# Re-run Tie/Super6 analysis if current_history is updated
st.session_state.tie_opportunity_data = st.session_state.oracle_engine.get_tie_opportunity_analysis(st.session_state.history)

tie_pred = st.session_state.tie_opportunity_data['prediction']
tie_conf = st.session_state.tie_opportunity_data['confidence']
tie_reason = st.session_state.tie_opportunity_data['reason']

tie_class = "no-recommendation"
if tie_pred == 'T':
    tie_class = "tie" # Assuming you define a CSS class for Tie if needed
elif tie_pred == 'S6':
    tie_class = "super6" # Assuming you define a CSS class for S6 if needed

st.markdown(f"""
<div style="text-align: center;">
    <div class="tie-opportunity-text {tie_class}">
        โอกาส: {tie_pred}
    </div>
    <div style="font-size: 1rem; color: #ccc;">
        ความมั่นใจ: {tie_conf:.1f}%
    </div>
    <div style="font-size: 0.85rem; color: #888; font-style: italic;">
        เหตุผล: {tie_reason}
    </div>
</div>
""", unsafe_allow_html=True)


# --- Live Drawdown Display ---
st.markdown("---")
st.markdown("#### สถานะ Drawdown")
drawdown_color = "green"
if st.session_state.live_drawdown >= 1:
    drawdown_color = "orange"
if st.session_state.live_drawdown >= 3:
    drawdown_color = "red"

st.markdown(f"""
<div style="text-align: center; font-size: 1.5rem; font-weight: bold; color: {drawdown_color};">
    Drawdown ปัจจุบัน: {st.session_state.live_drawdown}
</div>
""", unsafe_allow_html=True)

# --- Gemini Analysis Display ---
st.markdown("---")
st.markdown("#### การวิเคราะห์จาก Gemini AI")
gemini_api_key_available = "GEMINI_API_KEY" in st.secrets # Re-check key availability

if gemini_api_key_available:
    with col_analyze: # This col_analyze was defined above in the input section, reuse or define a new one if layout desired differently
        if st.button("วิเคราะห์ด้วย Gemini AI (แบบ Manual)"):
            if len(st.session_state.history) < 20:
                st.warning("โปรดบันทึกประวัติอย่างน้อย 20 ตา เพื่อการวิเคราะห์ที่มีประสิทธิภาพจาก Gemini.")
            else:
                with st.spinner('กำลังให้ Gemini วิเคราะห์...'):
                    st.session_state.gemini_analysis_result = asyncio.run(get_gemini_analysis(list(st.session_state.history)))
                st.session_state.hands_since_last_gemini_analysis = 0 # Reset counter
    
    if st.session_state.gemini_continuous_analysis_mode:
        st.info(f"💡 โหมดวิเคราะห์ต่อเนื่องด้วย Gemini ทำงานอยู่ (Drawdown: {st.session_state.live_drawdown})", icon="ℹ️")

    st.markdown(f"""
    <div style="border: 1px solid #444; padding: 10px; border-radius: 5px; background-color: #222;">
        <pre style="white-space: pre-wrap; word-wrap: break-word;">{st.session_state.gemini_analysis_result}</pre>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning("⚠️ ไม่พบ Gemini API Key ใน Streamlit Secrets. โปรดเพิ่มเพื่อเปิดใช้งานฟังก์ชันการวิเคราะห์จาก Gemini.")


# --- History Display (Big Road) ---
st.markdown("---")
st.markdown("#### ประวัติขอนปัจจุบัน (Big Road)")

# Re-build big road data for display every time
big_road_data_display = []
if '_build_big_road_data' in globals() and callable(globals()['_build_big_road_data']):
    big_road_data_display = _build_big_road_data(st.session_state.history)

if big_road_data_display:
    html_output = "<div class='big-road-container'>"
    # Adjust how many columns to show if too many to prevent excessively wide display
    # For now, let's show all, assuming horizontal scroll handles it.
    
    for col_idx, column in enumerate(big_road_data_display):
        html_output += "<div class='big-road-column'>"
        for row_idx in range(6): # Baccarat Big Road typically has 6 rows
            cell_content = ""
            tie_markup = ""
            natural_markup = ""
            circle_class = ""

            if row_idx < len(column) and column[row_idx] is not None:
                outcome, ties, is_natural = column[row_idx]
                if outcome == 'P':
                    circle_class = "player-circle"
                elif outcome == 'B' or outcome == 'S6': # S6 also uses Banker circle
                    circle_class = "banker-circle"
                # If outcome is 'T', it should generally not create a new circle in Big Road,
                # but instead attach to the previous P/B/S6. _build_big_road_data handles this.
                # If it somehow appears here as a standalone 'T' from history, it won't get a circle.

                if outcome == 'S6':
                    cell_content = "S6" # Show S6 inside circle
                
                # Only render circle if it's P, B, or S6
                if outcome in ['P', 'B', 'S6']:
                    cell_content = f"<div class='big-road-circle {circle_class}'>{cell_content}</div>"

                if ties > 0:
                    tie_markup = f"<div class='tie-oval'>+{ties}</div>"
                if is_natural:
                    natural_markup = "<div class='natural-indicator'>N</div>"
            
            html_output += f"<div class='big-road-cell'>{cell_content}{tie_markup}{natural_markup}</div>"
        html_output += "</div>"
    html_output += "</div>"
    st.markdown(html_output, unsafe_allow_html=True)
else:
    st.info("ยังไม่มีประวัติในขอนนี้ เริ่มบันทึกผลลัพธ์เพื่อสร้าง Big Road.", icon="ℹ️")


# --- Bet Log Display ---
st.markdown("---")
st.markdown("#### Bet Log")
if st.session_state.bet_log:
    # Create a DataFrame for better display
    df_bet_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_bet_log.set_index(df_bet_log.index + 1)) # 1-based index
else:
    st.info("ยังไม่มีข้อมูลการเดิมพัน.")

# --- Debug Log Display (Optional, for development) ---
st.markdown("---")
st.checkbox("แสดง Debug Log (สำหรับนักพัฒนา)", key="show_debug_log")
if st.session_state.show_debug_log:
    st.markdown("#### Debug Log")
    for entry in st.session_state.debug_log:
        st.code(entry, language='text')

st.markdown("---")
st.info(f"Total History Recorded (P/B/T/S6): {len(st.session_state.history)} hands.")
st.info(f"Oracle Engine Internal State Version: v{st.session_state.oracle_engine.__version__}")

# Note: st.rerun() is now called within the callback functions (record_bet_result, remove_last_from_history, reset_all_history)
# This prevents excessive reruns and makes the app more responsive.
# If you find the UI not updating as expected after other non-button interactions, you might need to add specific st.rerun() calls.
