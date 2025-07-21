import streamlit as st
import pandas as pd
import math # สำหรับฟังก์ชัน floor ใน Fibonacci
from oracle_engine import OracleEngine # Import the OracleEngine class

# --- Streamlit App Setup and CSS ---
st.set_page_config(page_title="🔮 Oracle AI", layout="centered")

st.markdown("""
    <style>
    /* CSS for the main title */
    .custom-title {
        font-family: 'Georgia', serif;
        font-size: 2.5rem; /* Adjusted from 3rem */
        text-align: center;
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    /* Reduce overall spacing of Streamlit elements */
    .stApp > header {
        display: none; /* Hide Streamlit Header */
    }
    .stApp {
        padding-top: 1rem; /* Reduce top padding of the screen */
        padding-bottom: 1rem; /* Reduce bottom padding of the screen */
    }
    .st-emotion-cache-z5fcl4 { /* Target specific class for block container */
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* CSS for labels of st.number_input, st.selectbox, st.text_input */
    .stNumberInput > label, .stSelectbox > label, .stTextInput > label {
        font-size: 0.95rem;
        font-weight: bold;
        margin-bottom: 0.1rem; /* Reduce bottom margin of label */
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
        color: #4CAF50; /* Green color */
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
        display: flex; /* Use flex to arrange columns */
        overflow-x: auto; /* Enable horizontal scrolling if content overflows */
        padding: 10px;
        background-color: #1a1a1a; /* Dark background for the road */
        border-radius: 8px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        min-height: 180px; /* Adjusted minimum height for 6 rows of smaller cells */
        align-items: flex-start; /* Align columns to the top */
        border: 1px solid #333; /* Subtle border */
    }

    .big-road-column {
        display: flex;
        flex-direction: column; /* Stack cells vertically */
        min-width: 26px; /* Adjusted minimum width for each column */
        margin-right: 1px; /* Smaller gap between columns */
    }

    .big-road-cell {
        width: 24px; /* Adjusted fixed width for circles */
        height: 24px; /* Adjusted fixed height for circles */
        display: flex;
        justify-content: center;
        align-items: center;
        position: relative;
        margin-bottom: 1px; /* Smaller gap between cells in a column */
        box-sizing: border-box; /* Include padding and border in element's total width and height */
    }

    .big-road-circle {
        width: 20px; /* Adjusted circle size */
        height: 20px; /* Adjusted circle size */
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.6em; /* Smaller font inside circle */
        font-weight: bold;
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
        box-sizing: border-box;
        /* Modern look: subtle shadow */
        box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.4);
    }

    .player-circle {
        background-color: #007bff; /* Blue */
    }

    .banker-circle {
        background-color: #dc3545; /* Red */
    }

    .tie-oval {
        position: absolute;
        top: -4px; /* Position above the circle */
        right: -4px; /* Position to the right of the circle */
        background-color: #28a745; /* Green */
        color: white;
        font-size: 0.55em; /* Smaller font for tie count */
        font-weight: bold;
        padding: 0px 3px; /* Smaller padding */
        border-radius: 6px; /* Oval shape */
        line-height: 1; /* Ensure text fits */
        z-index: 3; /* Ensure it's on top */
        border: 1px solid rgba(255,255,255,0.3); /* Subtle white border */
        box-shadow: 0px 0px 2px rgba(0, 0, 0, 0.5); /* Small shadow for pop */
    }

    .natural-indicator {
        position: absolute;
        bottom: 0px; /* Position at the bottom of the cell */
        right: 0px; /* Position at the right of the cell */
        font-size: 0.55em; /* Smaller font for natural indicator */
        color: #FFD700; /* Gold color for natural */
        font-weight: bold;
        line-height: 1; /* Remove extra line height */
        z-index: 2; /* Ensure natural indicator is on top */
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<div class="custom-title">🔮 Oracle AI</div>', unsafe_allow_html=True)

# --- Session State Initialization ---
if "history" not in st.session_state:
    # History will now store list of dicts:
    # {'main_outcome': 'P'/'B'/'T', 'ties': int, 'is_any_natural': bool}
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000.0
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100.0 # Initial default bet amount
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()

# --- Session State for Money Management Systems ---
if "money_management_system" not in st.session_state:
    st.session_state.money_management_system = "Fixed Bet" # Default system

# Martingale State
if "martingale_current_step" not in st.session_state:
    st.session_state.martingale_current_step = 0 # 0 = starting bet
if "martingale_base_bet" not in st.session_state:
    st.session_state.martingale_base_bet = 100.0 # Default starting bet
if "martingale_multiplier" not in st.session_state: # Initialize multiplier
    st.session_state.martingale_multiplier = 2.0
if "martingale_max_steps" not in st.session_state: # Initialize max steps
    st.session_state.martingale_max_steps = 5

# Fibonacci State
if "fibonacci_sequence" not in st.session_state:
    # Standard Fibonacci sequence (indexed from 0)
    st.session_state.fibonacci_sequence = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181]
if "fibonacci_current_index" not in st.session_state:
    st.session_state.fibonacci_current_index = 1 # Start with 1 unit (index 1)
if "fibonacci_unit_bet" not in st.session_state:
    st.session_state.fibonacci_unit_bet = 100.0 # Default unit bet
if "fibonacci_max_steps_input" not in st.session_state: # Initialize max steps input
    st.session_state.fibonacci_max_steps_input = len(st.session_state.fibonacci_sequence) - 1

# Labouchere State
if "labouchere_original_sequence" not in st.session_state:
    st.session_state.labouchere_original_sequence = [1.0, 2.0, 3.0, 4.0] # Default sequence
if "labouchere_current_sequence" not in st.session_state:
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()
if "labouchere_unit_bet" not in st.session_state:
    st.session_state.labouchere_unit_bet = 100.0 # Default unit bet

# --- Function to Calculate Next Bet Amount ---
def calculate_next_bet():
    """Calculates the next bet amount based on the selected money management system."""
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
            return st.session_state.martingale_base_bet # Revert to base bet if max steps reached

        return next_bet

    elif system == "Fibonacci":
        fib_seq = st.session_state.fibonacci_sequence
        current_idx = st.session_state.fibonacci_current_index
        max_steps = st.session_state.fibonacci_max_steps_input # Use value from input

        # Ensure index is within bounds of defined sequence
        if current_idx >= len(fib_seq) or current_idx > max_steps:
            st.warning(f"Fibonacci ถึงไม้สูงสุด ({max_steps}) หรือเกินลำดับแล้ว! จะใช้เงินเดิมพันหน่วย.")
            return st.session_state.fibonacci_unit_bet # Revert to unit bet

        next_bet = fib_seq[current_idx] * st.session_state.fibonacci_unit_bet
        return next_bet

    elif system == "Labouchere":
        current_seq = st.session_state.labouchere_current_sequence
        unit_bet = st.session_state.labouchere_unit_bet

        if not current_seq: # Sequence is empty, means target achieved
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

# --- Callback Functions for History and Betting Management ---
def remove_last_from_history():
    """Removes the last result from the session history and resets money management state."""
    if st.session_state.history:
        st.session_state.history.pop()
        # Also notify the engine to remove its last history item
        st.session_state.oracle_engine.remove_last() # This will also reset engine's learning/backtest data
    # Reset money management states on history removal (optional, but good for consistency)
    reset_money_management_state_on_undo()

def reset_all_history():
    """Resets all history, money balance, bet log, and creates a new OracleEngine instance."""
    st.session_state.history = []
    st.session_state.money_balance = 1000.0
    st.session_state.bet_log = []
    st.session_state.oracle_engine = OracleEngine() # Create a new Engine to reset Memory Logic
    reset_money_management_state() # Reset all money management states

def reset_money_management_state():
    """Resets the state of all money management systems to their initial values."""
    # Martingale
    st.session_state.martingale_current_step = 0
    # Fibonacci
    st.session_state.fibonacci_current_index = 1
    # Labouchere
    st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()

def reset_money_management_state_on_undo():
    """
    Resets the current money management system's state to its base.
    A true undo would require storing the state *before* each bet.
    """
    if st.session_state.money_management_system == "Martingale":
        st.session_state.martingale_current_step = 0
    elif st.session_state.money_management_system == "Fibonacci":
        st.session_state.fibonacci_current_index = 1
    elif st.session_state.money_management_system == "Labouchere":
        st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy()


def record_bet_result(predicted_side, actual_result):
    """
    Records the bet result, updates balance, and adjusts money management system state.
    Also updates the history with structured data for Big Road and notifies the engine.
    """
    bet_amt_for_log = st.session_state.bet_amount_calculated # Use the calculated bet amount for the log
    win_loss = 0.0
    outcome = "Miss"

    current_system = st.session_state.money_management_system

    # --- Calculate money in/out (based on actual result) ---
    # Money in/out is always calculated if a result is recorded (even if Avoid or no prediction)
    # But actual deduction/addition to balance only happens if "Play" was recommended.
    if predicted_side in ['P', 'B', 'T']: # If there was a prediction and recommended to Play
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
    else: # If predicted_side was '?' (no prediction) or 'Avoid' - no actual bet was placed for system
        win_loss = 0.0
        outcome = "Avoided" # Or "No Bet"
        # If recording a result for 'Avoid' or '?', money management state is not updated.

    # --- Update Money Management System State (only when "Play" was recommended) ---
    if predicted_side in ['P', 'B', 'T']: # If there was a prediction and recommended to Play
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
                st.session_state.fibonacci_current_index = 1 # Reset to start of sequence after a win
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
            else: # Sequence was already empty (completed last round) - treat as a new round for next calculation
                st.session_state.labouchere_current_sequence = st.session_state.labouchere_original_sequence.copy() # Reset for new round


    st.session_state.bet_log.append({
        "System": current_system,
        "Bet Amount": f"{bet_amt_for_log:.2f}",
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}",
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
    })

    # --- Update history with structured data for Big Road ---
    # If the actual result is a Tie, we increment the tie count of the last P/B result
    if actual_result == 'T':
        found_pb_for_tie = False
        for i in reversed(range(len(st.session_state.history))):
            if st.session_state.history[i]['main_outcome'] in ['P', 'B']:
                st.session_state.history[i]['ties'] += 1
                found_pb_for_tie = True
                break
        if not found_pb_for_tie: # If history is empty or only ties, add a new tie entry
            # If a tie is the very first result, or follows only ties, we still record it
            st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})
    else: # For P or B results, add a new entry
        st.session_state.history.append({'main_outcome': actual_result, 'ties': 0, 'is_any_natural': False})

    # --- Notify OracleEngine to update its learning based on the last prediction and actual result ---
    # To correctly update learning, we need the state of patterns/momentum *before* the current actual result.
    # This implies running detect_patterns/momentum on history *before* the current result.
    # Create a temporary engine instance to get patterns/momentum before current result
    temp_engine_for_learning = OracleEngine()
    # Set its history to be the state *before* the current result was added
    temp_engine_for_learning.history = st.session_state.history[:-1] if len(st.session_state.history) > 0 else []

    # Copy current learning stats to temp_engine_for_learning so it can update them
    # Use .copy() to create a shallow copy of the dictionaries to avoid AttributeError
    temp_engine_for_learning.pattern_stats = st.session_state.oracle_engine.pattern_stats.copy()
    temp_engine_for_learning.momentum_stats = st.session_state.oracle_engine.momentum_stats.copy()
    temp_engine_for_learning.failed_pattern_instances = st.session_state.oracle_engine.failed_pattern_instances.copy()

    patterns_before = temp_engine_for_learning.detect_patterns(temp_engine_for_learning.history)
    momentum_before = temp_engine_for_learning.detect_momentum(temp_engine_for_learning.history)

    # Only update learning if a prediction was made (i.e., not '?' or 'Avoid')
    if predicted_side in ['P', 'B', 'T']:
        st.session_state.oracle_engine._update_learning(
            predicted_outcome=predicted_side,
            actual_outcome=actual_result,
            patterns_detected=patterns_before,
            momentum_detected=momentum_before
        )


# Load and update Engine
engine = st.session_state.oracle_engine
# The engine's history will be updated from st.session_state.history
# by assigning it directly before prediction.
engine.history = st.session_state.history # Ensure engine has the latest history


# --- Capital Balance and Bet Amount ---
st.session_state.money_balance = st.number_input(
    "💰 เงินทุนปัจจุบัน:",
    min_value=0.0, # Can start at 0
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

# UI for Fixed Bet
if st.session_state.money_management_system == "Fixed Bet":
    st.session_state.bet_amount = st.number_input(
        "💸 เงินเดิมพันต่อตา (Fixed Bet):",
        min_value=1.0,
        value=st.session_state.bet_amount,
        step=10.0,
        format="%.2f",
        help="กำหนดจำนวนเงินที่คุณจะเดิมพันในแต่ละตา"
    )

# UI for Martingale
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
        min_value=1.1, # Must be greater than 1
        value=st.session_state.martingale_multiplier, # Use session state value
        step=0.1,
        format="%.1f",
        help="ตัวคูณเงินเดิมพันเมื่อแพ้ในระบบ Martingale"
    )
    st.session_state.martingale_max_steps = st.number_input(
        "🪜 จำนวนไม้สูงสุด Martingale (ป้องกันความเสี่ยง):",
        min_value=1,
        value=st.session_state.martingale_max_steps, # Use session state value
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบเงินเมื่อแพ้"
    )
    st.info(f"Martingale: ปัจจุบันอยู่ที่ไม้ที่ {st.session_state.martingale_current_step}")

# UI for Fibonacci
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
        value=st.session_state.fibonacci_max_steps_input, # Use session state value
        step=1,
        format="%d",
        help="จำนวนครั้งสูงสุดที่จะทบตามลำดับ Fibonacci"
    )
    st.info(f"Fibonacci: ปัจจุบันอยู่ที่ลำดับที่ {st.session_state.fibonacci_current_index} (ค่า {st.session_state.fibonacci_sequence[st.session_state.fibonacci_current_index]})")

# UI for Labouchere
elif st.session_state.money_management_system == "Labouchere":
    original_seq_str = ",".join([f"{s:.1f}" if s % 1 != 0 else f"{int(s)}" for s in st.session_state.labouchere_original_sequence])

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
    st.info(f"Labouchere: ลำดับปัจจุบัน: {', '.join([f'{x:.1f}' if x % 1 != 0 else f'{int(x)}' for x in st.session_state.labouchere_current_sequence]) if st.session_state.labouchere_current_sequence else 'ว่างเปล่า (เป้าหมายสำเร็จ!)'}")


# Calculate next bet amount
st.session_state.bet_amount_calculated = calculate_next_bet()
st.info(f"**จำนวนเงินที่ต้องเดิมพันตาถัดไป:** {st.session_state.bet_amount_calculated:.2f} บาท")


if len(st.session_state.history) < 20: # Use st.session_state.history directly
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(st.session_state.history)}** ตา)")

# --- Prediction and Display Results ---
st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None
next_pred_side = '?'
conf = 0

# Pass the actual history (list of dicts) to the engine for prediction
engine.history = st.session_state.history # Ensure engine has the latest history

if len(engine.history) >= 20:
    prediction_data = engine.predict_next()

    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score(engine.history) # Pass history to confidence_score

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f'<div class="prediction-text">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")

        with st.expander("🧬 Developer View"):
            st.write(prediction_data['developer_view'])
            st.write("--- Pattern Success Rates ---")
            st.write(engine.pattern_stats)
            st.write("--- Momentum Success Rates ---")
            st.write(engine.momentum_stats)
            st.write("--- Failed Pattern Instances ---")
            st.write(engine.failed_pattern_instances)
            st.write("--- Backtest Results ---")
            st.write(engine.backtest_accuracy()) # Display full backtest results
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
else:
    st.markdown("— (ประวัติไม่ครบ)")

# --- Big Road Display ---
st.markdown("<b>🛣️ Big Road:</b>", unsafe_allow_html=True) # Changed to bold tag

history_results = st.session_state.history # Use the structured history

if history_results:
    max_row = 6
    columns = []
    current_col = []
    last_non_tie_result = None

    for i, round_result in enumerate(history_results):
        # Ensure round_result is a dictionary and has 'main_outcome'
        if not isinstance(round_result, dict) or 'main_outcome' not in round_result:
            continue # Skip invalid history entries

        main_outcome = round_result['main_outcome']
        is_any_natural = round_result['is_any_natural'] # Assuming this is always False for now
        ties_on_cell = round_result['ties'] # Get ties count from the history object itself

        if main_outcome == "T":
            # Ties are handled by incrementing the tie count of the last P/B result
            # This logic is now handled in record_bet_result, so we just skip ties here for Big Road drawing
            continue # Skip to the next round if it's a Tie, as Ties don't form new columns in Big Road

        # If the current outcome is the same as the last non-tie outcome, continue the streak in the current column
        if main_outcome == last_non_tie_result:
            if len(current_col) < max_row: # Add to current column if space available
                current_col.append((main_outcome, ties_on_cell, is_any_natural))
            else: # If column is full, start a new column (tailing)
                columns.append(current_col)
                current_col = [(main_outcome, ties_on_cell, is_any_natural)]
        else: # If the current outcome is different, start a new column (new streak)
            if current_col: # Append existing column if not empty
                columns.append(current_col)
            current_col = [(main_outcome, ties_on_cell, is_any_natural)] # Start a new column with the new outcome
            last_non_tie_result = main_outcome # Update last non-tie result

    # Append the last current column if it's not empty after the loop
    if current_col:
        columns.append(current_col)

    MAX_DISPLAY_COLUMNS = 12 # Changed to 12 columns as requested
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:] # Display only the last N columns for recent history

    # Build the HTML string for the Big Road display
    big_road_html_parts = []
    big_road_html_parts.append(f"<div class='big-road-container' id='big-road-container-unique'>")
    for col in columns:
        big_road_html_parts.append("<div class='big-road-column'>")
        # Ensure that cells are always created up to max_row for consistent column height
        for row_idx in range(max_row):
            cell_content = ""
            if row_idx < len(col):
                cell_result, tie_count, natural_flag = col[row_idx]
                emoji_color_class = "player-circle" if cell_result == "P" else "banker-circle"
                
                tie_html = ""
                if tie_count > 0:
                    tie_html = f"<div class='tie-oval'>{tie_count}</div>"
                
                natural_indicator = ""
                if natural_flag: # Assuming natural_flag is True/False
                    natural_indicator = f"<span class='natural-indicator'>N</span>"
                
                cell_content = (
                    f"<div class='big-road-circle {emoji_color_class}'>"
                    f"{natural_indicator}" # Natural indicator inside the circle
                    f"</div>"
                    f"{tie_html}" # Tie oval outside the circle but within the cell for layering
                )
            
            big_road_html_parts.append(f"<div class='big-road-cell'>{cell_content}</div>")
        big_road_html_parts.append("</div>") # Close big-road-column
    big_road_html_parts.append("</div>") # Close big-road-container

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
                record_bet_result('?', 'P') # Pass '?' as predicted_side to indicate no actual bet
                st.rerun()
        with col_p_b_t[1]:
            if st.button(f"บันทึก: 🔴 B", key="no_bet_B", use_container_width=True):
                record_bet_result('?', 'B') # Pass '?' as predicted_side to indicate no actual bet
                st.rerun()
        with col_p_b_t[2]:
            if st.button(f"บันทึก: 🟢 T", key="no_bet_T", use_container_width=True):
                record_bet_result('?', 'T') # Pass '?' as predicted_side to indicate no actual bet
                st.rerun()
else: # Case when history is less than 20 or an error in engine
    with col_p_b_t[0]:
        if st.button(f"บันทึก: 🔵 P", key="init_P", use_container_width=True):
            record_bet_result('?', 'P') # Pass '?' as predicted_side
            st.rerun()
    with col_p_b_t[1]:
        if st.button(f"บันทึก: 🔴 B", key="init_B", use_container_width=True):
            record_bet_result('?', 'B') # Pass '?' as predicted_side
            st.rerun()
    with col_p_b_t[2]:
        if st.button(f"บันทึก: 🟢 T", key="init_T", use_container_width=True):
            record_bet_result('?', 'T') # Pass '?' as predicted_side
            st.rerun()

col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        st.rerun()
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun()

# --- Bet Log ---
st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# --- Footer ---
st.caption("ระบบวิเคราะห์ Oracle AI โดยคุณ")
