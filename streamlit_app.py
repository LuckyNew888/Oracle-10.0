import streamlit as st
from oracle_engine import OracleEngine
import pandas as pd
import math # สำหรับฟังก์ชัน floor ใน Fibonacci

# --- ตั้งค่าหน้าเว็บและ CSS ---
st.set_page_config(page_title="🔮 Oracle AI", layout="centered")

st.markdown("""
    <style>
    /* CSS สำหรับส่วนหัวข้อหลัก */
    .custom-title {
        font-family: 'Georgia', serif;
        font-size: 3rem;
        text-align: center;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    /* ลดระยะห่างโดยรวมขององค์ประกอบ Streamlit */
    .stApp > header {
        display: none; /* ซ่อน Header ของ Streamlit */
    }
    .stApp {
        padding-top: 1rem; /* ลด padding ด้านบนของหน้าจอ */
        padding-bottom: 1rem; /* ลด padding ด้านล่างของหน้าจอ */
    }
    .st-emotion-cache-z5fcl4 { /* Target specific class for block container */
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* CSS สำหรับ Label ของ st.number_input, st.selectbox, st.text_input */
    .stNumberInput > label, .stSelectbox > label, .stTextInput > label {
        font-size: 0.95rem;
        font-weight: bold;
        margin-bottom: 0.1rem; /* ลดระยะห่างด้านล่างของ label */
    }
    /* CSS สำหรับตัวเลขในช่อง input ของ st.number_input */
    .stNumberInput div[data-baseweb="input"] input {
        font-size: 0.95rem;
    }
    /* CSS สำหรับประวัติผลย้อนหลัง */
    .history-display {
        font-size: 1.2rem;
        word-wrap: break-word;
        background-color: #262730; /* สีเทาเข้มเข้ากับธีมมืด */
        padding: 10px;
        border-radius: 5px;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        min-height: 40px;
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
    }
    /* CSS สำหรับหัวข้อ h4 ที่ต้องการให้เล็กและกระชับ */
    h4 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 1.25rem;
    }
    /* CSS สำหรับผลการทำนาย (ใหญ่ขึ้น) */
    .prediction-text {
        font-size: 2rem;
        font-weight: bold;
        color: #4CAF50; /* สีเขียว */
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    /* ลด margin ของปุ่ม */
    div.stButton > button {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }
    /* ลด margin ของ st.columns */
    div.stColumns > div {
        padding-top: 0.1rem;
        padding-bottom: 0.1rem;
    }
    /* ลด margin ของ info/warning boxes */
    .stAlert {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ส่วนหัวของแอป
st.markdown('<div class="custom-title">🔮 Oracle AI</div>', unsafe_allow_html=True)

# --- การเริ่มต้น Session State ---
if "history" not in st.session_state:
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000.0
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100.0 # Initial default bet amount
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()

# --- Session State สำหรับระบบเดินเงิน ---
if "money_management_system" not in st.session_state:
    st.session_state.money_management_system = "Fixed Bet" # Default system

# Martingale State
if "martingale_current_step" not in st.session_state:
    st.session_state.martingale_current_step = 0 # 0 = starting bet
if "martingale_base_bet" not in st.session_state:
    st.session_state.martingale_base_bet = 100.0 # Default starting bet

# Fibonacci State
if "fibonacci_sequence" not in st.session_state:
    # Standard Fibonacci sequence (indexed from 0)
    st.session_state.fibonacci_sequence = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181]
if "fibonacci_current_index" not in st.session_state:
    st.session_state.fibonacci_current_index = 1 # Start with 1 unit (index 1)
if "fibonacci_unit_bet" not in st.session_state:
    st.session_state.fibonacci_unit_bet = 100.0 # Default unit bet

# Labouchere State
if "labouchere_original_sequence" not in st.session_state:
    st.session_state.labouchere_original_sequence = [1.0, 2.0, 3.0, 4.0] # Default sequence
if "labouchere_current_sequence" not in st.session_state:
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()
if "labouchere_unit_bet" not in st.session_state:
    st.session_state.labouchere_unit_bet = 100.0 # Default unit bet

# --- ฟังก์ชันคำนวณเงินเดิมพันสำหรับตาถัดไป ---
def calculate_next_bet():
    system = st.session_state.money_management_system
    
    if system == "Fixed Bet":
        return st.session_state.bet_amount
    
    elif system == "Martingale":
        # Calculate current bet based on step and base bet
        current_bet_multiplier = st.session_state.martingale_multiplier ** st.session_state.martingale_current_step
        next_bet = st.session_state.martingale_base_bet * current_bet_multiplier
        
        # Check against Max Martingale Steps
        if st.session_state.martingale_current_step >= st.session_state.martingale_max_steps:
            st.warning(f"Martingale ถึงไม้สูงสุด ({st.session_state.martingale_max_steps}) แล้ว! จะใช้เงินเดิมพันฐาน.")
            return st.session_state.martingale_base_bet # กลับไปใช้ base bet หากถึงไม้สูงสุด

        return next_bet

    elif system == "Fibonacci":
        fib_seq = st.session_state.fibonacci_sequence
        current_idx = st.session_state.fibonacci_current_index
        max_steps = st.session_state.fibonacci_max_steps_input # ใช้ค่าจาก input

        # Ensure index is within bounds of defined sequence
        if current_idx >= len(fib_seq) or current_idx > max_steps:
            st.warning(f"Fibonacci ถึงไม้สูงสุด ({max_steps}) หรือเกินลำดับแล้ว! จะใช้เงินเดิมพันหน่วย.")
            return st.session_state.fibonacci_unit_bet # กลับไปใช้ unit bet

        next_bet = fib_seq[current_idx] * st.session_state.fibonacci_unit_bet
        return next_bet

    elif system == "Labouchere":
        current_seq = st.session_state.labouchere_current_sequence
        unit_bet = st.session_state.labouchere_unit_bet

        if not current_seq: # ลำดับหมดแล้ว หมายถึงชนะเป้าหมายแล้ว
            st.success("Labouchere: ลำดับครบเป้าหมายแล้ว! กำลังรีเซ็ตลำดับ.")
            st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()
            if not st.session_state.labouchere_current_sequence: # If original sequence is also empty, fallback
                return unit_bet # Fallback if original sequence is empty
            current_seq = st.session_state.labouchere_current_sequence # Update current_seq after reset

        if len(current_seq) == 1:
            next_bet = current_seq[0] * unit_bet
        else:
            next_bet = (current_seq[0] + current_seq[-1]) * unit_bet
        
        return next_bet
    
    return st.session_state.bet_amount # Fallback

# --- ฟังก์ชัน Callback สำหรับการจัดการประวัติและการเดิมพัน ---
def add_to_history(result):
    st.session_state.history.append(result)

def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
    # Reset money management states on history removal (optional, but good for consistency)
    reset_money_management_state_on_undo()

def reset_all_history():
    st.session_state.history = []
    st.session_state.money_balance = 1000.0
    st.session_state.bet_log = []
    st.session_state.oracle_engine = OracleEngine() # สร้าง Engine ใหม่ เพื่อรีเซ็ต Memory Logic
    reset_money_management_state() # รีเซ็ตสถานะการเดินเงินทั้งหมด

def reset_money_management_state():
    # Martingale
    st.session_state.martingale_current_step = 0
    # Fibonacci
    st.session_state.fibonacci_current_index = 1
    # Labouchere
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

def reset_money_management_state_on_undo():
    # This function would be more complex to truly "undo" a step in Martingale/Fibonacci/Labouchere
    # For simplicity, we just reset the current system's state to base.
    # A true undo would require storing the state *before* each bet.
    if st.session_state.money_management_system == "Martingale":
        st.session_state.martingale_current_step = 0
    elif st.session_state.money_management_system == "Fibonacci":
        st.session_state.fibonacci_current_index = 1
    elif st.session_state.money_management_system == "Labouchere":
        st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()


def record_bet_result(predicted_side, actual_result):
    bet_amt_for_log = st.session_state.bet_amount_calculated # Use the calculated bet amount for the log
    win_loss = 0.0
    outcome = "Miss"

    current_system = st.session_state.money_management_system

    # Update money management state based on actual result
    if current_system == "Martingale":
        if predicted_side == actual_result: # Win
            st.session_state.martingale_current_step = 0 # Reset step
        else: # Loss
            st.session_state.martingale_current_step += 1
            # Ensure not to exceed max steps
            if st.session_state.martingale_current_step > st.session_state.martingale_max_steps:
                st.session_state.martingale_current_step = st.session_state.martingale_max_steps

    elif current_system == "Fibonacci":
        fib_seq = st.session_state.fibonacci_sequence
        current_idx = st.session_state.fibonacci_current_index
        
        if predicted_side == actual_result: # Win
            # Go back two steps, but not below index 1 (0 is not used for betting)
            st.session_state.fibonacci_current_index = max(1, current_idx - 2)
        else: # Loss
            # Move to next step
            st.session_state.fibonacci_current_index += 1
            # Ensure not to exceed max steps or sequence length
            max_steps = st.session_state.fibonacci_max_steps_input
            if st.session_state.fibonacci_current_index >= len(fib_seq) or st.session_state.fibonacci_current_index > max_steps:
                st.session_state.fibonacci_current_index = max_steps # Cap at max_steps or end of defined sequence

    elif current_system == "Labouchere":
        current_seq = st.session_state.labouchere_current_sequence
        
        # Only modify sequence if it's not empty before this bet
        if current_seq:
            if predicted_side == actual_result: # Win
                if len(current_seq) <= 2: # If 1 or 2 numbers left, sequence becomes empty
                    st.session_state.labouchere_current_sequence = []
                else:
                    # Remove first and last element
                    st.session_state.labouchere_current_sequence = current_seq[1:-1]
            else: # Loss
                # Add the bet amount (converted to unit) to the end of the sequence
                # bet_amt_for_log / st.session_state.labouchere_unit_bet gives the 'unit' value
                if st.session_state.labouchere_unit_bet > 0:
                    st.session_state.labouchere_current_sequence.append(bet_amt_for_log / st.session_state.labouchere_unit_bet)
                else: # Prevent division by zero, just add a 1 unit
                    st.session_state.labouchere_current_sequence.append(1.0)
        else: # Sequence was already empty (completed last round)
            st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy() # Reset for new round

    # --- Calculation of Win/Loss for actual money balance ---
    # This part remains the same as it's about actual money change
    if predicted_side in ['P', 'B', 'T']: # Only if the system *intended* to bet
        if predicted_side == actual_result:
            outcome = "Hit"
            if actual_result == 'P':
                win_loss = bet_amt_for_log
            elif actual_result == 'B':
                win_loss = bet_amt_for_log * 0.95 # Banker deduction
            elif actual_result == 'T':
                win_loss = bet_amt_for_log * 8.0 # Tie payout
            st.session_state.money_balance += win_loss
        else: # Loss
            win_loss = -bet_amt_for_log
            st.session_state.money_balance -= bet_amt_for_log
    else: # If predicted_side was '?' or 'Avoid' - no actual bet was placed
        win_loss = 0.0
        outcome = "Avoided"

    st.session_state.bet_log.append({
        "System": current_system,
        "Bet Amount": f"{bet_amt_for_log:.2f}",
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}",
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
    })
    
    st.session_state.history.append(actual_result) # Add actual result to history for engine

# โหลดและอัปเดต Engine
engine = st.session_state.oracle_engine
engine.history = st.session_state.history.copy()

# --- สถานะเงินทุนและจำนวนเงินเดิมพัน ---
st.session_state.money_balance = st.number_input(
    "💰 เงินทุนปัจจุบัน:",
    min_value=0.0, # ให้สามารถเริ่มต้นที่ 0 ได้
    value=st.session_state.money_balance,
    step=100.0,
    format="%.2f",
    help="กำหนดจำนวนเงินทุนเริ่มต้นของคุณ"
)

# --- เลือกและตั้งค่าระบบเดินเงิน ---
st.session_state.money_management_system = st.selectbox(
    "📊 เลือกระบบเดินเงิน:",
    ("Fixed Bet", "Martingale", "Fibonacci", "Labouchere"),
    key="select_money_system"
)

# UI สำหรับ Fixed Bet
if st.session_state.money_management_system == "Fixed Bet":
    st.session_state.bet_amount = st.number_input(
        "💸 เงินเดิมพันต่อตา (Fixed Bet):",
        min_value=1.0,
        value=st.session_state.bet_amount,
        step=10.0,
        format="%.2f",
        help="กำหนดจำนวนเงินที่คุณจะเดิมพันในแต่ละตา"
    )

# UI สำหรับ Martingale
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
        min_value=1.1, # ต้องมากกว่า 1
        value=2.0,
        step=0.1,
        format="%.1f",
        help="ตัวคูณเงินเดิมพันเมื่อแพ้ในระบบ Martingale"
    )
    st.session_state.martingale_max_steps = st.number_input(
        "🪜 จำนวนไม้สูงสุด Martingale (ป้องกันความเสี่ยง):",
        min_value=1,
        value=5,
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบเงินเมื่อแพ้"
    )
    st.info(f"Martingale: ปัจจุบันอยู่ที่ไม้ที่ {st.session_state.martingale_current_step}")

# UI สำหรับ Fibonacci
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
        value=len(st.session_state.fibonacci_sequence) - 1, # Default to actual length of sequence
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบตามลำดับ Fibonacci"
    )
    st.info(f"Fibonacci: ปัจจุบันอยู่ที่ลำดับที่ {st.session_state.fibonacci_current_index} (ค่า {st.session_state.fibonacci_sequence[st.session_state.fibonacci_current_index]})")

# UI สำหรับ Labouchere
elif st.session_state.money_management_system == "Labouchere":
    original_seq_str = ",".join([str(s) for s in st.session_state.labouchere_original_sequence])
    
    new_original_seq_str = st.text_input(
        "🔢 ลำดับ Labouchere (คั่นด้วย , เช่น 1,2,3,4):",
        value=original_seq_str,
        help="กำหนดลำดับตัวเลขเริ่มต้นของ Labouchere"
    )
    # Parse the input string to update original_sequence
    try:
        parsed_seq = [float(x.strip()) for x in new_original_seq_str.split(',') if x.strip()]
        if parsed_seq: # Only update if parsed successfully and not empty
            if st.session_state.labouchere_original_sequence != parsed_seq:
                st.session_state.labouchere_original_sequence = parsed_seq
                st.session_state.labouchere_current_sequence = parsed_seq.copy() # Reset current sequence
        elif not parsed_seq and st.session_state.labouchere_original_sequence: # User cleared input
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
    st.info(f"Labouchere: ลำดับปัจจุบัน: {', '.join([f'{x:.1f}' for x in st.session_state.labouchere_current_sequence]) if st.session_state.labouchere_current_sequence else 'ว่างเปล่า (เป้าหมายสำเร็จ!)'}")


# คำนวณเงินเดิมพันสำหรับตาถัดไป
st.session_state.bet_amount_calculated = calculate_next_bet()
st.info(f"**จำนวนเงินที่ต้องเดิมพันตาถัดไป:** {st.session_state.bet_amount_calculated:.2f} บาท")


if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(engine.history)}** ตา)")

# --- การทำนายและแสดงผลลัพธ์ ---
st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None
next_pred_side = '?'
conf = 0

if len(engine.history) >= 20:
    prediction_data = engine.predict_next()

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score()

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f'<div class="prediction-text">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")

        with st.expander("🧬 Developer View"):
            st.write(prediction_data['developer_view'])
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
else:
    st.markdown("— (ประวัติไม่ครบ)")

# --- ส่วนบันทึกผลลัพธ์ + ประวัติ + ปุ่มควบคุม ---
st.markdown("#### 📝 บันทึกผลลัพธ์:")
history_emojis = engine.get_history_emojis()

if history_emojis:
    display_history_str = " ".join(history_emojis[-30:])
    if len(history_emojis) > 30:
        display_history_str = "... " + display_history_str
    st.markdown(f"<p class='history-display'>{display_history_str}</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลประวัติ")

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
        st.rerun()
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun()

# --- บันทึกการเดิมพัน (Bet Log) ---
st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# --- ข้อความปิดท้าย ---
st.caption("ระบบวิเคราะห์ Oracle AI โดยคุณ")
