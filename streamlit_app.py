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
        'trend_indicator': st.session_state.get('trend_indicator', None) # บันทึก trend_indicator ด้วย
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
}
/* Main title */
.big-title {
    font-size: 28px; /* Increased font size */
    text-align: center;
    font-weight: bold;
    margin-bottom: 20px; /* More space */
    color: #2c3e50; /* Darker blue-grey */
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1); /* Subtle shadow */
}
/* Prediction box */
.predict-box {
    padding: 15px; /* More padding */
    background-color: #34495e; /* Darker background */
    border-radius: 15px; /* More rounded corners */
    color: white;
    font-size: 20px; /* Larger font */
    margin-bottom: 20px;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3); /* Stronger shadow */
    text-align: center; /* Center text */
    animation: fadeIn 0.8s ease-out; /* Fade-in animation */
}
.predict-box b {
    color: #ecf0f1; /* Lighter text for bold parts */
}
.predict-box .st-emotion-cache-1r6slb0 { /* Target Streamlit's caption */
    font-size: 14px;
    color: #bdc3c7; /* Lighter grey for captions */
    margin-top: 5px;
}

/* Big Road container */
.big-road-container {
    width: 100%;
    overflow-x: auto;
    padding: 10px;
    background: #ecf0f1;
    border-radius: 10px;
    white-space: nowrap;
    margin-bottom: 20px;
    box-shadow: inset 0 3px 6px rgba(0, 0, 0, 0.15); /* Deeper inset shadow */
    border: 1px solid #bdc3c7; /* Subtle border */
    max-height: 200px; /* Limit height for scroll */
}
/* Big Road column */
.big-road-column {
    display: inline-block;
    vertical-align: top;
    margin-right: 8px; /* More space between columns */
    border-left: 1px solid #bdc3c7;
    padding-left: 6px;
}
.big-road-column:first-child {
    border-left: none;
    padding-left: 0;
}
/* Big Road cell */
.big-road-cell {
    width: 32px; /* Larger cells */
    height: 32px;
    text-align: center;
    line-height: 32px;
    font-size: 20px; /* Larger icons */
    margin-bottom: 4px; /* More space between cells */
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Slightly stronger shadow */
    position: relative; /* For tie overlay */
}
.tie-overlay {
    position: absolute;
    bottom: -2px; /* Position at bottom-right */
    right: -2px;
    font-size: 10px; /* Smaller font for tie count */
    color: white;
    background-color: #2c3e50; /* Darker background for tie count */
    border-radius: 50%;
    width: 16px;
    height: 16px;
    line-height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    border: 1px solid white; /* Small white border */
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
    background-color: #ecf0f1;
    border-radius: 10px;
    margin-top: 20px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    text-align: center;
    border: 1px solid #bdc3c7;
}
.trend-box h4 {
    color: #34495e;
    margin-bottom: 5px;
}
.trend-box p {
    font-size: 18px; /* Larger font for trend text */
    color: #555;
    font-weight: bold;
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

# --- Functions ---
def handle_click(outcome: Outcome):
    """
    จัดการการคลิกปุ่ม P, B, T
    เพิ่มผลลัพธ์ลงใน OracleBrain, อัปเดตการทำนาย, และบันทึกสถานะ
    """
    if outcome == "T":
        st.session_state.tie_buffer += 1
    else:
        st.session_state.oracle.add_result(outcome, st.session_state.tie_buffer)
        st.session_state.tie_buffer = 0
        
    # พยายามทำนายเสมอหลังจากการป้อนข้อมูลใดๆ (P/B/T)
    # แต่การทำนายจะแสดงผลเมื่อมีข้อมูล P/B อย่างน้อย 20 มือ
    prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    
    # ดึงแนวโน้มแบบง่าย
    st.session_state.trend_indicator = st.session_state.oracle.get_simplified_trend()

    # แมปโค้ดรูปแบบเป็นชื่อภาษาไทย
    pattern_names = {
        "PBPB": "ปิงปอง",
        "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด",
        "BBPP": "สองตัวติด",
        "PPPP": "มังกร P",
        "BBBB": "มังกร B"
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    
    save_state() # บันทึกสถานะหลังจากการกระทำทุกครั้ง

def handle_remove():
    """
    จัดการการคลิกปุ่ม "ย้อนกลับ"
    ลบผลลัพธ์ล่าสุด, อัปเดตการทำนาย, และบันทึกสถานะ
    """
    st.session_state.oracle.remove_last()
    st.session_state.tie_buffer = 0 # รีเซ็ต tie buffer เมื่อย้อนกลับ
    
    # คำนวณการทำนายใหม่หลังจากการลบ
    prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    
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
    save_state() # บันทึกสถานะหลังจากการกระทำทุกครั้ง

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE 5.0</div>', unsafe_allow_html=True)

# --- Prediction Box ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴"}.get(st.session_state.prediction, "❓")
    st.markdown(f"<b>📍 ทำนาย:</b> {emoji} {st.session_state.prediction}", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence}%")
else:
    st.warning("⚠️ รอข้อมูลก่อนเริ่มทำนาย (อย่างน้อย 20 ผลลัพธ์ที่ไม่ใช่เสมอ)")
    if st.session_state.tie_buffer > 0:
        st.info(f"⚪ Tie สะสม: {st.session_state.tie_buffer} ครั้ง")
st.markdown("</div>", unsafe_allow_html=True)

# --- Big Road Display ---
st.markdown("### 🕒 Big Road")
# ใช้ static method เพื่อดึงคอลัมน์สำหรับการแสดงผล Big Road
big_road_display_cols = OracleBrain._generate_big_road_columns_for_display(
    st.session_state.oracle.history, st.session_state.oracle.ties
)

if big_road_display_cols:
    html = "<div class='big-road-container'>"
    for col_data in big_road_display_cols:
        html += "<div class='big-road-column'>"
        for outcome, tie_count in col_data:
            icon = "🔵" if outcome == "P" else "🔴"
            # แสดงจำนวน Tie เป็น overlay เล็กๆ ถ้ามากกว่า 0
            tie_html = f"<div class='tie-overlay'>{tie_count}</div>" if tie_count > 0 else ""
            html += f"<div class='big-road-cell'>{icon}{tie_html}</div>"
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

