import streamlit as st
import pandas as pd
import math
# Removed asyncio as it's no longer needed for Firestore operations
# Removed json as it's no longer needed for Firebase config or failed_pattern_instances serialization
# Removed uuid as it's no longer needed for anonymous user ID generation

# Removed Firebase imports
# from firebase_admin import credentials, firestore, auth, initialize_app
# import firebase_admin

# Import OracleEngine and helper functions
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data

# --- Firebase Initialization (Removed) ---
# All Firebase initialization logic has been removed.
# st.session_state.firebase_initialized = False # Ensure this is false if no Firebase

# --- Streamlit App Setup and CSS ---
st.set_page_config(page_title="🔮 Oracle AI", layout="centered")

st.markdown("""
    <style>
    /* CSS for the main title */
    .custom-title {
        font-family: 'Georgia', serif;
        font-size: 2.5rem;
        text-align: center;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        margin-bottom: 0.5rem;
        font-weight: bold;
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
        min-height: 180px;
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
st.markdown('<div class="custom-title">🔮 Oracle AI</div>', unsafe_allow_html=True)

# --- OracleEngine Caching ---
@st.cache_resource(ttl=None)
def get_oracle_engine():
    return OracleEngine()

if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = get_oracle_engine()

# --- Session State Initialization (other variables) ---
if "history" not in st.session_state:
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000.0
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100.0
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []

# Money Management Systems
if "money_management_system" not in st.session_state:
    st.session_state.money_management_system = "Fixed Bet"
if "martingale_current_step" not in st.session_state:
    st.session_state.martingale_current_step = 0
if "martingale_base_bet" not in st.session_state:
    st.session_state.martingale_base_bet = 100.0
if "martingale_multiplier" not in st.session_state:
    st.session_state.martingale_multiplier = 2.0
if "martingale_max_steps" not in st.session_state:
    st.session_state.martingale_max_steps = 5
if "fibonacci_sequence" not in st.session_state:
    st.session_state.fibonacci_sequence = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181]
if "fibonacci_current_index" not in st.session_state:
    st.session_state.fibonacci_current_index = 1
if "fibonacci_unit_bet" not in st.session_state:
    st.session_state.fibonacci_unit_bet = 100.0
if "fibonacci_max_steps_input" not in st.session_state:
    st.session_state.fibonacci_max_steps_input = len(st.session_state.fibonacci_sequence) - 1
if "labouchere_original_sequence" not in st.session_state:
    st.session_state.labouchere_original_sequence = [1.0, 2.0, 3.0, 4.0]
if "labouchere_current_sequence" not in st.session_state:
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()
if "labouchere_unit_bet" not in st.session_state:
    st.session_state.labouchere_unit_bet = 100.0

# --- Function to Calculate Next Bet Amount ---
def calculate_next_bet():
    system = st.session_state.money_management_system

    if system == "Fixed Bet":
        return st.session_state.bet_amount

    elif system == "Martingale":
        current_bet_multiplier = st.session_state.martingale_multiplier ** st.session_state.martingale_current_step
        next_bet = st.session_state.martingale_base_bet * current_bet_multiplier

        if st.session_state.martingale_current_step >= st.session_state.martingale_max_steps:
            st.warning(f"Martingale ถึงไม้สูงสุด ({st.session_state.martingale_max_steps}) แล้ว! จะใช้เงินเดิมพันฐาน.")
            return st.session_state.martingale_base_bet

        return next_bet

    elif system == "Fibonacci":
        fib_seq = st.session_state.fibonacci_sequence
        current_idx = st.session_state.fibonacci_current_index
        max_steps = st.session_state.fibonacci_max_steps_input

        if current_idx >= len(fib_seq) or current_idx > max_steps:
            st.warning(f"Fibonacci ถึงไม้สูงสุด ({max_steps}) หรือเกินลำดับแล้ว! จะใช้เงินเดิมพันหน่วย.")
            return st.session_state.fibonacci_unit_bet

        next_bet = fib_seq[current_idx] * st.session_state.fibonacci_unit_bet
        return next_bet

    elif system == "Labouchere":
        current_seq = st.session_state.labouchere_current_sequence
        unit_bet = st.session_state.labouchere_unit_bet

        if not current_seq:
            st.success("Labouchere: ลำดับครบเป้าหมายแล้ว! กำลังรีเซ็ตลำดับ.")
            st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()
            if not st.session_state.labouchere_current_sequence:
                return unit_bet
            current_seq = st.session_state.labouchere_current_sequence

        if len(current_seq) == 1:
            next_bet = current_seq[0] * unit_bet
        else:
            next_bet = (current_seq[0] + current_seq[-1]) * unit_bet

        return next_bet

    return st.session_state.bet_amount

# --- Callback Functions for History and Betting Management ---
def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        _cached_backtest_accuracy.clear()
        st.session_state.oracle_engine.reset_learning_states_on_undo()
    st.rerun()

def reset_all_history():
    st.session_state.history = []
    st.session_state.money_balance = 1000.0
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history()
    _cached_backtest_accuracy.clear()
    reset_money_management_state()
    st.rerun()

def reset_money_management_state():
    st.session_state.martingale_current_step = 0
    st.session_state.fibonacci_current_index = 1
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

def reset_money_management_state_on_undo():
    if st.session_state.money_management_system == "Martingale":
        st.session_state.martingale_current_step = 0
    elif st.session_state.money_management_system == "Fibonacci":
        st.session_state.fibonacci_current_index = 1
    elif st.session_state.money_management_system == "Labouchere":
        st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()


def record_bet_result(predicted_side, actual_result):
    bet_amt_for_log = st.session_state.bet_amount_calculated # This is the bet amount that *would* have been placed
    win_loss = 0.0
    outcome = "Avoided" # Default outcome if no prediction was made

    current_system = st.session_state.money_management_system

    # --- Core Logic for Win/Loss and Money Management ---
    # ONLY process win/loss and money management if a prediction was actually made (not 'Avoid')
    if predicted_side in ['P', 'B', 'T']:
        if predicted_side == actual_result: # Direct Hit
            outcome = "Hit"
            if actual_result == 'P':
                win_loss = bet_amt_for_log
            elif actual_result == 'B':
                win_loss = bet_amt_for_log * 0.95 # Banker commission
            elif actual_result == 'T':
                win_loss = bet_amt_for_log * 8.0 # Tie payout
            st.session_state.money_balance += win_loss

            # Reset money management system on win
            if current_system == "Martingale":
                st.session_state.martingale_current_step = 0
            elif current_system == "Fibonacci":
                st.session_state.fibonacci_current_index = 1
            elif current_system == "Labouchere":
                current_seq = st.session_state.labouchere_current_sequence
                if len(current_seq) <= 2:
                    st.session_state.labouchere_current_sequence = [] # Target achieved
                else:
                    st.session_state.labouchere_current_sequence = current_seq[1:-1] # Remove first and last
                if not st.session_state.labouchere_current_sequence: # If sequence becomes empty, reset for next target
                    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

        elif actual_result == 'T' and predicted_side in ['P', 'B']: # Tie when betting P or B (Push/No Action)
            win_loss = 0.0 # Money returned
            outcome = "Push (Tie)"
            # Money balance remains unchanged
            # Money management system state remains unchanged (no step/index change)
            
        else: # Miss (Loss for P/B/T bets)
            win_loss = -bet_amt_for_log
            st.session_state.money_balance = max(0.0, st.session_state.money_balance - bet_amt_for_log) # Ensure money_balance doesn't go below 0.0

            # Advance money management system on loss
            if current_system == "Martingale":
                st.session_state.martingale_current_step += 1
                if st.session_state.martingale_current_step > st.session_state.martingale_max_steps:
                    st.session_state.martingale_current_step = st.session_state.martingale_max_steps
            elif current_system == "Fibonacci":
                st.session_state.fibonacci_current_index += 1
                max_steps = st.session_state.fibonacci_max_steps_input
                if st.session_state.fibonacci_current_index >= len(st.session_state.fibonacci_sequence) or st.session_state.fibonacci_current_index > max_steps:
                    st.session_state.fibonacci_current_index = max_steps # Cap at max steps or end of sequence
            elif current_system == "Labouchere":
                current_seq = st.session_state.labouchere_current_sequence
                if st.session_state.labouchere_unit_bet > 0:
                    st.session_state.labouchere_current_sequence.append(bet_amt_for_log / st.session_state.labouchere_unit_bet)
                else:
                    st.session_state.labouchere_current_sequence.append(1.0) # Fallback if unit bet is zero/invalid
    # else: # If predicted_side is '?', it means "Avoid".
    #     # Money balance does not change.
    #     # Money management system state does not change.
    #     # win_loss remains 0.0 (initialized)
    #     outcome remains "Avoided" (initialized)


    # --- Record Bet Log ---
    st.session_state.bet_log.append({
        "System": current_system,
        "Bet Amount": f"{bet_amt_for_log:.2f}" if predicted_side in ['P', 'B', 'T'] else "0.00", # Show 0.00 if avoided
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}",
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
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
    # This condition is already correct as it only updates learning if a prediction was made and it wasn't a push.
    if predicted_side in ['P', 'B', 'T'] and not (actual_result == 'T' and predicted_side in ['P', 'B']):
        history_before_current_result = st.session_state.history[:-1] if len(st.session_state.history) > 0 else []
        big_road_data_before = _build_big_road_data(history_before_current_result)
        
        patterns_before = st.session_state.oracle_engine.detect_patterns(history_before_current_result, big_road_data_before)
        momentum_before = st.session_state.oracle_engine.detect_momentum(history_before_current_result, big_road_data_before)

        st.session_state.oracle_engine._update_learning(
            predicted_outcome=predicted_side,
            actual_outcome=actual_result,
            patterns_detected=patterns_before,
            momentum_detected=momentum_before
        )
    
    _cached_backtest_accuracy.clear()
    st.rerun()


engine = st.session_state.oracle_engine
engine.history = st.session_state.history

# --- User/Room ID Input (Removed) ---
st.sidebar.markdown("### ⚙️ การตั้งค่า")
# Removed Firebase authentication status and User ID display
# Removed Room ID input

# --- Capital Balance and Bet Amount ---
st.session_state.money_balance = st.number_input(
    "💰 เงินทุนปัจจุบัน:",
    min_value=0.0,
    value=st.session_state.money_balance,
    step=100.0,
    format="%.2f",
    help="กำหนดจำนวนเงินทุนเริ่มต้นของคุณ"
)

# --- Select and Configure Money Management System ---
st.session_state.money_management_system = st.selectbox(
    "📊 เลือกระบบเดินเงิน:",
    ("Fixed Bet", "Martingale", "Fibonacci", "Labouchere"),
    key="select_money_system"
)

if st.session_state.money_management_system == "Fixed Bet":
    st.session_state.bet_amount = st.number_input(
        "💸 เงินเดิมพันต่อตา (Fixed Bet):",
        min_value=1.0,
        value=st.session_state.bet_amount,
        step=10.0,
        format="%.2f",
        help="กำหนดจำนวนเงินที่คุณจะเดิมพันในแต่ละตา"
    )

elif st.session_state.money_management_system == "Martingale":
    st.session_state.martingale_base_bet = st.number_input(
        "💰 เงินเดิมพันเริ่มต้น Martingale:",
        min_value=1.0,
        value=st.session_state.martingale_base_bet,
        step=10.0,
        format="%.2f",
        help="เงินเดิมพันเริ่มต้นของระบบ Martingale"
    )
    st.session_state.martingale_multiplier = st.number_input(
        "✖️ ตัวคูณ Martingale (เช่น 2.0):",
        min_value=1.1,
        value=st.session_state.martingale_multiplier,
        step=0.1,
        format="%.1f",
        help="ตัวคูณเงินเดิมพันเมื่อแพ้ในระบบ Martingale"
    )
    st.session_state.martingale_max_steps = st.number_input(
        "🪜 จำนวนไม้สูงสุด Martingale (ป้องกันความเสี่ยง):",
        min_value=1,
        value=st.session_state.martingale_max_steps,
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบเงินเมื่อแพ้"
    )
    st.info(f"Martingale: ปัจจุบันอยู่ที่ไม้ที่ {st.session_state.martingale_current_step}")

elif st.session_state.money_management_system == "Fibonacci":
    st.session_state.fibonacci_unit_bet = st.number_input(
        "💸 เงินเดิมพันหน่วย Fibonacci:",
        min_value=1.0,
        value=st.session_state.fibonacci_unit_bet,
        step=10.0,
        format="%.2f",
        help="1 หน่วยในลำดับ Fibonacci จะเท่ากับเงินเท่าไหร่"
    )
    st.session_state.fibonacci_max_steps_input = st.number_input(
        "🪜 จำนวนไม้สูงสุด Fibonacci (ป้องกันความเสี่ยง):",
        min_value=1,
        value=st.session_state.fibonacci_max_steps_input,
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบตามลำดับ Fibonacci"
    )
    st.info(f"Fibonacci: ปัจจุบันอยู่ที่ลำดับที่ {st.session_state.fibonacci_current_index} (ค่า {st.session_state.fibonacci_sequence[st.session_state.fibonacci_current_index]})")

elif st.session_state.money_management_system == "Labouchere":
    original_seq_str = ",".join([f"{s:.1f}" if s % 1 != 0 else f"{int(s)}" for s in st.session_state.labouchere_original_sequence])

    new_original_seq_str = st.text_input(
        "🔢 ลำดับ Labouchere (คั่นด้วย , เช่น 1,2,3,4):",
        value=original_seq_str,
        help="กำหนดลำดับตัวเลขเริ่มต้นของ Labouchere"
    )
    try:
        parsed_seq = [float(x.strip()) for x in new_original_seq_str.split(',') if x.strip()]
        if parsed_seq:
            if st.session_state.labouchere_original_sequence != parsed_seq:
                st.session_state.labouchere_original_sequence = parsed_seq
                st.session_state.labouchere_current_sequence = parsed_seq.copy()
        elif not parsed_seq and st.session_state.labouchere_original_sequence:
             st.session_state.labouchere_original_sequence = []
             st.session_state.labouchere_current_sequence = []
    except ValueError:
        st.error("Invalid Labouchere sequence format. Please use numbers separated by commas.")

    st.session_state.labouchere_unit_bet = st.number_input(
        "💸 เงินเดิมพันหน่วย Labouchere:",
        min_value=1.0,
        value=st.session_state.labouchere_unit_bet,
        step=10.0,
        format="%.2f",
        help="1 หน่วยในลำดับ Labouchere จะเท่ากับเงินเท่าไหร่"
    )
    st.info(f"Labouchere: ลำดับปัจจุบัน: {', '.join([f'{x:.1f}' if x % 1 != 0 else f'{int(x)}' for x in st.session_state.labouchere_current_sequence]) if st.session_state.labouchere_current_sequence else 'ว่างเปล่า (เป้าหมายสำเร็จ!)'}")


st.session_state.bet_amount_calculated = calculate_next_bet()
st.info(f"**จำนวนเงินที่ต้องเดิมพันตาถัดไป:** {st.session_state.bet_amount_calculated:.2f} บาท")


if len(st.session_state.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(st.session_state.history)}** ตา)")

st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None
next_pred_side = '?'
conf = 0

engine = st.session_state.oracle_engine
engine.history = st.session_state.history

if len(engine.history) >= 20:
    prediction_data = engine.predict_next()

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score(engine.history, _build_big_road_data(engine.history))

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f'<div class="prediction-text">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")

        with st.expander("🧬 Developer View"):
            st.text(prediction_data['developer_view'])
            st.write("--- Pattern Success Rates ---")
            st.write(engine.pattern_stats)
            st.write("--- Momentum Success Rates ---")
            st.write(engine.momentum_stats)
            st.write("--- Failed Pattern Instances ---")
            st.write(engine.failed_pattern_instances)
            st.write("--- Backtest Results ---")
            backtest_summary = _cached_backtest_accuracy(
                engine.history,
                engine.pattern_stats,
                engine.momentum_stats,
                engine.failed_pattern_instances
            )
            st.write(f"Accuracy: {backtest_summary['accuracy_percent']:.2f}% ({backtest_summary['hits']}/{backtest_summary['total_bets']})")
            st.write(f"Max Drawdown: {backtest_summary['max_drawdown']} misses")
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
    max_row = 6
    columns = big_road_display_data

    MAX_DISPLAY_COLUMNS = 12
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:]

    big_road_html_parts = []
    big_road_html_parts.append(f"<div class='big-road-container' id='big-road-container-unique'>")
    for col in columns:
        big_road_html_parts.append("<div class='big-road-column'>")
        for row_idx in range(max_row):
            cell_content = ""
            if row_idx < len(col):
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

if prediction_data and isinstance(prediction_data, dict) and 'recommendation' in prediction_data:
    if prediction_data['recommendation'] == "Play ✅":
        with col_p_b_t[0]:
            if st.button(f"🔵 P", key="result_P_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'P')
                st.rerun()
        with col_p_b_t[1]:
            if st.button(f"🔴 B", key="result_B_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'B')
                st.rerun()
        with col_p_b_t[2]:
            if st.button(f"🟢 T", key="result_T_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'T')
                st.rerun()
    elif prediction_data['recommendation'] == "Avoid ❌":
        with col_p_b_t[0]:
            if st.button(f"บันทึก: 🔵 P", key="no_bet_P", use_container_width=True):
                record_bet_result('?', 'P')
                st.rerun()
        with col_p_b_t[1]:
            if st.button(f"บันทึก: 🔴 B", key="no_bet_B", use_container_width=True):
                record_bet_result('?', 'B')
                st.rerun()
        with col_p_b_t[2]:
            if st.button(f"บันทึก: 🟢 T", key="no_bet_T", use_container_width=True):
                record_bet_result('?', 'T')
                st.rerun()
else:
    with col_p_b_t[0]:
        if st.button(f"บันทึก: 🔵 P", key="init_P", use_container_width=True):
            record_bet_result('?', 'P')
            st.rerun()
    with col_p_b_t[1]:
        if st.button(f"บันทึก: 🔴 B", key="init_B", use_container_width=True):
            record_bet_result('?', 'B')
            st.rerun()
    with col_p_b_t[2]:
        if st.button(f"บันทึก: 🟢 T", key="init_T", use_container_width=True):
            record_bet_result('?', 'T')
            st.rerun()

col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        pass # Action handled by on_click
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        pass # Action handled by on_click

st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

st.caption("ระบบวิเคราะห์ Oracle AI โดยคุณ")
