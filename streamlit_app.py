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
    /* Specific styles for Tie and Super6 predictions */
    .prediction-text.tie {
        color: #28a745; /* Green for Tie */
    }
    .prediction-text.super6 {
        color: #FF8C00; /* Orange for Super6 */
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
    st.session_state.oracle_engine = OracleEngine() # This is the line that re-initializes
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
    # New: Ensure Tie/Super6 stats and weights are present for existing cached engine
    if not hasattr(st.session_state.oracle_engine, 'tie_stats'):
        st.session_state.oracle_engine.tie_stats = {}
    if not hasattr(st.session_state.oracle_engine, 'super6_stats'):
        st.session_state.oracle_engine.super6_stats = {}
    if not hasattr(st.session_state.oracle_engine, 'tie_weights'):
        st.session_state.oracle_engine.tie_weights = {
            'Tie After PBP': 0.7, 'Tie After BBP': 0.7, 'Consecutive Tie': 0.8, 'Tie Frequency Pattern': 0.6,
        }
    if not hasattr(st.session_state.oracle_engine, 'super6_weights'):
        st.session_state.oracle_engine.super6_weights = {
            'Super6 After B Streak': 0.6, 'Super6 After P Cut': 0.5,
        }


# --- Session State Initialization (other variables) ---
if "history" not in st.session_state:
    st.session_state.history = []
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []
if "last_prediction_data" not in st.session_state: # Store last prediction data for record_bet_result
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
if "live_drawdown" not in st.session_state: # Live consecutive loss counter
    st.session_state.live_drawdown = 0


# --- Callback Functions for History and Betting Management ---
def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        _cached_backtest_accuracy.clear()
        st.session_state.oracle_engine.reset_learning_states_on_undo()
        # Reset live_drawdown on undo, as the history has changed
        st.session_state.live_drawdown = 0 
    

def reset_all_history(): # This is now "Start New Shoe"
    st.session_state.history = []
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history() # Resets all learning states
    _cached_backtest_accuracy.clear()
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0 # Reset live_drawdown on new shoe


def record_bet_result(actual_result): # Simplified signature
    # Retrieve predicted_side and recommendation_status from session state
    predicted_side = st.session_state.last_prediction_data['prediction']
    recommendation_status = st.session_state.last_prediction_data['recommendation']
    
    outcome_status = "Recorded" # Default outcome status for log

    # --- Update live_drawdown based on the actual outcome and AI's prediction ---
    if predicted_side in ['P', 'B', 'T', 'S6']: # Include 'S6' in predictions that affect drawdown
        if predicted_side == actual_result:
            st.session_state.live_drawdown = 0 # Reset on a hit
        else:
            st.session_state.live_drawdown += 1 # Increment on a miss
    else: # If AI predicted '?' (no specific prediction)
        st.session_state.live_drawdown = 0 # Reset if AI made no specific prediction for this hand

    # --- Record Bet Log ---
    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Recommendation": recommendation_status, # Log the recommendation
        "Outcome": outcome_status # Simplified outcome
    })

    # --- Update History for Oracle Engine ---
    # This part should still happen to record the actual game outcome for future predictions
    # Note: For Super6, we need to decide how it's recorded in history.
    # For now, if actual_result is 'S6', it will be recorded as 'S6'.
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
        # If actual_result is 'S6', it will be treated as a main_outcome.
        # This simplifies the history structure for now.
        st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})

    # --- Update Oracle Engine's Learning States ---
    # Only update learning if a prediction was made (i.e., not '?' for predicted_side)
    # The _update_learning function now takes the full history for pattern detection
    # so we pass st.session_state.history directly.
    if predicted_side != '?':
        st.session_state.oracle_engine._update_learning(
            predicted_outcome=predicted_side,
            actual_outcome=actual_result,
            # Pass the full history to detect_patterns, momentum, sequences for learning
            # The methods themselves will handle slicing if needed.
            patterns_detected=st.session_state.oracle_engine.detect_patterns(st.session_state.history[:-1], _build_big_road_data(st.session_state.history[:-1])),
            momentum_detected=st.session_state.oracle_engine.detect_momentum(st.session_state.history[:-1], _build_big_road_data(st.session_state.history[:-1])),
            sequences_detected=st.session_state.oracle_engine._detect_sequences(st.session_state.history[:-1])
        )
    
    _cached_backtest_accuracy.clear()


engine = st.session_state.oracle_engine
engine.history = st.session_state.history

# --- Removed Money Management UI ---
st.sidebar.markdown("### ⚙️ การตั้งค่า")
# All money management UI elements removed as per user request.


if len(st.session_state.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(st.session_state.history)}** ตา)")

st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None # Initialize for the current run
next_pred_side = '?'
conf = 0
recommendation_status = "—"

# Get current_drawdown_display from session state
current_drawdown_display = st.session_state.live_drawdown

if len(engine.history) >= 20:
    prediction_data = engine.predict_next() # Calculate prediction for current state

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score(engine.history, _build_big_road_data(engine.history))
        recommendation_status = prediction_data['recommendation']
        
        # Store the current prediction data in session state for the next button click
        st.session_state.last_prediction_data = prediction_data

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', 'S6': '🟠 Super6', '?': '— ไม่มีคำแนะนำ'} # Added S6
        
        # Apply specific CSS class for Tie and Super6 predictions
        prediction_css_class = ""
        if next_pred_side == 'T':
            prediction_css_class = "tie"
        elif next_pred_side == 'S6':
            prediction_css_class = "super6"

        st.markdown(f'<div class="prediction-text {prediction_css_class}">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}") # Risk is now informational
        st.markdown(f"**🧾 คำแนะนำ:** **{recommendation_status}**")
        
        # Display Current Drawdown ONLY if a prediction was made (not '?')
        # As per the new logic, live_drawdown is 0 if next_pred_side is '?'.
        # So this condition ensures it only shows when there's an actual P/B/T/S6 prediction.
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
            st.write("--- Tie Prediction Stats ---") # New: Display Tie stats
            st.write(engine.tie_stats)
            st.write("--- Super6 Prediction Stats ---") # New: Display Super6 stats
            st.write(engine.super6_stats)
            st.write("--- Failed Pattern Instances ---")
            st.write(engine.failed_pattern_instances)
            st.write("--- Backtest Results ---")
            backtest_summary = _cached_backtest_accuracy(
                engine.history,
                engine.pattern_stats,
                engine.momentum_stats,
                engine.failed_pattern_instances,
                engine.sequence_memory_stats,
                engine.tie_stats, # Pass tie stats
                engine.super6_stats # Pass super6 stats
            )
            st.write(f"Accuracy: {backtest_summary['accuracy_percent']:.2f}% ({backtest_summary['hits']}/{backtest_summary['total_bets']})")
            st.write(f"Max Drawdown: {backtest_summary['max_drawdown']} misses")
            st.write(f"Current Drawdown (live): {st.session_state.live_drawdown} misses") # Display live drawdown here
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
        # Ensure last_prediction_data is reset if there's an error or no prediction
        st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
        st.session_state.live_drawdown = 0 # Reset live_drawdown on error
else:
    st.markdown("— (ประวัติไม่ครบ)")
    # Ensure last_prediction_data is reset if history is insufficient
    st.session_state.last_prediction_data = {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Uncertainty'}
    st.session_state.live_drawdown = 0 # Reset live_drawdown if history is insufficient


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
                
                # Special handling for Super6 display in Big Road (if we decide to show it there)
                # For now, Super6 is just another outcome like P/B/T in history.
                # If 'S6' is a main_outcome, it will be displayed as a new circle.
                # You might want to customize its appearance (e.g., a different color/icon).
                if cell_result == 'S6':
                    # Add a new CSS class for Super6 circles if you want a distinct visual
                    # For now, it will use banker-circle but add an S6 indicator.
                    # You can define .super6-circle { background-color: orange; } in CSS if desired.
                    emoji_color_class = "banker-circle" # Default to banker color for now
                    natural_indicator = f"<span class='natural-indicator'>S6</span>" # Indicate Super6

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
