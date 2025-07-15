# streamlit_app.py
import streamlit as st
# Make sure oracle_core.py is in the same directory or accessible in PYTHONPATH
from oracle_core import OracleBrain, Outcome # Outcome is now a Literal, not an Enum

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle v2.7.3", layout="centered")

# --- Custom CSS for Styling ---
st.markdown("""
<style>
/* Import Sarabun font from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

html, body, [class*="st-emotion"] { /* Target Streamlit's main content div classes */
    font-family: 'Sarabun', sans-serif !important;
}
.big-title {
    font-size: 28px;
    text-align: center;
    font-weight: bold;
    color: #FF4B4B; /* Streamlit's default primary color */
    margin-bottom: 20px;
}
.predict-box {
    padding: 15px;
    background-color: #262730; /* Darker background for the box */
    border-radius: 12px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    text-align: center; /* Center content inside prediction box */
}
.predict-box h2 {
    margin: 10px 0;
    font-size: 40px;
    font-weight: bold;
}
.predict-box b {
    color: #FFD700; /* Gold color for emphasis */
}
.predict-box .st-emotion-cache-1c7y2vl { /* Target Streamlit's caption */
    font-size: 14px;
    color: #BBBBBB;
}

/* Miss Streak warning text */
.st-emotion-cache-1f1d6zpt p, .st-emotion-cache-1s04v0m p { /* Target text inside warning/error boxes */
    font-size: 14px; /* Reduced font size for miss streak text */
}


.big-road-container {
    width: 100%;
    overflow-x: auto; /* Allows horizontal scrolling if many columns */
    padding: 8px 0;
    background: #1A1A1A; /* Slightly darker background for the road */
    border-radius: 8px;
    white-space: nowrap; /* Keeps columns in a single line */
    display: flex; /* Use flexbox for columns */
    align-items: flex-start; /* Align columns to the top */
    min-height: 140px; /* Adjusted minimum height for the road */
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.3);
}
.big-road-column {
    display: inline-flex; /* Use inline-flex for vertical stacking within column */
    flex-direction: column;
    margin-right: 2px; /* Reduced margin between columns */
    border-right: 1px solid rgba(255,255,255,0.1); /* Separator between columns */
    padding-right: 2px; /* Reduced padding */
}
.big-road-cell {
    width: 20px; /* Further reduced size for smaller emoji */
    height: 20px; /* Further reduced size for smaller emoji */
    text-align: center;
    line-height: 20px; /* Adjusted line-height for new size */
    font-size: 14px; /* Smaller font for emojis */
    margin-bottom: 1px; /* Reduced margin between cells */
    border-radius: 50%; /* Make cells round */
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
    color: white; /* Default text color for ties */
    position: relative; /* For positioning tie count */
}
/* Specific colors for P, B, T */
.big-road-cell.P { background-color: #007BFF; } /* Blue for Player */
.big-road-cell.B { background-color: #DC3545; } /* Red for Banker */
.big-road-cell.T { background-color: #6C757D; } /* Gray for Tie (though not directly used for main cells) */
.big-road-cell .tie-count {
    font-size: 9px; /* Slightly smaller font for tie count */
    position: absolute;
    bottom: -1px; /* Adjusted position */
    right: -1px; /* Adjusted position */
    background-color: #FFD700; /* Gold background for prominence */
    color: #333; /* Dark text for contrast */
    border-radius: 50%;
    padding: 1px 3px; /* Reduced padding */
    line-height: 1;
    min-width: 14px; /* Ensure minimum width for single digit */
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2); /* Slightly smaller shadow */
}

/* Button styling */
.stButton>button {
    width: 100%;
    border-radius: 8px;
    font-size: 18px;
    font-weight: bold;
    padding: 10px 0;
    margin-bottom: 10px;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
}
/* Specific button colors */
#btn_P button { background-color: #007BFF; color: white; border: none; }
#btn_B button { background-color: #DC3545; color: white; border: none; }
#btn_T button { background-color: #6C757D; color: white; border: none; }
.stButton button[kind="secondary"] { /* For control buttons */
    background-color: #343A40;
    color: white;
    border: 1px solid #495057;
}
.stButton button[kind="secondary"]:hover {
    background-color: #495057;
}

/* Warning/Error messages */
.st-emotion-cache-1f1d6zpt { /* Target Streamlit warning box */
    background-color: #FFC10720; /* Light yellow with transparency */
    border-left: 5px solid #FFC107;
    color: #FFC107;
}
/* .st-emotion-cache-1f1d6zpt p { color: #FFC107; } */ /* Handled by general p selector */

.st-emotion-cache-1s04v0m { /* Target Streamlit error box */
    background-color: #DC354520; /* Light red with transparency */
    border-left: 5px solid #DC3545;
    color: #DC3545;
}
/* .st-emotion-cache-1s04v0m p { color: #DC3545; } */ /* Handled by general p selector */

.st-emotion-cache-13ln4z2 { /* Target Streamlit info box */
    background-color: #17A2B820; /* Light blue with transparency */
    border-left: 5px solid #17A2B8;
    color: #17A2B8;
}
/* .st-emotion-cache-13ln4z2 p { color: #17A2B8; } */ /* Handled by general p selector */

/* Accuracy by Module section */
h3 { /* Target h3 for "ความแม่นยำรายโมดูล" */
    font-size: 18px; /* Reduced font size for section header */
    margin-top: 20px;
    margin-bottom: 10px;
}
.st-emotion-cache-1kyxreq { /* Target st.write output for accuracy (p tag) */
    font-size: 14px; /* Reduced font size for accuracy lines */
    margin-bottom: 5px;
}

hr {
    border-top: 1px solid rgba(255,255,255,0.1);
    margin: 25px 0;
}
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
# Initialize session state variables if they don't exist
if 'oracle' not in st.session_state:
    st.session_state.oracle = OracleBrain()
if 'prediction' not in st.session_state:
    st.session_state.prediction = None
if 'source' not in st.session_state:
    st.session_state.source = None
if 'confidence' not in st.session_state:
    st.session_state.confidence = None
if 'pattern_name' not in st.session_state:
    st.session_state.pattern_name = None
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = False

# --- UI Callback Functions ---
def handle_click(outcome_str: str):
    """
    Handles button clicks for P, B, T outcomes.
    Adds the result to OracleBrain and updates the prediction.
    """
    # Pass the string directly, as Outcome is a Literal type in oracle_core.py
    st.session_state.oracle.add_result(outcome_str)
    
    # Get new prediction after adding result
    # The last return value from predict_next is miss_streak, which we don't need here directly
    prediction, source, confidence, pattern_code, _ = st.session_state.oracle.predict_next()
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    
    # Map pattern codes to Thai names
    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร P", "BBBB": "มังกร B",
        "PPBPP": "ปิงปองยาว P", "BBPBB": "ปิงปองยาว B",
        "PPPBBB": "สามตัวตัด B", "BBBPBB": "สามตัวตัด P",
        "PBBP": "คู่สลับ P", "BPPB": "คู่สลับ B"
    }
    # Get pattern name, default to pattern_code if not found, or None if no pattern_code
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    # Mark that initial message has been shown (or bypassed)
    if not st.session_state.initial_shown:
        st.session_state.initial_shown = True

def handle_remove():
    """
    Handles removing the last added result.
    """
    st.session_state.oracle.remove_last()
    # Re-predict after removal
    prediction, source, confidence, pattern_code, _ = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    
    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร P", "BBBB": "มังกร B",
        "PPBPP": "ปิงปองยาว P", "BBPBB": "ปิงปองยาว B",
        "PPPBBB": "สามตัวตัด B", "BBBPBB": "สามตัวตัด P",
        "PBBP": "คู่สลับ P", "BPPB": "คู่สลับ B"
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    # If history becomes too short for prediction, reset initial_shown flag
    p_count = st.session_state.oracle.history.count("P")
    b_count = st.session_state.oracle.history.count("B")
    if (p_count + b_count) < 20:
        st.session_state.initial_shown = False

def handle_reset():
    """
    Handles resetting the entire system.
    """
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.initial_shown = False # Reset initial message flag

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE</div>', unsafe_allow_html=True)

# --- Prediction Output Box ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำทำนาย:</b>", unsafe_allow_html=True)

# Determine what to display in the prediction box
if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(st.session_state.prediction, "❓")
    st.markdown(f"<h2>{emoji} <b>{st.session_state.prediction}</b></h2>", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence:.1f}%") # Format confidence to 1 decimal place
else:
    # Check if we are waiting for initial data (history < 20 non-ties)
    # and if the initial message hasn't been bypassed yet
    p_count = st.session_state.oracle.history.count("P")
    b_count = st.session_state.oracle.history.count("B")
    if (p_count + b_count) < 20 and not st.session_state.initial_shown:
        st.warning("⚠️ รอข้อมูลครบ 20 ตา (P/B) ก่อนเริ่มทำนาย")
    else:
        # This state means history is >= 20 non-ties, but predict_next returned None
        # (e.g., due to miss streak >= 6)
        miss = st.session_state.oracle.calculate_miss_streak()
        if miss >= 6:
            st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")
        else:
            st.info("⏳ กำลังวิเคราะห์ข้อมูล")

st.markdown("</div>", unsafe_allow_html=True)

# --- Miss Streak Warning ---
miss = st.session_state.oracle.calculate_miss_streak()
# Apply CSS class to warning/error messages for smaller text
st.warning(f"❌ แพ้ติดกัน: {miss} ครั้ง")
if miss == 3:
    st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
elif miss >= 6:
    st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")

# --- Big Road Display ---
st.markdown("<hr>", unsafe_allow_html=True) # Keep this HR for separation from prediction box
st.markdown("<b>🕒 Big Road:</b>", unsafe_allow_html=True)

history = st.session_state.oracle.history

if history:
    max_row = 6
    columns = []
    current_col = []
    last_non_tie_result = None
    
    for i, result in enumerate(history):
        if result == "T":
            # Add tie count to the *last* non-tie cell in the current_col or previous column
            # This logic assumes ties are attached to the preceding non-tie result.
            if current_col:
                # Increment tie count for the last cell in the current column
                # (result, tie_count)
                last_cell_idx = len(current_col) - 1
                current_col[last_cell_idx] = (current_col[last_cell_idx][0], current_col[last_cell_idx][1] + 1)
            elif columns:
                # If current_col is empty, it means the tie is for the last cell of the *previous* column
                last_col_idx = len(columns) - 1
                # Ensure there's at least one cell in the last column of columns
                if columns[last_col_idx]:
                    last_cell_in_prev_col_idx = len(columns[last_col_idx]) - 1
                    columns[last_col_idx][last_cell_in_prev_col_idx] = (
                        columns[last_col_idx][last_cell_in_prev_col_idx][0],
                        columns[last_col_idx][last_cell_in_prev_col_idx][1] + 1
                    )
                # If previous column is also empty, this tie is at the very beginning without a preceding P/B
                # In such a case, we'll effectively ignore it for Big Road display as per standard practice.
            continue # Continue to next history item after handling tie
        
        # Handle non-tie results (P or B)
        if result == last_non_tie_result:
            # Same result, continue current column
            if len(current_col) < max_row:
                current_col.append((result, 0)) # Add new cell, tie count starts at 0
            else:
                # Column is full, start a new column
                columns.append(current_col)
                current_col = [(result, 0)]
        else:
            # Different result, start a new column
            if current_col: # Only append if the current_col has elements
                columns.append(current_col)
            current_col = [(result, 0)]
            last_non_tie_result = result
            
    if current_col: # Add the last column if it's not empty
        columns.append(current_col)

    # Generate HTML for Big Road
    html = "<div class='big-road-container'>"
    for col in columns:
        html += "<div class='big-road-column'>"
        for cell_result, tie_count in col:
            emoji = "🔵" if cell_result == "P" else "🔴"
            tie_html = f"<span class='tie-count'>{tie_count}</span>" if tie_count > 0 else ""
            html += f"<div class='big-road-cell {cell_result}'>{emoji}{tie_html}</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons ---
# Use st.columns for button layout
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_P")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_B")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_T")

# --- Control Buttons ---
col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ลบรายการล่าสุด", on_click=handle_remove)
with col5:
    st.button("🔄 เริ่มใหม่ทั้งหมด", on_click=handle_reset)

# --- Accuracy by Module ---
st.markdown("### 📈 ความแม่นยำรายโมดูล")
modules = st.session_state.oracle.get_module_accuracy()
if modules:
    for name, acc in modules.items():
        st.write(f"✅ {name}: {acc:.1f}%") # Format accuracy to 1 decimal place
else:
    st.info("ยังไม่มีข้อมูลความแม่นยำ")

