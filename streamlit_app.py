import streamlit as st
import pandas as pd
import math

# Import OracleEngine and helper functions
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data

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
        color: #4CAF50;
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
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
        padding: 10px;
        background-color: #1a1a1a;
        border-radius: 8px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        min-height: 180px; /* Still maintain a min-height for visual consistency */
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
        margin-bottom: 1px;
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

if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = get_oracle_engine()

# --- Cache compatibility check for new attributes and methods ---
# This ensures that if a cached OracleEngine instance is loaded from a previous version
# that didn't have certain attributes or methods, it gets re-initialized or updated.
# More robust check for critical methods like _detect_sequences
if not hasattr(st.session_state.oracle_engine, '_detect_sequences'):
    st.session_state.oracle_engine = OracleEngine()
    st.session_state.oracle_engine.reset_history() # Reset all learning states
    # No need for individual attribute checks below if we just re-initialized the whole engine.
    # The new OracleEngine() instance will have all the latest attributes.
else:
    # If the engine wasn't re-initialized, ensure all new attributes are present.
    # This handles cases where the class structure changed but not so drastically as to remove core methods.
    if not hasattr(st.session_state.oracle_engine, 'sequence_memory_stats'):
        st.session_state.oracle_engine.sequence_memory_stats = {}
    if not hasattr(st.session_state.oracle_engine, 'pattern_weights'):
        st.session_state.oracle_engine.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Big Eye Boy (2D Simple - Follow)': 0.9, 'Big Eye Boy (2D Simple - Break)': 0.8,
            'Small Road (2D Simple - Chop)': 0.75, 'Cockroach Pig (2D Simple - Chop)': 0.7,
            'Broken Pattern': 0.3,
        }
    if not hasattr(st.session_state.oracle_engine, 'momentum_weights'):
        st.session_state.oracle_engine.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6,
        }
    if not hasattr(st.session_state.oracle_engine, 'sequence_weights'):
        st.session_state.oracle_engine.sequence_weights = {3: 0.6, 4: 0.7, 5: 0.8}


# --- Session State Initialization (other variables) ---
if "history" not in st.session_state:
    st.session_state.history = []
# Removed money_balance, bet_amount from session_state init
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []

# Removed all money management system related session state initializations
# if "money_management_system" not in st.session_state:
#     st.session_state.money_management_system = "Fixed Bet"
# ... and so on for martingale, fibonacci, labouchere

# --- Removed Function to Calculate Next Bet Amount ---
# def calculate_next_bet():
#     ...

# --- Callback Functions for History and Betting Management ---
def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        _cached_backtest_accuracy.clear()
        st.session_state.oracle_engine.reset_learning_states_on_undo()
    

def reset_all_history(): # This is now "Start New Shoe"
    st.session_state.history = []
    # Removed money_balance reset
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history() # Resets all learning states
    _cached_backtest_accuracy.clear()
    # Removed reset_money_management_state()


def record_bet_result(predicted_side, actual_result, recommendation_status):
    # Simplified logic: no money management, just record the outcome and update learning
    # We'll use a placeholder bet amount of 1.0 for logging consistency if needed,
    # but actual money balance is not tracked.
    
    # The recommendation_status will now be "Play ✅" if a prediction was made,
    # or "Avoid ❌" if no prediction could be made (e.g., low confidence, insufficient history).
    
    # For logging purposes, we can assume a "bet" happened if it was a "Play ✅" recommendation
    # and a prediction was made.
    
    outcome = "Recorded" # Default outcome
    
    # --- Record Bet Log ---
    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Recommendation": recommendation_status, # Log the recommendation
        "Outcome": outcome # Simplified outcome
    })

    # --- Update History for Oracle Engine ---
    # This part should still happen to record the actual game outcome for future predictions
    if actual_result == 'T':
        found_pb_for_tie = False
        for i in reversed(range(len(st.session_state.history))):
            if st.session_state.history[i]['main_outcome'] in ['P', 'B']:
                st.session_state.history[i]['ties'] += 1
                found_pb_for_tie = True
                break
        if not found_pb_for_tie:
            st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})
    else:
        st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})

    # --- Update Oracle Engine's Learning States ---
    # Only update learning if a prediction was made (i.e., not '?' for predicted_side)
    if predicted_side != '?':
        history_before_current_result = st.session_state.history[:-1] if len(st.session_state.history) > 0 else []
        big_road_data_before = _build_big_road_data(history_before_current_result)
        
        patterns_before = st.session_state.oracle_engine.detect_patterns(history_before_current_result, big_road_data_before)
        momentum_before = st.session_state.oracle_engine.detect_momentum(history_before_current_result, big_road_data_before)
        sequences_before = st.session_state.oracle_engine._detect_sequences(history_before_current_result) # New: Get sequences

        st.session_state.oracle_engine._update_learning(
            predicted_outcome=predicted_side,
            actual_outcome=actual_result,
            patterns_detected=patterns_before,
            momentum_detected=momentum_before,
            sequences_detected=sequences_before # New: Pass sequences to update learning
        )
    
    _cached_backtest_accuracy.clear()


engine = st.session_state.oracle_engine
engine.history = st.session_state.history

# --- Removed Money Management UI ---
st.sidebar.markdown("### ⚙️ การตั้งค่า")
# Removed st.session_state.money_balance input
# Removed st.selectbox for money_management_system
# Removed all conditional inputs for Martingale, Fibonacci, Labouchere
# Removed st.session_state.bet_amount input
# Removed st.info(f"**จำนวนเงินที่ต้องเดิมพันตาถัดไป:** ...")


if len(st.session_state.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(st.session_state.history)}** ตา)")

st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None
next_pred_side = '?'
conf = 0
recommendation_status = "—" # Initialize recommendation status
current_drawdown_display = 0 # Initialize for display

engine = st.session_state.oracle_engine
engine.history = st.session_state.history

if len(engine.history) >= 20:
    prediction_data = engine.predict_next()

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score(engine.history, _build_big_road_data(engine.history))
        recommendation_status = prediction_data['recommendation'] # Get the recommendation status
        current_drawdown_display = prediction_data['current_drawdown'] # Get current drawdown

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f'<div class="prediction-text">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}") # Risk is now informational
        st.markdown(f"**🧾 คำแนะนำ:** **{recommendation_status}**")
        
        # Display Current Drawdown ONLY if a prediction was made (not '?')
        if next_pred_side != '?':
            st.markdown(f"**📉 แพ้ติดกัน:** **{current_drawdown_display}** ครั้ง") 

        with st.expander("🧬 Developer View"):
            st.text(prediction_data['developer_view'])
            st.write("--- Pattern Success Rates ---")
            st.write(engine.pattern_stats)
            st.write("--- Momentum Success Rates ---")
            st.write(engine.momentum_stats)
            st.write("--- Sequence Memory Stats ---") # New: Display sequence memory
            st.write(engine.sequence_memory_stats)
            st.write("--- Failed Pattern Instances ---")
            st.write(engine.failed_pattern_instances)
            st.write("--- Backtest Results ---")
            backtest_summary = _cached_backtest_accuracy(
                engine.history,
                engine.pattern_stats,
                engine.momentum_stats,
                engine.failed_pattern_instances,
                engine.sequence_memory_stats # Pass sequence memory to backtest cache
            )
            st.write(f"Accuracy: {backtest_summary['accuracy_percent']:.2f}% ({backtest_summary['hits']}/{backtest_summary['total_bets']})")
            st.write(f"Max Drawdown: {backtest_summary['max_drawdown']} misses")
            st.write(f"Current Drawdown (from backtest): {backtest_summary['current_drawdown']} misses") # Also show in backtest summary
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
else:
    st.markdown("— (ประวัติไม่ครบ)")

# --- Big Road Display ---
st.markdown("<b>🛣️ Big Road:</b>", unsafe_allow_html=True)

history_results = st.session_state.history
big_road_display_data = _build_big_road_data(history_results)

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
                cell_result, tie_count, natural_flag = col[row_idx]
                emoji_color_class = "player-circle" if cell_result == "P" else "banker-circle"
                
                tie_html = ""
                if tie_count > 0:
                    tie_html = f"<div class='tie-oval'>{tie_count}</div>"
                
                natural_indicator = ""
                if natural_flag:
                    natural_indicator = f"<span class='natural-indicator'>N</span>"
                
                cell_content = (
                    f"<div class='big-road-circle {emoji_color_class}'>"
                    f"{natural_indicator}"
                    f"</div>"
                    f"{tie_html}"
                )
            
            big_road_html_parts.append(f"<div class='big-road-cell'>{cell_content}</div>")
        big_road_html_parts.append("</div>")
    big_road_html_parts.append("</div>")

    st.markdown("".join(big_road_html_parts), unsafe_allow_html=True)

else:
    st.info("🔄 ยังไม่มีข้อมูล")


col_p_b_t = st.columns(3)

# The buttons will now always record the actual result,
# and the prediction_data['recommendation'] will be passed.
# If prediction_data['prediction'] is '?', then recommendation will be 'Avoid ❌'
# If prediction_data['prediction'] is P/B/T, then recommendation will be 'Play ✅'
if prediction_data: # If prediction_data is available (history >= 20)
    with col_p_b_t[0]:
        if st.button(f"บันทึก: 🔵 P", key="result_P", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'P', prediction_data['recommendation'])
    with col_p_b_t[1]:
        if st.button(f"บันทึก: 🔴 B", key="result_B", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'B', prediction_data['recommendation'])
    with col_p_b_t[2]:
        if st.button(f"บันทึก: 🟢 T", key="result_T", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'T', prediction_data['recommendation'])
else: # Initial state or insufficient history (prediction_data is None)
    with col_p_b_t[0]:
        if st.button(f"บันทึก: 🔵 P", key="init_P", use_container_width=True):
            record_bet_result('?', 'P', "Avoid ❌") # No prediction yet, so '?' and 'Avoid'
    with col_p_b_t[1]:
        if st.button(f"บันทึก: 🔴 B", key="init_B", use_container_width=True):
            record_bet_result('?', 'B', "Avoid ❌")
    with col_p_b_t[2]:
        if st.button(f"บันทึก: 🟢 T", key="init_T", use_container_width=True):
            record_bet_result('?', 'T', "Avoid ❌")


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
