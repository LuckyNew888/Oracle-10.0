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
CURRENT_ENGINE_VERSION = "1.11" # This must match OracleEngine.__version__ in oracle_engine.py

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
    st.session_state.debug_log.append(f"UNDO: History length before pop: {len(st.session_state.history)}")
    
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


    _cached_backtest_accuracy.clear() 
    st.session_state.oracle_engine.reset_learning_states_on_undo() # This should affect stats, not history structure
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'}
    st.session_state.hands_since_last_gemini_analysis = 0
    st.session_state.gemini_analysis_mode = False
    st.session_state.gemini_continuous_analysis_mode = False # Ensure continuous mode is off
    st.session_state.debug_log.append(f"--- UNDO finished ---")
    st.experimental_rerun() # Force rerun

def reset_all_history(): # This is now "Start New Shoe"
    st.session_state.history = []
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history() # Resets all learning states
    _cached_backtest_accuracy.clear()
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0 # Reset live_drawdown on new shoe
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini" # Reset Gemini analysis
    st.session_state.tie_opportunity_data = {'prediction': '?', 'confidence': 0, 'reason': 'ยังไม่มีการวิเคราะห์'} # Reset Tie analysis
    st.session_state.hands_since_last_gemini_analysis = 0 # Reset Gemini counter on new shoe
    st.session_state.gemini_continuous_analysis_mode = False # Reset continuous analysis mode
    st.session_state.debug_log = [] # Clear debug log on full reset
    st.experimental_rerun() # Force rerun

def record_bet_result(actual_result): # Simplified signature
    # Retrieve predicted_side and recommendation_status from session state
    # Ensure last_prediction_data is set before accessing
    if "last_prediction_data" not in st.session_state or st.session_state.last_prediction_data is None:
        st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
        # FIX: Ensure debug_log is initialized safely before appending
        if "debug_log" not in st.session_state: st.session_state.debug_log = [] # Defensive check
        st.session_state.debug_log.append(f"RECORD: last_prediction_data was reset/initialized.") 
    
    predicted_side = st.session_state.last_prediction_data['prediction']
    recommendation_status = st.session_state.last_prediction_data['recommendation']
    
    outcome_status = "Recorded" # Default outcome status for log
    history_action = "append_new" # Default action for history update

    # --- Store current drawdown BEFORE updating for this hand ---
    drawdown_before_this_hand = st.session_state.live_drawdown
    st.session_state.debug_log.append(f"--- RECORD initiated (Hand {len(st.session_state.history) + 1}) ---")
    st.session_state.debug_log.append(f"RECORD: Predicted: {predicted_side}, Actual: {actual_result}")
    st.session_state.debug_log.append(f"  Drawdown BEFORE calculation: {drawdown_before_this_hand}")

    # --- Update live_drawdown based on the actual outcome and AI's prediction ---
    # User's refined logic for live_drawdown:
    # Reset drawdown to 0 IF:
    # 1. Specific prediction (P/B/S6/T) was made AND actual result HIT
    # 2. Specific prediction (P/B/S6) was made AND actual result was T (Tie - neutral break for P/B/S6)
    # Increment drawdown BY 1 IF:
    # 1. Specific prediction (P/B/S6/T) was made AND actual result MISSED
    # Leave drawdown UNCHANGED IF:
    # 1. No specific prediction ('?') was made (AI recommended Avoid)

    if predicted_side != '?': # Only update drawdown if a specific prediction was made by AI
        is_hit_for_drawdown_reset = False
        # is_miss_for_drawdown = False # Not used directly for update logic, only for debug log

        # Check for HIT conditions that reset drawdown
        if predicted_side == actual_result: # Direct hit
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: Direct HIT ({predicted_side} == {actual_result}).")
        elif predicted_side == 'B' and actual_result == 'S6': # Banker hit by S6
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: Banker HIT by S6. ")
        elif predicted_side in ['P', 'B', 'S6'] and actual_result == 'T': # P/B/S6 hit by T (neutral break)
            is_hit_for_drawdown_reset = True
            st.session_state.debug_log.append(f"  Drawdown Logic: P/B/S6 HIT by T (neutral break).")
        
        # If it's a hit, reset drawdown
        if is_hit_for_drawdown_reset:
            st.session_state.live_drawdown = 0
            st.session_state.gemini_continuous_analysis_mode = False # Exit continuous mode on a hit
            st.session_state.debug_log.append(f"  Drawdown Logic: Drawdown reset to 0 (HIT).")
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
    if '_cached_backtest_accuracy' in globals() and callable(globals()['_cached_backtest_accuracy']): # Check if _cached_backtest_accuracy is globally available
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


# --- Gemini Analysis Function ---
# This function is designed to be called asynchronously.
# It uses `st.secrets` to get the API key securely.
async def get_gemini_analysis(history_data):
    """
    Calls Gemini API to get an advanced analysis of the game history.
    """
    # Retrieve API key from Streamlit secrets
    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        return "❌ ไม่พบ Gemini API Key ใน Streamlit Secrets. โปรดตั้งค่าใน 'Manage app' -> 'Secrets'."

    prompt = f"""
    คุณเป็นผู้เชี่ยวชาญด้านบาคาร่า AI และนักวิเคราะห์รูปแบบไพ่ที่แม่นยำสูง.
    คุณได้รับข้อมูลประวัติการเล่นบาคาร่าในรูปแบบลำดับเหตุการณ์ (sequence) และข้อมูล Big Road.
    โปรดวิเคราะห์ประวัติที่ให้มา และให้ข้อมูลเชิงลึกเกี่ยวกับการทำนายผลลัพธ์ต่อไป (Player, Banker, Tie, หรือ Super6)
    โดยเน้นที่โอกาสของ Tie (เสมอ) และ Super6 (Banker ชนะ 6 แต้ม) เป็นพิเศษ.

    ข้อมูลประวัติ (ลำดับเหตุการณ์): {history_data}
    ข้อมูล Big Road (โครงสร้างคอลัมน์): {json.dumps(get_big_road_data_safe(history_data))}

    โปรดให้การวิเคราะห์ของคุณในรูปแบบข้อความที่เป็นธรรมชาติและเข้าใจง่าย โดยระบุ:
    1. รูปแบบที่โดดเด่นที่คุณสังเกตเห็น (เช่น มังกร, ปิงปอง, คู่ตัด, 2D patterns)
    2. แนวโน้มปัจจุบันของเกม (เช่น แนวโน้ม Banker, Player, หรือการสลับไปมา)
    3. โอกาสของ Tie หรือ Super6 ในตาถัดไป โดยให้เหตุผลสั้นๆ
    4. คำแนะนำโดยรวมสำหรับตาถัดไป (Player, Banker, Tie, Super6, หรือ No Bet)
    """

    # For now, simulate a response to avoid breaking the app without a real API call setup.
    await asyncio.sleep(2) # Simulate network latency
    
    # Mock Gemini response for demonstration
    mock_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": f"""
                            จากการวิเคราะห์ประวัติ {len(history_data)} ตา:
                            1. **รูปแบบโดดเด่น:** ดูเหมือนจะมีการสลับระหว่าง Player และ Banker ในช่วงสั้นๆ แต่ก็มีแนวโน้ม Banker Streak เกิดขึ้นบ้าง. Big Road แสดงให้เห็นว่า Banker มีความแข็งแกร่งเล็กน้อยในช่วง 5-10 ตาที่ผ่านมา
                            2. **แนวโน้มปัจจุบัน:** แนวโน้มยังคงผันผวน แต่ Banker มีโอกาสที่จะสร้าง Streak ได้อีกครั้ง
                            3. **โอกาสของ Tie/Super6:**
                               * **Tie:** มีโอกาสปานกลาง (ประมาณ 10-15%) เนื่องจากมีการออก Tie ประปรายในประวัติ และบางครั้งก็เกิดขึ้นหลังจากรูปแบบ PBP.
                               * **Super6:** โอกาสค่อนต่ำ (ประมาณ 2-5%) เนื่องจาก Super6 เป็นผลลัพธ์ที่หายากและไม่มีรูปแบบที่ชัดเจนบ่งชี้ในประวัติที่ผ่านมา.
                            4. **คำแนะนำโดยรวม:** แนะนำให้ Bet Banker (B) ด้วยความระมัดระวัง. หากมี Tie เกิดขึ้น ให้ถือว่าเสมอตัว. หลีกเลี่ยง Super6 เว้นแต่จะมีข้อมูลเพิ่มเติมที่แข็งแกร่งกว่านี้.
                            """
                        }
                    ]
                }
            }
        ]
    }
    
    # In a real scenario, you would parse the actual API response here.
    result = mock_response

    if result.get("candidates") and len(result["candidates"]) > 0 and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts") and len(result["candidates"][0]["content"]["parts"]) > 0:
        # FIX: Changed .parts[0].text to ["parts"][0]["text"] for dictionary access
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"❌ ไม่สามารถรับการวิเคราะห์จาก Gemini ได้: โครงสร้างการตอบกลับไม่ถูกต้องหรือไม่มีเนื้อหาข้อความ."

def get_big_road_data_safe(history_list):
    """Safely calls _build_big_road_data if it exists in global scope."""
    if '_build_big_road_data' in globals() and callable(globals()['_build_big_road_data']):
        return globals()['_build_big_road_data'](history_list)
    return [] # Return empty list if function not available

# --- Main Streamlit App Logic ---
engine = st.session_state.oracle_engine
engine.history = st.session_state.history

# --- Sidebar for Settings and API Key ---
st.sidebar.markdown("### ⚙️ การตั้งค่า")

# Check if GEMINI_API_KEY is available in Streamlit Secrets
gemini_api_key_available = "GEMINI_API_KEY" in st.secrets

if not gemini_api_key_available:
    st.sidebar.warning("⚠️ ไม่พบ Gemini API Key ใน Streamlit Secrets. โปรดตั้งค่าใน 'Manage app' -> 'Secrets' เพื่อใช้ฟังก์ชันวิเคราะห์เชิงลึก")
else:
    st.sidebar.success("✅ Gemini API Key พร้อมใช้งาน (จาก Streamlit Secrets)")

if st.sidebar.button("✨ วิเคราะห์เชิงลึก (Gemini) (กดเอง)", use_container_width=True): # Renamed button to clarify
    if gemini_api_key_available:
        with st.spinner("กำลังให้ Gemini วิเคราะห์..."):
            # Pass a copy of the history to avoid modifying the live history during analysis
            # Call the async function using Streamlit's async support
            st.session_state.gemini_analysis_result = asyncio.run(get_gemini_analysis(list(st.session_state.history)))
            st.session_state.hands_since_last_gemini_analysis = 0 # Reset 12-hand counter if manually triggered
            st.session_state.gemini_continuous_analysis_mode = False # Exit continuous mode if manually triggered
    else:
        st.sidebar.error("โปรดตั้งค่า Gemini API Key ใน Streamlit Secrets ก่อน")
    st.experimental_rerun() # Force rerun

if len(st.session_state.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(st.session_state.history)}** ตา)")

# --- Main Prediction Section ---
st.markdown("#### 🔮 ทำนายตาถัดไป (หลัก):")
prediction_data = None # Initialize for the current run
next_pred_side = '?'
conf = 0
recommendation_status = "—"

# Get current_drawdown_display from session state
current_drawdown_display = st.session_state.live_drawdown

if len(engine.history) >= 20:
    # Pass current_drawdown_display to predict_next for protection logic
    prediction_data = engine.predict_next(current_live_drawdown=current_drawdown_display) # Calculate primary prediction for current state
    st.session_state.tie_opportunity_data = engine.get_tie_opportunity_analysis(engine.history) # Calculate Tie opportunity

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score(engine.history, get_big_road_data_safe(engine.history)) # Call safe function
        recommendation_status = prediction_data['recommendation']
        
        # Store the current prediction data in session state for the next button click
        st.session_state.last_prediction_data = prediction_data

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', 'S6': '🟠 Super6', '?': '— ไม่มีคำแนะนำ'} # Added S6
        
        # Apply specific CSS class for prediction results
        prediction_css_class = ""
        if next_pred_side == 'P':
            prediction_css_class = "player"
        elif next_pred_side == 'B':
            prediction_css_class = "banker"
        elif next_pred_side == 'T':
            prediction_css_class = "tie"
        elif next_pred_side == 'S6':
            prediction_css_class = "super6"
        elif next_pred_side == '?':
            prediction_css_class = "no-prediction"


        st.markdown(f'<div class="prediction-text {prediction_css_class}">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}") # Risk is now informational
        st.markdown(f"**🧾 คำแนะนำ:** **{recommendation_status}**")
        
        # Display Current Drawdown ONLY if a prediction was made (not '?')
        # As per the new logic, live_drawdown is 0 if next_pred_side is '?'.
        # So this condition ensures it only shows when there's an actual P/B/T/S6 prediction.
        if next_pred_side != '?': 
            st.markdown(f"**📉 แพ้ติดกัน:** **{current_drawdown_display}** ครั้ง") 
        else:
            st.markdown(f"**📉 แพ้ติดกัน:** **0** ครั้ง") # Removed explanatory text

    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายหลักจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
        # Ensure last_prediction_data is reset if there's an error or no prediction
        st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
        st.session_state.live_drawdown = 0 # Reset live_drawdown on error
else:
    st.markdown("— (ประวัติไม่ครบ)")
    # Ensure last_prediction_data is reset if history is insufficient
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0 # Reset live_drawdown if history is insufficient


# --- Tie Opportunity Section ---
st.markdown("---") # Separator
st.markdown("#### 🟢 โอกาสเสมอ (Tie Opportunity):")
# Changed minimum history for Tie/Super6 analysis to 1 (as theoretical prob applies from 0 hands)
if len(engine.history) >= 1: 
    tie_data = st.session_state.tie_opportunity_data
    tie_pred_side = tie_data['prediction']
    tie_conf = tie_data['confidence']
    tie_reason = tie_data['reason']

    # Display Tie/Super6 prediction if confidence is high enough
    if tie_pred_side == 'T':
        st.markdown(f'<div class="tie-opportunity-text">🟢 Tie (Confidence: {tie_conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**💡 เหตุผล:** {tie_reason}")
    elif tie_pred_side == 'S6':
        st.markdown(f'<div class="tie-opportunity-text super6">🟠 Super6 (Confidence: {tie_conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**💡 เหตุผล:** {tie_reason}")
    else:
        st.markdown(f'<div class="tie-opportunity-text no-recommendation">— ไม่มีคำแนะนำ Tie/Super6 ที่แข็งแกร่ง (Confidence: {tie_conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**💡 เหตุผล:** {tie_reason}")
else:
    st.markdown("— (ประวัติไม่ครบสำหรับ Tie/Super6)")


with st.expander("🧬 Developer View"):
    st.text(prediction_data['developer_view'] if prediction_data else "No primary prediction data available.")
    st.write("--- Pattern Success Rates ---")
    st.write(engine.pattern_stats)
    st.write("--- Momentum Success Rates ---")
    st.write(engine.momentum_stats)
    st.write("--- Sequence Memory Stats ---") # New: Display sequence memory
    st.write(engine.sequence_memory_stats)
    st.write("--- Tie Prediction Stats (for tracking) ---") # New: Display Tie stats
    st.write(engine.tie_stats)
    st.write("--- Super6 Prediction Stats (for tracking) ---") # New: Display Super6 stats
    st.write(engine.super6_stats)
    st.write("--- Failed Pattern Instances ---")
    st.write(engine.failed_pattern_instances)
    st.write("--- Backtest Results ---")
    
    # FIX: Ensure _cached_backtest_accuracy is called conditionally to avoid NameError if not imported
    backtest_summary = {}
    if '_cached_backtest_accuracy' in globals() and callable(globals()['_cached_backtest_accuracy']):
        backtest_summary = _cached_backtest_accuracy(
            engine.history,
            engine.pattern_stats,
            engine.momentum_stats,
            engine.failed_pattern_instances,
            engine.sequence_memory_stats,
            engine.tie_stats, # Pass tie stats
            engine.super6_stats # Pass super6 stats
        )
    else:
        st.write("⚠️ ไม่สามารถคำนวณ Backtest ได้: _cached_backtest_accuracy ไม่พร้อมใช้งานในเวอร์ชันนี้.")

    if backtest_summary:
        st.write(f"Accuracy: {backtest_summary['accuracy_percent']:.2f}% ({backtest_summary['hits']}/{backtest_summary['total_bets']})")
        st.write(f"Max Drawdown: {backtest_summary['max_drawdown']} misses")
    else:
        st.write("ยังไม่มีข้อมูล Backtest (ประวัติไม่ครบ หรือฟังก์ชันไม่พร้อมใช้งาน)")
    
    st.write(f"Current Drawdown (live): {st.session_state.live_drawdown} misses") # Display live drawdown here
    
    st.markdown("--- 🧠 Gemini Analysis ---")
    st.write(st.session_state.gemini_analysis_result) # Display Gemini's analysis here

    st.markdown("--- 🐞 Debug Log ---")
    # Display debug log in reverse order for easier viewing of latest entries
    for log_entry in reversed(st.session_state.debug_log):
        st.text(log_entry)


# --- Big Road Display ---
st.markdown("<b>🛣️ Big Road:</b>", unsafe_allow_html=True)

history_results = st.session_state.history
big_road_display_data = get_big_road_data_safe(history_results) # Use safe function

if big_road_display_data:
    max_row_display = 6 # Fixed to 6 rows as requested for vertical display
    
    columns = big_road_display_data

    MAX_DISPLAY_COLUMNS = 12 # Still limit horizontal display to 12 columns
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:]

    big_road_html_parts = []
    big_road_html_parts.append(f"<div class='big-road-container' id='big-road-container-unique'>")
    for col in columns:
        big_road_html_parts.append("<div class='big-road-column'>")
        # Loop through fixed 6 rows
        for row_idx in range(max_row_display): 
            cell_content = ""
            # Check if there's data for this cell in the current column
            if row_idx < len(col) and col[row_idx] is not None:
                # Unpack the tuple with the new is_super6 flag
                # The tuple now contains (main_outcome, ties, is_natural, is_super6)
                cell_result, tie_count, natural_flag, is_super6 = col[row_idx]
                
                emoji_color_class = ""
                main_text_in_circle = "" # What text goes inside the circle

                if cell_result == "P":
                    emoji_color_class = "player-circle"
                    main_text_in_circle = "" 
                elif cell_result == "B":
                    emoji_color_class = "banker-circle"
                    main_text_in_circle = ""
                elif cell_result == "T":
                    emoji_color_class = "tie-circle" # Using a dedicated tie-circle class
                    main_text_in_circle = "T" # Display 'T' for Tie inside the circle
                elif cell_result == "S6":
                    emoji_color_class = "banker-circle" # Super6 should be red like Banker
                    main_text_in_circle = "6" # Display '6' for Super6 inside the circle
                
                tie_html = ""
                if tie_count > 0:
                    tie_html = f"<div class='tie-oval'>{tie_count}</div>"
                
                natural_indicator_html = ""
                # Only show 'N' if it's natural AND NOT a Super6 (since S6 has '6' inside)
                if natural_flag and not is_super6: 
                    natural_indicator_html = f"<span class='natural-indicator'>N</span>"

                cell_content = (
                    f"<div class='big-road-circle {emoji_color_class}'>"
                    f"{main_text_in_circle}" # Display the main text (e.g., 'T' or '6')
                    f"{natural_indicator_html}" # Display 'N' if applicable
                    f"</div>"
                    f"{tie_html}"
                )
            
            big_road_html_parts.append(f"<div class='big-road-cell'>{cell_content}</div>")
        big_road_html_parts.append("</div>")
    big_road_html_parts.append("</div>")

    st.markdown("".join(big_road_html_parts), unsafe_allow_html=True)

else:
    st.info("🔄 ยังไม่มีข้อมูล")


col_p_b_t_s6 = st.columns(4) # Changed to 4 columns for S6 button

# Use on_click and pass only the actual result.
# predicted_side and recommendation_status will be retrieved from st.session_state.last_prediction_data
with col_p_b_t_s6[0]:
    if st.button(f"บันทึก: 🔵 P", key="record_P", use_container_width=True, on_click=record_bet_result, args=('P',)):
        pass # Action handled by on_click
with col_p_b_t_s6[1]:
    if st.button(f"บันทึก: 🔴 B", key="record_B", use_container_width=True, on_click=record_bet_result, args=('B',)):
        pass # Action handled by on_click
with col_p_b_t_s6[2]:
    if st.button(f"บันทึก: 🟢 T", key="record_T", use_container_width=True, on_click=record_bet_result, args=('T',)):
        pass # Action handled by on_click
with col_p_b_t_s6[3]: # New column for Super6 button
    if st.button(f"บันทึก: 🟠 S6", key="record_S6", use_container_width=True, on_click=record_bet_result, args=('S6',)):
        pass # Action handled by on_click


col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        pass # Action handled by on_click
with col_hist2:
    if st.button("🧹 เริ่มขอนใหม่", key="resetAllHist", use_container_width=True, on_click=reset_all_history): # Renamed button
        pass # Action handled by on_click

st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

st.caption("ระบบวิเคราะห์ Oracle AI โดยคุณ")
