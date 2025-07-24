import streamlit as st
import pandas as pd
import asyncio
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data, get_gemini_analysis

# --- Page Configuration ---
st.set_page_config(
    page_title="Oracle AI Baccarat Predictor",
    page_icon="🔮",
    layout="centered", # 'centered' or 'wide'
    initial_sidebar_state="collapsed" # 'auto', 'expanded', 'collapsed'
)

# --- Initialize Session State ---
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'drawdown' not in st.session_state:
    st.session_state.drawdown = 0 # Track current drawdown (consecutive losses when following prediction)
if 'bet_log' not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=['Hand', 'Predict', 'Actual', 'Recommendation', 'Outcome'])
if 'gemini_analysis_result' not in st.session_state:
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
if 'gemini_analysis_loading' not in st.session_state:
    st.session_state.gemini_analysis_loading = False
if 'show_big_road_tooltip' not in st.session_state:
    st.session_state.show_big_road_tooltip = False


# --- Helper Function for Big Road Display ---
def display_big_road(big_road_data):
    """
    Renders the Big Road visualization using Streamlit components.
    Adjusted for better mobile viewing.
    """
    if not big_road_data:
        st.info("ไม่มีประวัติการเล่น (Big Road จะแสดงเมื่อมีผลลัพธ์).")
        return

    # Create a layout for Big Road columns
    # Using st.columns for individual cells is too slow and complex for large grids.
    # A better approach is to render it as a single HTML/Markdown table or image.
    # For simplicity, we'll use a basic text-based representation or a custom div.

    st.markdown("""
    <style>
    .big-road-container {
        display: flex;
        flex-wrap: nowrap; /* Prevent wrapping for horizontal scroll */
        overflow-x: auto; /* Enable horizontal scrolling */
        border: 1px solid #333;
        padding: 5px;
        background-color: #1a1a1a;
        min-height: 120px; /* Ensure minimum height */
    }
    .big-road-column {
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        margin: 0 2px;
    }
    .big-road-cell {
        width: 18px; /* Smaller size for mobile */
        height: 18px; /* Smaller size for mobile */
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 10px; /* Smaller font for mobile */
        font-weight: bold;
        color: white;
        margin: 1px;
        flex-shrink: 0; /* Prevent cells from shrinking */
    }
    .player-cell { background-color: #007bff; } /* Blue */
    .banker-cell { background-color: #dc3545; } /* Red */
    .s6-cell { background-color: #ffc107; color: black; } /* Yellow for Super 6 */
    .tie-text { 
        position: absolute; /* Position relative to the cell */
        font-size: 8px; /* Smaller font for tie */
        color: white;
        text-shadow: 1px 1px 2px black;
        top: 0;
        right: 0;
        line-height: 1; /* Adjust line height */
    }
    .tie-indicator {
        position: absolute;
        width: 6px; /* Small line for tie indicator */
        height: 6px;
        border-radius: 50%;
        background-color: green;
        top: 0;
        right: 0;
        transform: translate(50%, -50%); /* Move to top-right corner */
    }
    </style>
    """, unsafe_allow_html=True)

    big_road_html = '<div class="big-road-container">'
    for col in big_road_data:
        big_road_html += '<div class="big-road-column">'
        for cell_data in col:
            if cell_data:
                outcome, ties, is_natural = cell_data
                cell_class = ""
                cell_text = ""
                if outcome == 'P':
                    cell_class = "player-cell"
                    cell_text = ""
                elif outcome == 'B':
                    cell_class = "banker-cell"
                    cell_text = ""
                elif outcome == 'S6':
                    cell_class = "s6-cell"
                    cell_text = "S6" # Show S6 in the cell
                
                tie_html = f'<div class="tie-indicator"></div>' if ties > 0 else ''
                # Natural indicator (small line or corner) - can be added here if desired
                # natural_html = '<span style="position: absolute; bottom: 0; right: 0; font-size: 6px; color: green;">N</span>' if is_natural else ''

                big_road_html += f'<div class="big-road-cell {cell_class}" style="position: relative;">{cell_text}{tie_html}</div>'
            else:
                big_road_html += '<div class="big-road-cell" style="background-color: transparent;"></div>' # Empty cell for padding
        big_road_html += '</div>'
    big_road_html += '</div>'
    st.markdown(big_road_html, unsafe_allow_html=True)


# --- Callback Functions ---
def record_result(outcome_type):
    current_prediction_output = st.session_state.oracle_engine.predict_next(
        current_live_drawdown=st.session_state.drawdown,
        current_big_road_data=_build_big_road_data(st.session_state.history)
    )
    predicted_side = current_prediction_output.get('prediction', '?')
    recommended_action = current_prediction_output.get('recommendation', 'Avoid ❌')

    # Add the new hand to history
    # For ties and S6, assume 0 for now as card data is not tracked
    is_any_natural = False # Can't detect without card data
    new_hand_data = {'main_outcome': outcome_type, 'ties': 0, 'is_any_natural': is_any_natural}

    # If the outcome is S6, ensure 'main_outcome' is 'S6' and adjust 'ties' if needed
    if outcome_type == 'S6':
        new_hand_data['main_outcome'] = 'S6'
        # If S6 also resulted in a tie, this would need to be passed
        # For now, assuming S6 is a distinct outcome.

    if outcome_type == 'T':
        # If last hand was P or B, increment its tie count
        if st.session_state.history:
            last_hand_main_outcome = st.session_state.history[-1]['main_outcome']
            if last_hand_main_outcome in ['P', 'B', 'S6']:
                st.session_state.history[-1]['ties'] += 1
                # No new hand is added to history for a tie that attaches to a previous P/B/S6
                # However, for Big Road _display_ and backtesting, it's better to log the T.
                # Let's adjust history for display purposes, but main outcome logic should stick to P/B/S6
                # This part is tricky. For simplified history logging:
                st.session_state.history.append(new_hand_data)
            else:
                # If T is the very first hand or consecutive T's, just add it.
                st.session_state.history.append(new_hand_data)
        else:
            st.session_state.history.append(new_hand_data)
    else:
        st.session_state.history.append(new_hand_data)

    # Update drawdown and bet log AFTER history is updated
    outcome_status = "Recorded"
    if predicted_side != '?': # Only evaluate outcome if a prediction was made
        is_correct = False
        if predicted_side == outcome_type:
            is_correct = True
        elif predicted_side == 'B' and outcome_type == 'S6': # Banker prediction correct if S6 wins
            is_correct = True

        if recommended_action == 'Play ✅':
            if is_correct:
                st.session_state.drawdown = 0 # Reset drawdown on a win
            else:
                st.session_state.drawdown += 1 # Increment drawdown on a loss
        # If recommendation was 'Avoid', drawdown is not affected by this hand's outcome.
    
    # Update learning states for the engine
    # Pass patterns/momentum/sequences *before* this hand was added to history.
    # We need to re-evaluate patterns/momentum/sequences based on the state *before* this hand for learning.
    # This implies running the detection functions on `st.session_state.history[:-1]` (previous state).
    # However, `_update_learning` is called *after* the history is updated, so it should use the *new* history state.
    # It's a bit of a chicken-and-egg problem for real-time update.
    # For now, let's assume _update_learning operates on the history it sees.
    st.session_state.oracle_engine._update_learning(
        predicted_outcome=predicted_side,
        actual_outcome=outcome_type, # Use the actual outcome just recorded
        patterns_detected=st.session_state.oracle_engine.detect_patterns(st.session_state.history, _build_big_road_data(st.session_state.history)),
        momentum_detected=st.session_state.oracle_engine.detect_momentum(st.session_state.history, _build_big_road_data(st.session_state.history)),
        sequences_detected=st.session_state.oracle_engine._detect_sequences(st.session_state.history)
    )

    # Add to Bet Log
    new_log_entry = pd.DataFrame([{
        'Hand': len(st.session_state.history),
        'Predict': predicted_side,
        'Actual': outcome_type,
        'Recommendation': recommended_action,
        'Outcome': outcome_status # Or "Win", "Loss", "Avoid" based on detailed logic
    }])
    st.session_state.bet_log = pd.concat([st.session_state.bet_log, new_log_entry], ignore_index=True)

    # Clear cache for backtest accuracy so it re-calculates on new data
    _cached_backtest_accuracy.clear()

def undo_last_hand():
    if st.session_state.history:
        st.session_state.history.pop() # Remove last hand
        if not st.session_state.bet_log.empty:
            st.session_state.bet_log = st.session_state.bet_log.iloc[:-1] # Remove last log entry
        
        # Recalculate drawdown from scratch based on the remaining history
        # This is more robust than trying to "undo" drawdown changes directly.
        st.session_state.drawdown = 0
        temp_engine_for_recalc = OracleEngine() # Use a temp engine for re-calc
        for i, hand_data in enumerate(st.session_state.history):
            if i >= 2: # Only calculate prediction from the 3rd hand onwards
                sim_prediction_output = temp_engine_for_recalc.predict_next(
                    current_live_drawdown=0, # Drawdown not tracked during this recalc
                    current_big_road_data=_build_big_road_data(st.session_state.history[:i])
                )
                sim_predicted_side = sim_prediction_output.get('prediction')
                sim_recommended_action = sim_prediction_output.get('recommendation')

                if sim_predicted_side != '?' and sim_recommended_action == 'Play ✅':
                    is_correct = False
                    if sim_predicted_side == hand_data['main_outcome']:
                        is_correct = True
                    elif sim_predicted_side == 'B' and hand_data['main_outcome'] == 'S6':
                        is_correct = True
                    
                    if is_correct:
                        st.session_state.drawdown = 0
                    else:
                        st.session_state.drawdown += 1
            
            # Simplified update for temp_engine_for_recalc's learning state for subsequent predictions
            if sim_predicted_side != '?': # Only if a prediction was made for that hand
                 temp_engine_for_recalc._update_learning(
                    predicted_outcome=sim_predicted_side,
                    actual_outcome=hand_data['main_outcome'],
                    patterns_detected=temp_engine_for_recalc.detect_patterns(st.session_state.history[:i+1], _build_big_road_data(st.session_state.history[:i+1])),
                    momentum_detected=temp_engine_for_recalc.detect_momentum(st.session_state.history[:i+1], _build_big_road_data(st.session_state.history[:i+1])),
                    sequences_detected=temp_engine_for_recalc._detect_sequences(st.session_state.history[:i+1])
                )

        # Reset engine's internal learning state for the last hand
        st.session_state.oracle_engine.reset_learning_states_on_undo()

        # Clear cache for backtest accuracy so it re-calculates
        _cached_backtest_accuracy.clear()

def reset_shoe():
    st.session_state.oracle_engine.reset_history()
    st.session_state.history = []
    st.session_state.drawdown = 0
    st.session_state.bet_log = pd.DataFrame(columns=['Hand', 'Predict', 'Actual', 'Recommendation', 'Outcome'])
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
    st.session_state.gemini_analysis_loading = False
    _cached_backtest_accuracy.clear() # Clear cache when starting new shoe

async def analyze_with_gemini_async():
    st.session_state.gemini_analysis_loading = True
    st.session_state.gemini_analysis_result = "กำลังวิเคราะห์ด้วย Gemini AI... กรุณารอสักครู่ ⏳"
    st.rerun() # Rerun to show loading message
    
    try:
        if len(st.session_state.history) < 5:
            st.session_state.gemini_analysis_result = "❗ ประวัติการเล่นไม่เพียงพอสำหรับการวิเคราะห์เชิงลึก (ต้องการอย่างน้อย 5 ตา)"
        else:
            analysis = await get_gemini_analysis(st.session_state.history)
            st.session_state.gemini_analysis_result = analysis
    except Exception as e:
        st.session_state.gemini_analysis_result = f"❌ เกิดข้อผิดพลาดในการเรียกใช้ Gemini AI: {e}"
    finally:
        st.session_state.gemini_analysis_loading = False
        st.rerun() # Rerun to show result

def analyze_with_gemini_sync():
    # Use asyncio.run for calling async function in a synchronous context if needed
    # For Streamlit buttons, direct async call is handled by asyncio.run in a wrapper.
    asyncio.run(analyze_with_gemini_async())


# --- UI Layout ---

# Header Section
st.markdown(
    """
    <style>
    .header-container {
        display: flex;
        align-items: center;
        gap: 15px; /* Space between icon and text */
        margin-bottom: 20px;
    }
    .header-text {
        font-size: 3em; /* Larger font for main title */
        font-weight: bold;
        color: gold; /* Gold color for "Oracle AI" */
        margin: 0;
        line-height: 1; /* Adjust line height for alignment */
    }
    .version-text {
        font-size: 1.2em; /* Smaller font for version */
        color: grey;
        margin: 0;
        line-height: 1;
        align-self: flex-end; /* Align to the bottom of the main text */
    }
    .magic-ball-icon {
        font-size: 3em; /* Icon size */
        line-height: 1; /* Align with text */
    }
    /* General improvements for mobile */
    .stButton>button {
        width: 100%; /* Make buttons full width */
        margin-bottom: 8px; /* Space between buttons */
        height: 50px; /* Taller buttons for easier tapping */
        font-size: 1.1em;
    }
    .stMarkdown h3 {
        margin-top: 25px;
        margin-bottom: 15px;
        color: #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="header-container">
        <span class="magic-ball-icon">🔮</span>
        <div>
            <p class="header-text">Oracle AI</p>
            <p class="version-text">v{}</p>
        </div>
    </div>
    """.format(st.session_state.oracle_engine.__version__),
    unsafe_allow_html=True
)


st.markdown("### บันทึกผลลัพธ์")
col_p, col_b = st.columns(2)
with col_p:
    st.button("P (Player)", on_click=record_result, args=('P',))
with col_b:
    st.button("B (Banker)", on_click=record_result, args=('B',))

col_t, col_s6 = st.columns(2)
with col_t:
    st.button("T (Tie)", on_click=record_result, args=('T',))
with col_s6:
    st.button("S6 (Super6)", on_click=record_result, args=('S6',))

st.button("Undo", on_click=undo_last_hand, help="ย้อนกลับตาที่แล้ว")
st.button("เริ่มต้นขอนใหม่", on_click=reset_shoe, help="ล้างประวัติทั้งหมดและเริ่มต้นใหม่")

# Manually trigger Gemini analysis
if not st.session_state.gemini_analysis_loading:
    st.button("วิเคราะห์ด้วย Gemini AI (แบบ Manual)", on_click=analyze_with_gemini_sync)
else:
    st.button("วิเคราะห์ด้วย Gemini AI (กำลังโหลด...) ⏳", disabled=True)


st.markdown("---") # Separator


# --- Prediction and Recommendation ---
st.markdown("### การทำนายและคำแนะนำ")
prediction_output = st.session_state.oracle_engine.predict_next(
    current_live_drawdown=st.session_state.drawdown,
    current_big_road_data=_build_big_road_data(st.session_state.history)
)

st.write(f"**ทำนาย:** <span style='font-size: 2em; font-weight: bold; color: {'red' if prediction_output['prediction'] == 'B' else ('blue' if prediction_output['prediction'] == 'P' else ('yellow' if prediction_output['prediction'] == 'S6' else 'white'))}'>{prediction_output['prediction']}</span>", unsafe_allow_html=True)
st.write(f"**คำแนะนำ:** <span style='font-size: 1.5em; font-weight: bold; color: {'green' if 'Play' in prediction_output['recommendation'] else 'red'}'>{prediction_output['recommendation']}</span>", unsafe_allow_html=True)
st.write(f"**ความมั่นใจโดยรวม:** <span style='font-size: 1.2em; font-weight: bold;'>{prediction_output['overall_confidence']:.1f}%</span>", unsafe_allow_html=True)
st.write(f"**ระดับความเสี่ยง:** <span style='font-size: 1.2em; font-weight: bold;'>{prediction_output['risk']}</span>", unsafe_allow_html=True)


# --- Drawdown Status ---
st.markdown("### สถานะ Drawdown")
drawdown_color = "green"
if st.session_state.drawdown >= 1: drawdown_color = "orange"
if st.session_state.drawdown >= 2: drawdown_color = "red"
if st.session_state.drawdown >= 3: drawdown_color = "#8b0000" # Dark red for critical

st.markdown(f"**Drawdown ปัจจุบัน:** <span style='font-size: 1.5em; font-weight: bold; color: {drawdown_color};'>{st.session_state.drawdown}</span>", unsafe_allow_html=True)
st.markdown(f"ระดับความเสี่ยงโดยรวม: **{prediction_output['risk']}** (จาก AI)")


# --- Tie / Super6 Opportunity ---
st.markdown("### โอกาส Tie / Super6")
tie_analysis = st.session_state.oracle_engine.get_tie_opportunity_analysis(st.session_state.history)
st.write(f"**โอกาส:** <span style='font-size: 1.5em; font-weight: bold; color: {'green' if tie_analysis['prediction'] == 'T' else 'white'}'>{tie_analysis['prediction']}</span>", unsafe_allow_html=True)
st.write(f"**ความมั่นใจ:** {tie_analysis['confidence']:.1f}%")
st.write(f"**เหตุผล:** {tie_analysis['reason']}")

st.markdown("---") # Separator


# --- Big Road Display ---
st.markdown("### ประวัติขอนปัจจุบัน (Big Road)")
current_big_road_data = _build_big_road_data(st.session_state.history)
display_big_road(current_big_road_data)

# Toggle Big Road explanation
st.toggle("แสดงคำอธิบาย Big Road", key="show_big_road_tooltip")
if st.session_state.show_big_road_tooltip:
    st.info("""
    **Big Road (บิ๊กโรด)** แสดงผลลัพธ์การเล่น Baccarat ในรูปแบบตาราง:
    * **วงกลมสีน้ำเงิน:** แทน Player Win
    * **วงกลมสีแดง:** แทน Banker Win (รวมถึง Super6)
    * **วงกลมสีเหลือง (ถ้ามี):** แทน Super6 Win (มีข้อความ 'S6' ข้างใน)
    * **เส้นทแยงมุมสีเขียว:** แสดง Tie (จะปรากฏบนวงกลม Player/Banker ล่าสุด)
    * **คอลัมน์ใหม่:** เริ่มขึ้นเมื่อผลลัพธ์เปลี่ยนจาก Player เป็น Banker หรือ Banker เป็น Player
    * **คอลัมน์เดียวกัน:** ผลลัพธ์เดิมจะเรียงลงมาในคอลัมน์เดียวกัน
    """)

st.markdown("---") # Separator


# --- Gemini AI Analysis ---
st.markdown("### การวิเคราะห์จาก Gemini AI")
# Display loading spinner or result
if st.session_state.gemini_analysis_loading:
    st.spinner("กำลังวิเคราะห์ด้วย Gemini AI... กรุณารอสักครู่ ⏳")
    # The actual text is set in analyze_with_gemini_async and will update after rerun
    st.write(st.session_state.gemini_analysis_result)
else:
    st.markdown(st.session_state.gemini_analysis_result)

st.markdown("---") # Separator

# --- Bet Log ---
st.markdown("### Bet Log")
if not st.session_state.bet_log.empty:
    st.dataframe(
        st.session_state.bet_log,
        hide_row_index=True,
        use_container_width=True, # Adjust to screen width
        height=(min(len(st.session_state.bet_log), 10) * 35) + 38 # Dynamic height up to 10 rows
    )
else:
    st.info("ไม่มีบันทึกการเดิมพัน")


# --- Historical Accuracy (Backtest) ---
st.markdown("### ความแม่นยำทางประวัติศาสตร์")
accuracy_results = _cached_backtest_accuracy(st.session_state.history, st.session_state.oracle_engine)

st.write(f"**ความแม่นยำโดยรวม (จาก {accuracy_results['total_bets']} ครั้งที่ทำนาย):** <span style='font-size: 1.2em; font-weight: bold; color: {'lightgreen' if accuracy_results['overall_accuracy'] >= 60 else 'orange'}'>{accuracy_results['overall_accuracy']:.2f}%</span>", unsafe_allow_html=True)
st.write(f"ความแม่นยำ Player: {accuracy_results['player_accuracy']:.2f}%")
st.write(f"ความแม่นยำ Banker: {accuracy_results['banker_accuracy']:.2f}%")
st.write(f"ความแม่นยำ Super6: {accuracy_results['s6_accuracy']:.2f}%")

st.markdown("---")
st.caption("Oracle AI v{} - Powered by Streamlit & Google Gemini API".format(st.session_state.oracle_engine.__version__))
