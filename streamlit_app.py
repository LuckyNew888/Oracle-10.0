# streamlit_app.py
import streamlit as st
import time # Import time for unique timestamp
# Import RoundResult, MainOutcome, and the helper function _get_main_outcome_history
from oracle_core import OracleBrain, RoundResult, MainOutcome, _get_main_outcome_history 

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle V7.9.6", layout="centered") # Updated version to V7.9.6

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
    font-size: 14px; /* This is the target size for module/pattern/confidence */
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
    flex-direction: row; /* Display columns from left to right */
    align-items: flex-start; /* Align columns to the top */
    min-height: 140px; /* Adjusted minimum height for the road */
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.3);
}
.big-road-column {
    display: inline-flex; /* Use inline-flex for vertical stacking within column */
    flex-direction: column;
    margin-right: 2px; 
    border-right: 1px solid rgba(255,255,255,0.1); 
    padding-right: 2px; 
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
/* Styling for Natural indicator in Big Road (New for V6.5) */
.natural-indicator {
    position: absolute;
    font-size: 8px; /* Smaller font for indicators */
    font-weight: bold;
    color: white;
    line-height: 1;
    padding: 1px 2px;
    border-radius: 3px;
    z-index: 10;
    background-color: #4CAF50; /* Green for Natural */
    top: -2px;
    right: -2px;
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
/* Checkbox styling adjustments */
.stCheckbox > label {
    padding: 8px 10px; /* Adjust padding for better click area */
    border: 1px solid #495057;
    border-radius: 8px;
    background-color: #343A40;
    color: white;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 10px;
    display: flex; /* Use flex to align checkbox and text */
    align-items: center;
    justify-content: center; /* Center content horizontally */
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}
.stCheckbox > label:hover {
    background-color: #495057;
    transform: translateY(-2px);
    box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
}
.stCheckbox > label > div:first-child { /* The actual checkbox input */
    margin-right: 8px; /* Space between checkbox and text */
}
/* Style for checked checkboxes */
.stCheckbox > label[data-checked="true"] {
    background-color: #007BFF; /* Example color for checked */
    border-color: #007BFF;
}


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

.st-emotion-cache-1s04v0m { /* Target Streamlit error box */
    background-color: #DC354520; /* Light red with transparency */
    border-left: 5px solid #DC3545;
    color: #DC3545;
}

.st-emotion-cache-13ln4z2 { /* Target Streamlit info box */
    background-color: #17A2B820; /* Light blue with transparency */
    border-left: 5px solid #17A2B8;
    color: #17A2B8;
}

/* Accuracy by Module section */
h3 { /* Target h3 for "ความแม่นยำรายโมดูล" */
    font-size: 12px !important; /* Force this size */
    margin-top: 10px !important; 
    margin-bottom: 3px !important; 
}
/* Target for the custom class used for accuracy items */
.accuracy-item { 
    font-size: 10px !important; /* Force this size */
    margin-bottom: 1px !important; 
}

/* Sniper message styling */
.sniper-message {
    background-color: #4CAF50; /* Green background */
    color: white;
    padding: 10px;
    border-radius: 8px;
    font-weight: bold;
    text-align: center;
    margin-top: 15px;
    margin-bottom: 15px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    animation: pulse 1.5s infinite; /* Add a subtle pulse animation */
}

/* NEW: Side Bet Sniper message styling */
.side-bet-sniper-message {
    background-color: #007bff; /* Blue background for side bet sniper */
    color: white;
    padding: 8px;
    border-radius: 6px;
    font-weight: bold;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 10px;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
    animation: pulse 1.5s infinite; /* Keep pulse animation */
    font-size: 14px; /* Smaller font than main sniper */
}


@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.02); opacity: 0.9; }
    100% { transform: scale(1); opacity: 1; }
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
if 'prediction' not in st.session_state: # Main P/B prediction
    st.session_state.prediction = None
if 'source' not in st.session_state:
    st.session_state.source = None
if 'confidence' not in st.session_state:
    st.session_state.confidence = None
if 'pattern_name' not in st.session_state:
    st.session_state.pattern_name = None
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = False
if 'is_sniper_opportunity_main' not in st.session_state: # Renamed
    st.session_state.is_sniper_opportunity_main = False
if 'show_debug_info' not in st.session_state: # New session state for debug toggle
    st.session_state.show_debug_info = False

# Session state for side bet predictions
if 'tie_prediction' not in st.session_state:
    st.session_state.tie_prediction = None
if 'tie_confidence' not in st.session_state: # New for V7.3
    st.session_state.tie_confidence = None
# Removed pock_prediction and pock_confidence

# NEW: Session state for side bet sniper opportunities
if 'is_tie_sniper_opportunity' not in st.session_state:
    st.session_state.is_tie_sniper_opportunity = False
# Removed is_pock_sniper_opportunity

# Session state for checkboxes (to control their state)
# Removed is_any_natural_checked as it's only for Pock


# --- UI Callback Functions ---
def handle_click(main_outcome_str: MainOutcome): 
    """
    Handles button clicks for P, B, T outcomes.
    Reads checkbox states for side bets.
    Adds the result to OracleBrain and updates all predictions.
    """
    # is_any_natural is no longer needed for Pock, but RoundResult still expects it.
    # We can pass False as a default since Pock is removed.
    is_any_natural = False 

    # Call add_result with all information
    st.session_state.oracle.add_result(main_outcome_str, is_any_natural)
    
    # Reset checkboxes after adding result (no checkboxes now, but keep for consistency if needed later)
    # st.session_state.is_any_natural_checked = False # This line is removed as the checkbox is removed

    # Unpack all return values from predict_next (now includes side bet confidences)
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity) = st.session_state.oracle.predict_next() # Adjusted unpacking
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 
    
    # Update side bet predictions and their confidences
    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    # Removed pock_prediction and pock_confidence

    # Update side bet sniper opportunities
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    # Removed is_pock_sniper_opportunity

    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร", "BBBB": "มังกร", 
        "PPBPP": "ปิงปองยาว", "BBPBB": "ปิงปองยาว", 
        "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
        "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว",
        "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว",
        "PBB": "สองตัวตัด", "BPP": "สองตัวตัด",
        "PPBP": "สองตัวตัด", "BBPA": "สองตัวตัด",
        "PBPP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PBBPP": "สองตัวตัด", "BPBB": "สองตัวติด",
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "มังกรตัด": "มังกรตัด" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    # Check if enough P/B history for initial message
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) >= 20: 
        st.session_state.initial_shown = True 

    st.query_params["_t"] = f"{time.time()}"


def handle_remove():
    """
    Handles removing the last added result.
    """
    st.session_state.oracle.remove_last()
    # Unpack all return values from predict_next (now includes side bet confidences)
    (prediction, source, confidence, pattern_code, _, is_sniper_opportunity_main,
     tie_pred, tie_conf, 
     is_tie_sniper_opportunity) = st.session_state.oracle.predict_next() # Adjusted unpacking
    
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.is_sniper_opportunity_main = is_sniper_opportunity_main 

    # Update side bet predictions and their confidences
    st.session_state.tie_prediction = tie_pred
    st.session_state.tie_confidence = tie_conf
    # Removed pock_prediction and pock_confidence
    
    # Update side bet sniper opportunities
    st.session_state.is_tie_sniper_opportunity = is_tie_sniper_opportunity
    # Removed is_pock_sniper_opportunity
    
    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร", "BBBB": "มังกร", 
        "PPBPP": "ปิงปองยาว", "BBPBB": "ปิงปองยาว", 
        "PPPBBB": "สามตัวตัด", "BBBPBB": "สามตัวตัด",
        "PBBP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PPPPP": "มังกรยาว", "BBBBB": "มังกรยาว",
        "PBPBP": "ปิงปองยาว", "BPBPB": "ปิงปองยาว",
        "PBB": "สองตัวตัด", "BPP": "สองตัวตัด",
        "PPBP": "สองตัวตัด", "BBPA": "สองตัวตัด",
        "PBPP": "คู่สลับ", "BPPB": "คู่สลับ",
        "PBBPP": "สองตัวตัด", "BPBB": "สองตัวติด",
        "PBPBPB": "ปิงปองยาว", "BPBPBP": "ปิงปองยาว",
        "มังกรตัด": "มังกรตัด" 
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    # Re-check if initial message should be shown after removing
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    if (p_count + b_count) < 20: 
        st.session_state.initial_shown = False
    
    # Reset checkboxes on remove, as the last round's state is gone
    # st.session_state.is_any_natural_checked = False # This line is removed as the checkbox is removed

    st.query_params["_t"] = f"{time.time()}"


def handle_reset():
    """
    Handles resetting the entire system.
    """
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.initial_shown = False 
    st.session_state.is_sniper_opportunity_main = False 
    
    # Reset side bet predictions and confidences
    st.session_state.tie_prediction = None
    st.session_state.tie_confidence = None
    # Removed pock_prediction and pock_confidence

    # Reset side bet sniper opportunities
    st.session_state.is_tie_sniper_opportunity = False
    # Removed is_pock_sniper_opportunity

    # Reset checkboxes on full reset
    # st.session_state.is_any_natural_checked = False # This line is removed as the checkbox is removed

    st.query_params["_t"] = f"{time.time()}"

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE V7.9.6</div>', unsafe_allow_html=True) # Updated version to V7.9.6

# --- Prediction Output Box (Main Outcome) ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำทำนายหลัก:</b>", unsafe_allow_html=True) 

if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(st.session_state.prediction, "❓")
    st.markdown(f"<h2>{emoji} <b>{st.session_state.prediction}</b></h2>", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence:.1f}%") 
else:
    # Get P/B count from the new history structure
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    main_history_len = p_count + b_count
    miss = st.session_state.oracle.calculate_miss_streak()

    if main_history_len < 20 and not st.session_state.initial_shown: 
        st.warning(f"⚠️ รอข้อมูลครบ 20 ตา (P/B) ก่อนเริ่มทำนาย (ปัจจุบัน {main_history_len} ตา)") 
    elif miss >= 6:
        st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")
    else:
        # This message now appears if history is sufficient and not on miss streak, but confidence is too low
        st.info("⏳ กำลังวิเคราะห์ข้อมูล... ความมั่นใจยังไม่สูงพอที่จะทำนาย")

st.markdown("</div>", unsafe_allow_html=True)

# --- Sniper Opportunity Message (Main Outcome) ---
if st.session_state.is_sniper_opportunity_main: 
    st.markdown("""
        <div class="sniper-message">
            🎯 SNIPER! มั่นใจเป็นพิเศษ
        </div>
    """, unsafe_allow_html=True)

# --- Side Bet Prediction Display ---
# Removed the "คำทำนายเสริม:" header and conditional display for "เสมอ (ไม่มีทำนาย)"
# Now, it only renders if there's an actual prediction for Tie.
if st.session_state.tie_prediction and st.session_state.tie_confidence is not None:
    st.markdown("<b>📍 คำทำนายเสริม:</b>", unsafe_allow_html=True) # Only show header if there's a prediction
    col_side1, col_side_empty = st.columns(2) 
    with col_side1:
        st.markdown(f"<p style='text-align:center; color:#6C757D; font-weight:bold;'>⚪ เสมอ</p>", unsafe_allow_html=True)
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.tie_confidence:.1f}%")
        if st.session_state.is_tie_sniper_opportunity:
            st.markdown("""
                <div class="side-bet-sniper-message">
                    🎯 SNIPER เสมอ!
                </div>
            """, unsafe_allow_html=True)
    with col_side_empty:
        pass # This column is intentionally empty to maintain layout if needed, but no content

st.markdown("<hr>", unsafe_allow_html=True)

# --- Miss Streak Warning ---
miss = st.session_state.oracle.calculate_miss_streak()
st.warning(f"❌ แพ้ติดกัน: {miss} ครั้ง")
if miss == 3:
    st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
elif miss >= 6:
    st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")

# --- Big Road Display ---
st.markdown("<hr>", unsafe_allow_html=True) 
st.markdown("<b>🕒 Big Road:</b>", unsafe_allow_html=True)

history_results = st.session_state.oracle.history 

# Build the entire HTML string for Big Road in one go
if history_results:
    max_row = 6
    columns = []
    current_col = []
    last_non_tie_result = None
    
    for i, round_result in enumerate(history_results): 
        main_outcome = round_result.main_outcome
        is_any_natural = round_result.is_any_natural 

        if main_outcome == "T":
            if current_col:
                last_cell_idx = len(current_col) - 1
                current_col[last_cell_idx] = (current_col[last_cell_idx][0], current_col[last_cell_idx][1] + 1,
                                               current_col[last_cell_idx][2]) 
            elif columns:
                last_col_idx = len(columns) - 1
                if columns[last_col_idx]:
                    last_cell_in_prev_col_idx = len(columns[last_col_idx]) - 1
                    columns[last_col_idx][last_cell_in_prev_col_idx] = (
                        columns[last_col_idx][last_cell_in_prev_col_idx][0],
                        columns[last_col_idx][last_cell_in_prev_col_idx][1] + 1,
                        columns[last_col_idx][last_cell_in_prev_col_idx][2]
                    )
            continue
        
        if main_outcome == last_non_tie_result:
            if len(current_col) < max_row:
                current_col.append((main_outcome, 0, is_any_natural)) 
            else:
                columns.append(current_col)
                current_col = [(main_outcome, 0, is_any_natural)] 
        else:
            if current_col:
                columns.append(current_col)
            current_col = [(main_outcome, 0, is_any_natural)] 
            last_non_tie_result = main_outcome
            
    if current_col:
        columns.append(current_col)

    # Limit columns to display only the most recent 14 columns
    MAX_DISPLAY_COLUMNS = 14 
    if len(columns) > MAX_DISPLAY_COLUMNS:
        columns = columns[-MAX_DISPLAY_COLUMNS:] 

    # Generate the full HTML string for Big Road
    big_road_html = f"<div class='big-road-container' id='big-road-container-unique'>"
    for col in columns:
        big_road_html += "<div class='big-road-column'>"
        for cell_result, tie_count, natural_flag in col: 
            emoji = "🔵" if cell_result == "P" else "🔴"
            tie_html = f"<span class='tie-count'>{tie_count}</span>" if tie_count > 0 else ""
            
            # Natural indicator is still passed in RoundResult, but Pock is removed.
            # So, natural_flag will always be False unless the user manually sets it in the future.
            # For now, it will not display as Pock is removed.
            natural_indicator = f"<span class='natural-indicator'>N</span>" if natural_flag else ""

            big_road_html += f"<div class='big-road-cell {cell_result}'>{emoji}{tie_html}{natural_indicator}</div>" 
        big_road_html += "</div>" 
    big_road_html += "</div>" 
    
    st.markdown(big_road_html, unsafe_allow_html=True)

else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons (Main Outcomes) ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<b>ป้อนผล:</b>", unsafe_allow_html=True) 

col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_P")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_B")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_T")

# Removed checkboxes for side outcomes
# st.markdown("<b>ผลเสริม (เลือกก่อนกดปุ่มผลหลัก):</b>", unsafe_allow_html=True)
# col_checkbox1, col_checkbox2, col_checkbox3 = st.columns(3) 
# with col_checkbox1:
#     st.checkbox("🟢 ไพ่ป็อก", key="is_any_natural_checked") 


# --- Control Buttons ---
st.markdown("<hr>", unsafe_allow_html=True)
col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ลบรายการล่าสุด", on_click=handle_remove)
with col5:
    st.button("🔄 เริ่มใหม่ทั้งหมด", on_click=handle_reset)

# --- Debugging Toggle ---
st.markdown("<hr>", unsafe_allow_html=True)
st.session_state.show_debug_info = st.checkbox("แสดงข้อมูล Debugging")

# --- Conditional Debugging Output ---
if st.session_state.show_debug_info:
    st.markdown("<h3>⚙️ ข้อมูล Debugging (สำหรับนักพัฒนา)</h3>", unsafe_allow_html=True)
    st.write(f"ความยาวประวัติ P/B: {len(_get_main_outcome_history(st.session_state.oracle.history))}") 
    st.write(f"ผลทำนายหลัก (prediction): {st.session_state.prediction}")
    st.write(f"โมดูลที่ใช้ (source): {st.session_state.source}")
    st.write(f"ความมั่นใจ (confidence): {st.session_state.confidence}")
    st.write(f"แพ้ติดกัน (miss streak): {st.session_state.oracle.calculate_miss_streak()}")
    st.write(f"อัตราความผันผวน (Choppiness Rate): {st.session_state.oracle._calculate_choppiness_rate(st.session_state.oracle.history, 20):.2f}") 
    st.write(f"Sniper หลัก: {st.session_state.is_sniper_opportunity_main}")
    st.write(f"ทำนายเสมอ: {st.session_state.tie_prediction}, ความมั่นใจเสมอ: {st.session_state.tie_confidence}, Sniper เสมอ: {st.session_state.is_tie_sniper_opportunity}") # Updated debug info
    # Removed Pock debug info
    st.write("---") 


# --- Accuracy by Module ---
st.markdown("<h3>📈 ความแม่นยำรายโมดูล</h3>", unsafe_allow_html=True) 

all_time_accuracies = st.session_state.oracle.get_module_accuracy_all_time()
recent_10_accuracies = st.session_state.oracle.get_module_accuracy_recent(10)
recent_20_accuracies = st.session_state.oracle.get_module_accuracy_recent(20)

if all_time_accuracies:
    st.markdown("<h4>ความแม่นยำ (All-Time)</h4>", unsafe_allow_html=True)
    sorted_module_names = sorted(all_time_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) # Adjusted sort key
    for name in sorted_module_names:
        acc = all_time_accuracies[name]
        st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
    
    p_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "P")
    b_count = sum(1 for r in st.session_state.oracle.history if r.main_outcome == "B")
    main_history_len = p_count + b_count

    if main_history_len >= 10: 
        st.markdown("<h4>ความแม่นยำ (10 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_10 = sorted(recent_10_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) # Adjusted sort key
        for name in sorted_module_names_recent_10:
            acc = recent_10_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)

    if main_history_len >= 20: 
        st.markdown("<h4>ความแม่นยำ (20 ตาล่าสุด)</h4>", unsafe_allow_html=True)
        sorted_module_names_recent_20 = sorted(recent_20_accuracies.keys(), key=lambda x: (x in ["Tie"], x)) # Adjusted sort key
        for name in sorted_module_names_recent_20:
            acc = recent_20_accuracies[name]
            st.markdown(f"<p class='accuracy-item'>✅ {name}: {acc:.1f}%</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลความแม่นยำ")

