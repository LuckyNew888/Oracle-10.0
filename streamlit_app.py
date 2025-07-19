import streamlit as st
import json
import os
from oracle_core import OracleBrain, Outcome # Assuming oracle_core.py contains OracleBrain and Outcome

# --- Persistence Setup ---
# กำหนดชื่อไฟล์สำหรับบันทึก/โหลดข้อมูล
DATA_FILE = "oracle_data.json"

def save_state():
    """บันทึกสถานะปัจจุบันของ OracleBrain และ Streamlit session ลงในไฟล์ JSON"""
    state = {
        'history': st.session_state.oracle.history,
        'ties': st.session_state.oracle.ties,
        'result_log': st.session_state.oracle.result_log,
        # แปลง None เป็นสตริง "None" เพื่อให้ JSON สามารถ serialize ได้
        'prediction_log': [p if p is not None else "None" for p in st.session_state.oracle.prediction_log], 
        'last_prediction': st.session_state.oracle.last_prediction,
        'show_initial_wait_message': st.session_state.oracle.show_initial_wait_message,
        'tie_buffer': st.session_state.tie_buffer,
        'prediction': st.session_state.prediction,
        'source': st.session_state.source,
        'confidence': st.session_state.confidence,
        'pattern_name': st.session_state.pattern_name,
        'trend_indicator': st.session_state.get('trend_indicator', None), # บันทึก trend_indicator ด้วย
        'last_p_b_outcome': st.session_state.get('last_p_b_outcome', None), # บันทึกผลลัพธ์ P/B ล่าสุดเพื่อแสดง Tie
        'miss_streak': st.session_state.get('miss_streak', 0) # บันทึก miss_streak ด้วย
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

def load_state():
    """โหลดสถานะจากไฟล์ JSON เข้าสู่ OracleBrain และ Streamlit session"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
            # สร้าง OracleBrain ใหม่และกำหนดค่า attribute
            st.session_state.oracle = OracleBrain() 
            st.session_state.oracle.history = state.get('history', [])
            st.session_state.oracle.ties = state.get('ties', [])
            st.session_state.oracle.result_log = state.get('result_log', [])
            # แปลง "None" กลับเป็น None
            st.session_state.oracle.prediction_log = [p if p != "None" else None for p in state.get('prediction_log', [])] 
            st.session_state.oracle.last_prediction = state.get('last_prediction', None)
            st.session_state.oracle.show_initial_wait_message = state.get('show_initial_wait_message', True)
            
            # กำหนดค่าตัวแปร Streamlit session state
            st.session_state.tie_buffer = state.get('tie_buffer', 0)
            st.session_state.prediction = state.get('prediction', None)
            st.session_state.source = state.get('source', None)
            st.session_state.confidence = state.get('confidence', None)
            st.session_state.pattern_name = state.get('pattern_name', None)
            st.session_state.trend_indicator = state.get('trend_indicator', None)
            st.session_state.last_p_b_outcome = state.get('last_p_b_outcome', None) # โหลด last_p_b_outcome
            st.session_state.miss_streak = state.get('miss_streak', 0) # โหลด miss_streak
        return True
    return False

# --- Setup ---
st.set_page_config(page_title="🔮 Oracle 5.0", layout="centered")

# Custom CSS for styling and animations
st.markdown("""
<style>
/* Font and general body styles */
html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif !important;
    background-color: #1a1a1a; /* Dark background for the whole app */
    color: #ecf0f1; /* Light text color */
}
/* Main title */
.big-title {
    font-size: 28px; /* Increased font size */
    text-align: center;
    font-weight: bold;
    margin-bottom: 5px; /* Reduced margin */
    color: #f39c12; /* Orange color for title */
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5); /* Stronger shadow */
    display: flex;
    justify-content: center;
    align-items: baseline; /* Align text at baseline */
}
.big-title .version {
    font-size: 16px; /* Smaller font for version */
    margin-left: 5px; /* Space between "ORACLE" and "5.0" */
    color: #ecf0f1; /* Lighter color for version */
}

/* Prediction box */
.predict-box {
    padding: 15px; /* More padding */
    background-color: #2c3e50; /* Darker blue-grey */
    border-radius: 15px; /* More rounded corners */
    color: white;
    font-size: 20px; /* Larger font */
    margin-bottom: 20px;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3); /* Stronger shadow */
    text-align: center; /* Center text */
    animation: fadeIn 0.8s ease-out; /* Fade-in animation */
    border: 2px solid #f39c12; /* Orange border */
    max-width: 400px; /* Limit width */
    margin-left: auto;
    margin-right: auto;
}
.predict-box b {
    color: #ecf0f1; /* Lighter text for bold parts */
    font-size: 28px; /* Larger font for prediction text */
}
.predict-box .st-emotion-cache-1r6slb0 { /* Target Streamlit's caption */
    font-size: 14px;
    color: #bdc3c7; /* Lighter grey for captions */
    margin-top: 5px;
}
.predict-box .tie-info {
    font-size: 20px; /* Larger font for tie info */
    font-weight: bold;
    color: #2ecc71; /* Green for tie count */
}

/* Big Road container */
.big-road-container {
    width: 100%;
    overflow-x: auto; /* Horizontal scrolling */
    padding: 10px;
    background: #000; /* Black background for Big Road */
    border-radius: 10px;
    white-space: nowrap;
    margin-bottom: 20px;
    box-shadow: inset 0 3px 6px rgba(0, 0, 0, 0.5); /* Deeper inset shadow */
    border: 2px solid #333; /* Darker border */
    max-height: 250px; /* Limit height for scroll, allows more rows if columns are short */
    display: flex; /* Use flexbox for columns */
    align-items: flex-start; /* Align columns to the top */
}
/* Big Road column */
.big-road-column {
    display: inline-flex; /* Use inline-flex to make columns flexible */
    flex-direction: column; /* Stack cells vertically */
    vertical-align: top;
    margin-right: 4px; /* Space between columns */
    padding-left: 0px; /* No left padding */
    flex-shrink: 0; /* Prevent columns from shrinking */
}
/* Big Road cell */
.big-road-cell {
    width: 28px; /* Smaller cells */
    height: 28px;
    text-align: center;
    line-height: 28px;
    font-size: 18px; /* Smaller icons */
    margin-bottom: 2px; /* Space between cells */
    border-radius: 50%; /* Circular shape */
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2); /* Shadow for depth */
    position: relative; /* For tie overlay */
    background-color: transparent; /* Default transparent background */
}
/* Specific colors for P and B cells */
.big-road-cell.player {
    background-color: #3498db; /* Blue for Player */
}
.big-road-cell.banker {
    background-color: #e74c3c; /* Red for Banker */
}

/* Tie overlay style */
.tie-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%); /* Center the tie number */
    font-size: 14px; /* Smaller font for tie number */
    color: black; /* Black text for tie number */
    background-color: #2ecc71; /* Green background for tie number */
    border-radius: 50%;
    width: 20px; /* Size of the tie circle */
    height: 20px;
    line-height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    border: 1px solid #1a1a1a; /* Dark border for tie circle */
    z-index: 10; /* Ensure it's on top */
}

/* Buttons */
.stButton>button {
    width: 100%;
    border-radius: 10px; /* More rounded */
    padding: 12px 0; /* More padding */
    font-size: 18px; /* Larger font */
    font-weight: bold;
    color: white;
    border: none;
    cursor: pointer;
    transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2); /* Stronger shadow */
}
.stButton>button:hover {
    transform: translateY(-3px); /* More pronounced lift */
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}
/* Button colors */
.stButton>button[data-testid="stButton-btn_p"] { background-color: #3498db; } /* Blue */
.stButton>button[data-testid="stButton-btn_p"]:hover { background-color: #2980b9; }

.stButton>button[data-testid="stButton-btn_b"] { background-color: #e74c3c; } /* Red */
.stButton>button[data-testid="stButton-btn_b"]:hover { background-color: #c0392b; }

.stButton>button[data-testid="stButton-btn_t"] { background-color: #2ecc71; } /* Emerald Green */
.stButton>button[data-testid="stButton-btn_t"]:hover { background-color: #27ae60; }

.stButton>button:nth-child(1)[data-testid^="stButton-"] { background-color: #f1c40f; } /* Yellow for Undo */
.stButton>button:nth-child(1)[data-testid^="stButton-"]:hover { background-color: #f39c12; }

.stButton>button:nth-child(2)[data-testid^="stButton-"] { background-color: #95a5a6; } /* Grey for Reset */
.stButton>button:nth-child(2)[data-testid^="stButton-"]:hover { background-color: #7f8c8d; }

/* Trend Indicator Box */
.trend-box {
    padding: 12px;
    background-color: #333; /* Darker background */
    border-radius: 10px;
    margin-top: 20px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
    text-align: center;
    border: 2px solid #f39c12; /* Orange border */
    color: #ecf0f1;
    max-width: 400px; /* Limit width */
    margin-left: auto;
    margin-right: auto;
}
.trend-box h4 {
    color: #f39c12; /* Orange for trend title */
    margin-bottom: 5px;
}
.trend-box p {
    font-size: 18px; /* Larger font for trend text */
    color: #ecf0f1;
    font-weight: bold;
}

/* Miss Streak Box */
.miss-streak-box {
    padding: 10px;
    background-color: #c0392b; /* Red background */
    border-radius: 10px;
    margin-top: 15px;
    margin-bottom: 15px;
    text-align: center;
    font-weight: bold;
    color: white;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
    max-width: 400px; /* Limit width */
    margin-left: auto;
    margin-right: auto;
}

/* Fade-in animation for prediction box */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
""", unsafe_allow_html=True)

# --- Session Init ---
# โหลดสถานะก่อน
if not load_state():
    # ถ้าไม่มีสถานะที่บันทึกไว้ ให้เริ่มต้น OracleBrain และตัวแปร session ใหม่
    st.session_state.oracle = OracleBrain()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.tie_buffer = 0
    st.session_state.trend_indicator = None # เริ่มต้น trend_indicator
    st.session_state.last_p_b_outcome = None # เก็บผลลัพธ์ P/B ล่าสุดสำหรับแสดง Tie
    st.session_state.miss_streak = 0 # เริ่มต้น miss_streak

# --- Functions ---
def handle_click(outcome: Outcome):
    """
    จัดการการคลิกปุ่ม P, B, T
    เพิ่มผลลัพธ์ลงใน OracleBrain, อัปเดตการทำนาย, และบันทึกสถานะ
    """
    if outcome == "T":
        st.session_state.tie_buffer += 1
        # เมื่อกด T, เราต้องการให้ Big Road อัปเดตทันที
        # และ Prediction Box แสดง Tie buffer
        # ไม่มีการเรียก predict_next() ที่นี่ เพราะ Tie ไม่ใช่ผลลัพธ์ที่ OracleBrain ทำนายโดยตรง
    else:
        # ถ้าเป็น P หรือ B, ให้เพิ่มผลลัพธ์พร้อมกับจำนวน Tie ที่สะสมไว้
        st.session_state.oracle.add_result(outcome, st.session_state.tie_buffer)
        st.session_state.tie_buffer = 0 # รีเซ็ต tie_buffer หลังจากเพิ่ม P/B
        st.session_state.last_p_b_outcome = outcome # บันทึกผลลัพธ์ P/B ล่าสุด

        # ทำการทำนายถัดไป (จะแสดงผลเมื่อมีข้อมูล P/B อย่างน้อย 20 มือ)
        prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
        st.session_state.prediction = prediction
        st.session_state.source = source
        st.session_state.confidence = confidence
        
        # คำนวณ Miss Streak หลังจากการทำนาย P/B
        st.session_state.miss_streak = st.session_state.oracle.calculate_miss_streak()
    
    # ดึงแนวโน้มแบบง่าย (ทำเสมอไม่ว่าจะเป็น P/B/T)
    st.session_state.trend_indicator = st.session_state.oracle.get_simplified_trend()

    # แมปโค้ดรูปแบบเป็นชื่อภาษาไทย (ทำเสมอไม่ว่าจะเป็น P/B/T)
    pattern_names = {
        "PBPB": "ปิงปอง",
        "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด",
        "BBPP": "สองตัวติด",
        "PPPP": "มังกร P",
        "BBBB": "มังกร B"
    }
    # ใช้ pattern_code จากการทำนายล่าสุด (ถ้ามี)
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    save_state() # บันทึกสถานะหลังจากการกระทำทุกครั้ง

def handle_remove():
    """
    จัดการการคลิกปุ่ม "ย้อนกลับ"
    ลบผลลัพธ์ล่าสุด, อัปเดตการทำนาย, และบันทึกสถานะ
    """
    # ตรวจสอบว่ามี Tie ที่ยังไม่ได้บันทึกเป็น P/B หรือไม่
    if st.session_state.tie_buffer > 0:
        st.session_state.tie_buffer -= 1 # ลด Tie buffer
    elif st.session_state.oracle.history:
        # ถ้าไม่มี Tie buffer และมีประวัติ P/B ให้ลบออก
        st.session_state.oracle.remove_last()
        st.session_state.tie_buffer = 0 # รีเซ็ต tie buffer เมื่อย้อนกลับ P/B
        
        # อัปเดต last_p_b_outcome ให้เป็นผลลัพธ์ก่อนหน้า (ถ้ามี)
        if st.session_state.oracle.history:
            st.session_state.last_p_b_outcome = st.session_state.oracle.history[-1]
            # ดึง tie_count ของมือที่ถูกย้อนกลับมา
            if st.session_state.oracle.ties:
                st.session_state.tie_buffer = st.session_state.oracle.ties[-1] 
                # หลังจากย้อนกลับ P/B, Tie ที่เคยผูกกับมือนี้จะกลับมาอยู่ใน buffer
                # เพื่อให้ผู้ใช้สามารถแก้ไข Tie ได้ก่อนจะบันทึกมือ P/B ถัดไป
                # และต้องลบ Tie ออกจาก ties list ของ OracleBrain ด้วย
                st.session_state.oracle.ties[-1] = 0 # ตั้งค่า Tie ของมือที่ย้อนกลับเป็น 0 ใน ties list
        else:
            st.session_state.last_p_b_outcome = None
    else:
        # ถ้าไม่มีประวัติ P/B และไม่มี Tie buffer ก็ไม่ต้องทำอะไร
        st.session_state.tie_buffer = 0
        st.session_state.last_p_b_outcome = None


    # คำนวณการทำนายใหม่หลังจากการลบ
    prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    
    # คำนวณ Miss Streak หลังจากการทำนาย P/B
    st.session_state.miss_streak = st.session_state.oracle.calculate_miss_streak()

    # คำนวณแนวโน้มใหม่
    st.session_state.trend_indicator = st.session_state.oracle.get_simplified_trend()

    # แมปชื่อรูปแบบใหม่
    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร P", "BBBB": "มังกร B"
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)

    save_state() # บันทึกสถานะหลังจากการกระทำทุกครั้ง

def handle_reset():
    """
    จัดการการคลิกปุ่ม "ล้างใหม่"
    รีเซ็ต OracleBrain และตัวแปร session ทั้งหมด, และบันทึกสถานะ
    """
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.tie_buffer = 0
    st.session_state.trend_indicator = None # รีเซ็ต trend indicator ด้วย
    st.session_state.last_p_b_outcome = None # รีเซ็ต last_p_b_outcome
    st.session_state.miss_streak = 0 # รีเซ็ต miss_streak
    save_state() # บันทึกสถานะหลังจากการกระทำทุกครั้ง

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE <span class="version">5.0</span></div>', unsafe_allow_html=True)

# --- Prediction Box ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
if st.session_state.tie_buffer > 0 and st.session_state.last_p_b_outcome:
    # แสดงผล Tie สะสมทันทีเมื่อมีการกด T และมี P/B ล่าสุด
    emoji = {"P": "🔵", "B": "🔴"}.get(st.session_state.last_p_b_outcome, "❓")
    st.markdown(f"<b>📍 ผลลัพธ์ล่าสุด:</b> {emoji} {st.session_state.last_p_b_outcome} <span class='tie-info'>+ {st.session_state.tie_buffer} Tie</span>", unsafe_allow_html=True)
    st.caption("กด P หรือ B เพื่อบันทึกมือถัดไป")
elif st.session_state.prediction:
    # แสดงผลการทำนายปกติ
    emoji = {"P": "🔵", "B": "🔴"}.get(st.session_state.prediction, "❓")
    st.markdown(f"<b>📍 ทำนาย:</b> {emoji} {st.session_state.prediction}", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence}%")
else:
    # ข้อความรอข้อมูล
    st.warning("⚠️ รอข้อมูลก่อนเริ่มทำนาย (อย่างน้อย 20 ผลลัพธ์ที่ไม่ใช่เสมอ)")
    # แสดง Tie สะสมแม้จะไม่มีการทำนาย P/B
    if st.session_state.tie_buffer > 0:
        st.info(f"⚪ Tie สะสม: {st.session_state.tie_buffer} ครั้ง")
st.markdown("</div>", unsafe_allow_html=True)

# --- Miss Streak Display ---
if st.session_state.miss_streak > 0:
    st.markdown(f"<div class='miss-streak-box'>🔥 แพ้ติดกัน: {st.session_state.miss_streak} ครั้ง</div>", unsafe_allow_html=True)

# --- Big Road Display ---
st.markdown("### 🕒 Big Road")
# ใช้ static method เพื่อดึงคอลัมน์สำหรับการแสดงผล Big Road
big_road_display_cols = OracleBrain._generate_big_road_columns_for_display(
    st.session_state.oracle.history, st.session_state.oracle.ties
)

if big_road_display_cols:
    html = "<div class='big-road-container'>"
    # แสดงเฉพาะ 16 คอลัมน์ล่าสุด
    cols_to_display = big_road_display_cols[-16:] 
    
    for col_data in cols_to_display:
        html += "<div class='big-road-column'>"
        for outcome, tie_count in col_data:
            # กำหนด class สำหรับสีพื้นหลังของวงกลม
            cell_class = "player" if outcome == "P" else "banker"
            
            # สร้าง HTML สำหรับ Tie Overlay (วงกลมเขียวตัวเลขดำ)
            tie_html = ""
            if tie_count > 0:
                tie_html = f"<div class='tie-overlay'>{tie_count}</div>"
            
            # วงกลม P หรือ B
            html += f"<div class='big-road-cell {cell_class}'>{tie_html}</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🌀 ยังไม่มีข้อมูล")

# --- Trend Indicator ---
st.markdown("### 📊 แนวโน้มปัจจุบัน")
st.markdown("<div class='trend-box'>", unsafe_allow_html=True)
if st.session_state.trend_indicator:
    st.markdown(f"<p>{st.session_state.trend_indicator}</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลแนวโน้ม (ต้องมีข้อมูลอย่างน้อย 3 คอลัมน์ใน Big Road)")
st.markdown("</div>", unsafe_allow_html=True)

# --- Buttons ---
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_p")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_b")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_t")

col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ย้อนกลับ", on_click=handle_remove)
with col5:
    st.button("🧹 ล้างใหม่", on_click=handle_reset)

# --- Accuracy ---
st.markdown("### 📈 ความแม่นยำของโมดูล")
modules_accuracy = st.session_state.oracle.get_module_accuracy()
# ตรวจสอบว่ามีความแม่นยำที่คำนวณได้หรือไม่
if any(modules_accuracy.values()) or len(st.session_state.oracle.history) >= 4: 
    for name, acc in modules_accuracy.items():
        st.write(f"✅ {name}: {acc:.1f}%")
else:
    st.info("ยังไม่มีข้อมูลความแม่นยำ (ต้องมีข้อมูลอย่างน้อย 4 ผลลัพธ์ที่ไม่ใช่เสมอ)")

