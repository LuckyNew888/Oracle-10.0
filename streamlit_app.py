import streamlit as st
from collections import Counter
import random
import pandas as pd
import math # สำหรับฟังก์ชัน floor ใน Fibonacci

# --- OracleEngine Class (รวมอยู่ในไฟล์เดียวกับ Streamlit App เพื่อความสะดวก) ---
class OracleEngine:
    def __init__(self):
        self.history = []
        self.memory_failed_patterns = set()

    # --- ส่วน Data Management (สำหรับ Engine เอง) ---
    def update_history(self, result):
        """Adds a new result to the history."""
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def remove_last(self):
        """Removes the last result from the history."""
        if self.history:
            self.history.pop()

    def reset_history(self):
        """Resets the entire history and failed patterns memory."""
        self.history = []
        self.memory_failed_patterns = set()

    # --- 1. 🧬 DNA Pattern Analysis (ตรวจจับรูปแบบ) ---
    def detect_patterns(self):
        """
        Detects various patterns such as Pingpong, Two-Cut, Dragon, Broken Pattern, Triple Cut.
        """
        patterns = []
        h = self.history

        # Detect Pingpong (Alternating P/B pattern for a certain length)
        # Check for alternation from the end
        if len(h) >= 2: # Needs at least 2 results to alternate
            alternating_count = 0
            # Loop backwards from the last element to count alternations
            for i in range(len(h) - 1, 0, -1):
                if h[i] != h[i-1]:
                    alternating_count += 1
                else:
                    break # Stop counting if alternation ends

            # Consider it a clear Pingpong if there are at least 3 alternations (meaning 4 results like P-B-P-B)
            if alternating_count >= 3:
                patterns.append(f'Pingpong ({alternating_count + 1}x)') # +1 to show total results in the pattern

        # Detect Two-Cut (BB-PP or PP-BB)
        if len(h) >= 4:
            last4 = h[-4:]
            # Check if the first 2 are the same, the last 2 are the same, and the two pairs are different
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # Detect Dragon (long streak: 3 to 6 consecutive same results)
        for i in range(3, 7):
            if len(h) >= i:
                if len(set(h[-i:])) == 1: # If the last i elements are all the same
                    patterns.append(f'Dragon ({i})') # Indicate the length of the Dragon

        # Detect Triple Cut (e.g., PPPBBB or BBBPPP)
        if len(h) >= 6:
            last6 = h[-6:]
            # Check if the first 3 are the same, the last 3 are the same, and the first 3 are different from the last 3
            if (last6[0] == last6[1] == last6[2] and
                last6[3] == last6[4] == last6[5] and
                last6[0] != last6[3]):
                patterns.append('Triple Cut')

        # Detect Broken Pattern (BPBPPBP) - Example Implementation
        # **Note:** This logic is just a starting example. It should be refined based on the true definition.
        if len(h) >= 7:
            last7 = "".join(h[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7:
                patterns.append('Broken Pattern')

        return patterns

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self):
        """Detects momentum such as B3+, P3+, Steady Repeat."""
        momentum = []
        h = self.history

        # Check for Momentum (3 or more consecutive same results)
        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
            # Count consecutive same characters from the end
            for i in reversed(range(len(h))):
                if h[i] == last_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                momentum.append(f"{last_char}{streak_count}+ Momentum")

        # Detect Steady Repeat (PBPBPBP or BPBPBPB)
        if len(h) >= 7:
            seq = h[-7:]
            if (seq == ['P','B','P','B','P','B','P'] or
                seq == ['B','P','B','P','B','P','B']):
                momentum.append("Steady Repeat Momentum")

        return momentum

    # --- 3. ⚠️ Trap Zone Detection (ตรวจจับโซนอันตราย) ---
    def in_trap_zone(self):
        """Detects zones where changes are rapid and dangerous."""
        h = self.history
        if len(h) < 2:
            return False

        # P1-B1, B1-P1 (Unstable)
        last2 = h[-2:]
        if tuple(last2) in [('P','B'), ('B','P')]:
            return True

        # B3-P1 or P3-B1 (Risk of reversal) - 3 consecutive then cut
        if len(h) >= 4:
            if (len(set(h[-4:-1])) == 1 and h[-4] != h[-1]):
                return True
        return False

    # --- 4. 🎯 Confidence Engine (ระบบประเมินความมั่นใจ 0-100%) ---
    def confidence_score(self):
        """Calculates the system's confidence score for prediction."""
        if not self.history or len(self.history) < 10:
            return 0

        patterns = self.detect_patterns()
        momentum = self.detect_momentum()
        trap = self.in_trap_zone()

        score = 50

        if patterns:
            score += len(patterns) * 10

        if momentum:
            score += len(momentum) * 8

        if trap:
            score -= 60

        if score < 0:
            score = 0
        if score > 100:
            score = 100

        return score

    # --- 5. 🔁 Memory Logic (จดจำ Pattern ที่เคยพลาด) ---
    def update_failed_pattern(self, pattern_name):
        """Adds a pattern that led to an incorrect prediction to memory."""
        self.memory_failed_patterns.add(pattern_name)

    def is_pattern_failed(self, pattern_name):
        """Checks if this pattern has previously led to an incorrect prediction."""
        return pattern_name in self.memory_failed_patterns

    # --- 6. 🧠 Intuition Logic (ลอจิกเชิงลึกเมื่อไม่มี Pattern ชัดเจน) ---
    def intuition_predict(self):
        """Uses deep logic to predict when no clear pattern is present."""
        h = self.history
        if len(h) < 3:
            return '?'

        last3 = h[-3:]
        last4 = h[-4:] if len(h) >= 4 else None

        # Specific Tie patterns
        if 'T' in last3 and last3.count('T') == 1 and last3[0] != last3[1] and last3[1] != last3[2]:
            return 'T'
        if last4 and Counter(last4)['T'] >= 2:
            return 'T'

        # Specific P/B patterns
        if last3 == ['P','B','P']:
            return 'P'
        if last3 == ['B','B','P']:
            return 'P'
        if last3 == ['P','P','B']:
            return 'B'
        if len(h) >= 5 and h[-5:] == ['B','P','B','P','P']:
             return 'B'

        return '?'

    # --- 7. 🔬 Backtest Simulation (ทดสอบผลย้อนหลัง) ---
    def backtest_accuracy(self):
        """
        Calculates the system's accuracy from historical predictions (requires actual logic).
        And checks Drawdown.
        """
        if len(self.history) < 20:
            return 0

        # TODO: Implement actual backtesting simulation here
        return random.randint(60, 90) # Dummy accuracy value between 60-90%

    def backtest_drawdown_exceeded(self):
        """
        Checks if Drawdown (consecutive misses) exceeds 3 times (requires actual logic).
        """
        # TODO: Implement actual drawdown checking logic here
        return False # Assume not exceeded (dummy value)

    # --- ฟังก์ชันหลักในการทำนายผลถัดไป ---
    def predict_next(self):
        """
        Main function for analyzing and predicting the next outcome.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        # --- 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที) ---
        if self.in_trap_zone():
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = "Trap Zone detected: High volatility, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำกว่าเกณฑ์) ---
        score = self.confidence_score()
        if score < 60:
            recommendation = "Avoid ❌"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%), recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": "Low Confidence",
                "recommendation": recommendation
            }

        # --- 3. ตรวจสอบ Drawdown (หากเกิน 3 miss ติดกัน ให้งดเดิมพัน) ---
        if self.backtest_drawdown_exceeded():
            risk_level = "High Drawdown"
            recommendation = "Avoid ❌"
            developer_view = "Drawdown exceeded 3 consecutive misses, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 4. ใช้ Pattern หลักในการทำนาย (หากมี) ---
        patterns = self.detect_patterns()
        momentum = self.detect_momentum()

        if patterns:
            developer_view_patterns_list = []
            for pat_name in patterns:
                developer_view_patterns_list.append(pat_name)

                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self.is_pattern_failed(pat_name):
                    developer_view += f" (Note: Pattern '{pat_name}' previously failed. Skipping.)"
                    continue

                # ลอจิกการทำนายตาม Pattern ที่มั่นใจ
                if 'Dragon' in pat_name:
                    prediction_result = self.history[-1]
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting last result."
                    break
                elif 'Pingpong' in pat_name: # Updated to check if 'Pingpong' is in name
                    last = self.history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting opposite of last."
                    break
                elif pat_name == 'Two-Cut':
                    if len(self.history) >= 2:
                        last_two = self.history[-2:]
                        if last_two[0] == last_two[1]:
                            prediction_result = 'P' if last_two[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
                elif pat_name == 'Triple Cut': # Logic for Triple Cut
                    if len(self.history) >= 3:
                        last_three = self.history[-3:]
                        if len(set(last_three)) == 1: # E.g., PPP
                            # Predict the opposite of the current triple
                            prediction_result = 'P' if last_three[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Triple Cut detected. Predicting opposite of last three."
                            break

            if developer_view_patterns_list and not developer_view:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            elif developer_view_patterns_list:
                developer_view += f" | Other patterns: {', '.join(developer_view_patterns_list)}."

        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if prediction_result == '?': # ถ้ายังไม่มีการทำนายจาก Pattern หลัก
            intuitive_guess = self.intuition_predict()

            if intuitive_guess == 'T':
                prediction_result = 'T'
                developer_view += " (Intuition Logic: Specific Tie pattern identified.)"
            elif intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view += f" (Intuition Logic: Predicting {intuitive_guess} based on subtle patterns.)"
            else:
                recommendation = "Avoid ❌"
                risk_level = "Uncertainty"
                developer_view += " (Intuition Logic: No strong P/B/T prediction, recommending Avoid.)"
                prediction_result = '?'

        # รวบรวม Developer View เพิ่มเติมจาก Momentum
        if momentum:
            if developer_view: developer_view += " | "
            developer_view += f"Momentum: {', '.join(momentum)}."

        # หากไม่มีอะไรเลยและยังทำนายไม่ได้
        if not developer_view and prediction_result == '?':
            developer_view = "No strong patterns or intuition detected."

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": self.backtest_accuracy(),
            "risk": risk_level,
            "recommendation": recommendation
        }

    def _build_big_road(self, history, max_rows=6):
        """
        Builds the Big Road representation from the history.
        Returns a 2D list (grid) where each cell is a dict {'type': 'P'/'B', 'ties': count} or None.
        Handles column changes, vertical stacking, and horizontal tailing.
        Ties are marked on the last P/B result.
        """
        if not history:
            return []

        # This will store the data for each cell in the Big Road, with its calculated grid position
        # Format: {'type': 'P'/'B', 'ties': count, 'grid_col': int, 'grid_row': int}
        road_cells = []

        current_col_idx = 0
        current_row_idx = 0
        last_pb_type = None # Stores the type of the last P/B result to determine column breaks

        # Iterate through the history to determine cell types and positions
        for i, result in enumerate(history):
            if result == 'T':
                # Ties are marked on the last P/B cell.
                # Find the last P/B cell that was added to road_cells and increment its tie count.
                found_pb_for_tie = False
                for cell in reversed(road_cells):
                    if cell['type'] in ['P', 'B']: # Only attach ties to P or B cells
                        cell['ties'] += 1
                        found_pb_for_tie = True
                        break
                # If no P/B cell exists yet (e.g., history starts with 'T'), we ignore the tie for Big Road.
                # Standard Big Road doesn't start with standalone ties, they are usually overlays.
                continue # Ties do not advance the main P/B column/row logic

            # Handle P or B results
            if last_pb_type is None: # This is the very first P/B result
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})
            elif result == last_pb_type: # Same type as previous P/B, continue in current column
                if current_row_idx < max_rows - 1: # Still space to go down
                    current_row_idx += 1
                else: # Column is full, start tailing
                    current_col_idx += 1
                    # current_row_idx remains at max_rows - 1 for tailing
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})
            else: # Different type from previous P/B, start a new column
                current_col_idx += 1
                current_row_idx = 0 # Reset row for the new column
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})

            last_pb_type = result # Update the last P/B type

        # Now, convert the `road_cells` into a proper 2D grid for rendering
        if not road_cells:
            return []

        # Determine the maximum column index to size the grid correctly
        max_grid_col = max(cell['grid_col'] for cell in road_cells)
        # The grid will have `max_rows` rows and `max_grid_col + 1` columns
        big_road_grid = [[None for _ in range(max_grid_col + 1)] for _ in range(max_rows)]

        for cell in road_cells:
            big_road_grid[cell['grid_row']][cell['grid_col']] = {'type': cell['type'], 'ties': cell['ties']}

        return big_road_grid


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
        min-height: 200px; /* Minimum height for visibility (6 rows * ~30px height per cell) */
        align-items: flex-start; /* Align columns to the top */
        border: 1px solid #333; /* Subtle border */
    }

    .big-road-column {
        display: flex;
        flex-direction: column; /* Stack cells vertically */
        min-width: 30px; /* Minimum width for each column */
        margin-right: 2px; /* Small gap between columns */
    }

    .big-road-cell {
        width: 28px; /* Fixed width for circles */
        height: 28px; /* Fixed height for circles */
        display: flex;
        justify-content: center;
        align-items: center;
        position: relative;
        margin-bottom: 2px; /* Gap between cells in a column */
    }

    .big-road-circle {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.7em; /* Text inside circle if needed */
        font-weight: bold;
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
    }

    .player-circle {
        background-color: #007bff; /* Blue */
    }

    .banker-circle {
        background-color: #dc3545; /* Red */
    }

    .tie-line {
        position: absolute;
        width: 80%; /* Length of the line */
        height: 2px; /* Thickness of the line */
        background-color: #28a745; /* Green line */
        transform: rotate(45deg); /* Rotate for a slash */
        top: 50%;
        left: 10%;
        transform-origin: center;
        /* Ensure it's on top of the circle */
        z-index: 1;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<div class="custom-title">🔮 Oracle AI</div>', unsafe_allow_html=True)

# --- Session State Initialization ---
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
def add_to_history(result):
    """Adds a result to the session history."""
    st.session_state.history.append(result)

def remove_last_from_history():
    """Removes the last result from the session history and resets money management state."""
    if st.session_state.history:
        st.session_state.history.pop()
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

    st.session_state.history.append(actual_result) # Add actual result to history for engine

# Load and update Engine
engine = st.session_state.oracle_engine
engine.history = st.session_state.history.copy()

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


if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(engine.history)}** ตา)")

# --- Prediction and Display Results ---
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

# --- Big Road Display ---
st.markdown("#### 🛣️ Big Road (เค้าไพ่หลัก):")
big_road_data = engine._build_big_road(engine.history)

if big_road_data:
    html_parts = []
    html_parts.append('<div class="big-road-container">')

    max_display_cols = 0
    if big_road_data and big_road_data[0]:
        max_display_cols = len(big_road_data[0])

    # Limit display columns to, for example, 30. Adjust as needed.
    # This ensures the Big Road doesn't become excessively wide.
    display_limit = 30
    start_col_idx = max(0, max_display_cols - display_limit)

    for col_idx in range(start_col_idx, max_display_cols):
        html_parts.append('<div class="big-road-column">')
        for row_idx in range(len(big_road_data)): # Iterate through max_rows (6)
            cell_data = big_road_data[row_idx][col_idx]
            if cell_data:
                circle_class = "player-circle" if cell_data['type'] == 'P' else "banker-circle"
                tie_html = ''
                if cell_data['ties'] > 0:
                    tie_html = '<div class="tie-line"></div>'

                html_parts.append(f"""
                <div class="big-road-cell">
                    <div class="big-road-circle {circle_class}"></div>
                    {tie_html}
                </div>
                """)
            else:
                html_parts.append('<div class="big-road-cell"></div>') # Empty cell
        html_parts.append('</div>') # Close big-road-column
    html_parts.append('</div>') # Close big-road-container

    st.markdown("".join(html_parts), unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลสำหรับ Big Road (ประวัติไม่เพียงพอ)")


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
