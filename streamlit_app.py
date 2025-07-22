import streamlit as st
import pandas as pd
import math # สำหรับฟังก์ชัน floor ของ Fibonacci
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data # นำเข้า helper ใหม่

# --- ตั้งค่า Streamlit และ CSS ---
st.set_page_config(page_title="🔮 Oracle AI", layout="centered")

st.markdown("""
    <style>
    /* CSS สำหรับหัวข้อหลัก */
    .custom-title {
        font-family: 'Georgia', serif;
        font-size: 2.5rem;
        text-align: center;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    /* ซ่อน header ของ Streamlit */
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
    /* ปรับขนาด label ของ input ต่างๆ */
    .stNumberInput > label, .stSelectbox > label, .stTextInput > label {
        font-size: 0.95rem;
        font-weight: bold;
        margin-bottom: 0.1rem;
    }
    .stNumberInput div[data-baseweb="input"] input {
        font-size: 0.95rem;
    }
    h4 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 1.25rem;
    }
    /* ขนาดผลลัพธ์ทำนาย */
    .prediction-text {
        font-size: 2rem;
        font-weight: bold;
        color: #4CAF50;
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    div.stButton > button {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }
    div.stColumns > div {
        padding-top: 0.1rem;
        padding-bottom: 0.1rem;
    }
    .stAlert {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
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

# หัวข้อแอป
st.markdown('<div class="custom-title">🔮 ระบบวิเคราะห์ Oracle AI</div>', unsafe_allow_html=True)

# --- โหลด OracleEngine ด้วย cache ---
@st.cache_resource(ttl=None)
def get_oracle_engine():
    return OracleEngine()

if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = get_oracle_engine()

# --- กำหนด state เริ่มต้น ---
if "history" not in st.session_state:
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000.0
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100.0
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []

if "money_management_system" not in st.session_state:
    st.session_state.money_management_system = "เดิมพันคงที่"

if "martingale_current_step" not in st.session_state:
    st.session_state.martingale_current_step = 0
if "martingale_base_bet" not in st.session_state:
    st.session_state.martingale_base_bet = 100.0
if "martingale_multiplier" not in st.session_state:
    st.session_state.martingale_multiplier = 2.0
if "martingale_max_steps" not in st.session_state:
    st.session_state.martingale_max_steps = 5

if "fibonacci_sequence" not in st.session_state:
    st.session_state.fibonacci_sequence = [0,1,1,2,3,5,8,13,21,34,55,89,144,233,377,610,987,1597,2584,4181]
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

# --- ฟังก์ชันคำนวณเงินเดิมพันครั้งถัดไป ---
def calculate_next_bet():
    system = st.session_state.money_management_system

    if system == "เดิมพันคงที่":
        return st.session_state.bet_amount

    elif system == "มาร์ติงเกล":
        current_bet_multiplier = st.session_state.martingale_multiplier ** st.session_state.martingale_current_step
        next_bet = st.session_state.martingale_base_bet * current_bet_multiplier

        if st.session_state.martingale_current_step >= st.session_state.martingale_max_steps:
            st.warning(f"มาร์ติงเกลถึงขั้นสูงสุด ({st.session_state.martingale_max_steps}) แล้ว! ใช้เงินเดิมพันฐานแทน.")
            return st.session_state.martingale_base_bet

        return next_bet

    elif system == "ฟีโบนักชี":
        fib_seq = st.session_state.fibonacci_sequence
        current_idx = st.session_state.fibonacci_current_index
        max_steps = st.session_state.fibonacci_max_steps_input

        if current_idx >= len(fib_seq) or current_idx > max_steps:
            st.warning(f"ฟีโบนักชีถึงขั้นสูงสุด ({max_steps}) หรือเกินลำดับแล้ว! ใช้เงินเดิมพันหน่วยแทน.")
            return st.session_state.fibonacci_unit_bet

        next_bet = fib_seq[current_idx] * st.session_state.fibonacci_unit_bet
        return next_bet

    elif system == "ลาบูเชร์":
        current_seq = st.session_state.labouchere_current_sequence
        unit_bet = st.session_state.labouchere_unit_bet

        if not current_seq:
            st.success("ลาบูเชร์: ทำลำดับครบเป้าหมายแล้ว! กำลังรีเซ็ตลำดับ.")
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

# --- ฟังก์ชันจัดการประวัติและเดิมพัน ---
def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        _cached_backtest_accuracy.clear()
        st.session_state.oracle_engine.reset_learning_states_on_undo()
    reset_money_management_state_on_undo()

def reset_all_history():
    st.session_state.history = []
    st.session_state.money_balance = 1000.0
    st.session_state.bet_log = []
    st.session_state.oracle_engine.reset_history()
    _cached_backtest_accuracy.clear()
    reset_money_management_state()

def reset_money_management_state():
    st.session_state.martingale_current_step = 0
    st.session_state.fibonacci_current_index = 1
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

def reset_money_management_state_on_undo():
    if st.session_state.money_management_system == "มาร์ติงเกล":
        st.session_state.martingale_current_step = 0
    elif st.session_state.money_management_system == "ฟีโบนักชี":
        st.session_state.fibonacci_current_index = 1
    elif st.session_state.money_management_system == "ลาบูเชร์":
        st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

def record_bet_result(predicted_side, actual_result):
    bet_amt_for_log = st.session_state.bet_amount_calculated
    win_loss = 0.0
    outcome = "พลาด"

    current_system = st.session_state.money_management_system

    if predicted_side in ['P', 'B', 'T']:
        if predicted_side == actual_result:
            outcome = "ถูก"
            if actual_result == 'P':
                win_loss = bet_amt_for_log
            elif actual_result == 'B':
                win_loss = bet_amt_for_log * 0.95
            elif actual_result == 'T':
                win_loss = bet_amt_for_log * 8.0
            st.session_state.money_balance += win_loss
        else:
            win_loss = -bet_amt_for_log
            st.session_state.money_balance -= bet_amt_for_log
    else:
        win_loss = 0.0
        outcome = "หลีกเลี่ยง"

    if predicted_side in ['P', 'B', 'T']:
        if current_system == "มาร์ติงเกล":
            if predicted_side == actual_result:
                st.session_state.martingale_current_step = 0
            else:
                st.session_state.martingale_current_step += 1
                if st.session_state.martingale_current_step > st.session_state.martingale_max_steps:
                    st.session_state.martingale_current_step = st.session_state.martingale_max_steps

        elif current_system == "ฟีโบนักชี":
            fib_seq =
