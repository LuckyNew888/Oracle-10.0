import streamlit as st
import pandas as pd
import math
import json # Import json for parsing structured responses from LLM
import asyncio # For running async functions

# Import OracleEngine and helper functions (note: _cached_backtest_accuracy and _build_big_road_data are global)
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data

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
def get_oracle_engine():
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
    st.session_state.oracle_engine = get_oracle_engine()


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
    # Removed st.experimental_rerun() from here

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
    # Removed st.experimental_rerun() from here

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
        elif predicted_side == 'T' and actual_result == 'T': # Tie hit by Tie
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: Tie HIT by Tie. ")
        elif predicted_side == 'S6' and actual_outcome_of_current_hand == 'S6': # S6 hit by S6
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: S6 HIT by S6. ")
        
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
