import streamlit as st
from oracle_core import OracleBrain, Outcome

# --- Setup Page ---
st.set_page_config(page_title="🔮 Oracle v2.7.3", layout="centered")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif !important;
}
.big-title {
    font-size: 28px;
    text-align: center;
    font-weight: bold;
}
.predict-box {
    padding: 10px;
    background-color: #111;
    border-radius: 10px;
    color: white;
    margin-bottom: 10px;
}
.big-road-container {
    width: 100%;
    overflow-x: auto;
    padding: 4px;
    background: transparent;
    white-space: nowrap;
}
.big-road-column {
    display: inline-block;
    vertical-align: top;
    margin-right: 4px;
}
.big-road-cell {
    width: 22px;
    height: 22px;
    text-align: center;
    line-height: 22px;
    font-size: 14px;
    margin-bottom: 2px;
}
</style>
""", unsafe_allow_html=True)

# --- Session Init ---
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

# --- UI Functions ---
def handle_click(outcome: Outcome):
    st.session_state.oracle.add_result(outcome)
    prediction, source, confidence, pattern_code, _ = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    pattern_names = {
        "PBPB": "ปิงปอง", "BPBP": "ปิงปอง",
        "PPBB": "สองตัวติด", "BBPP": "สองตัวติด",
        "PPPP": "มังกร P", "BBBB": "มังกร B"
    }
    st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)
    if not st.session_state.initial_shown:
        st.session_state.initial_shown = True

def handle_remove():
    st.session_state.oracle.remove_last()
    prediction, source, confidence, pattern_code, _ = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.pattern_name = None

def handle_reset():
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.initial_shown = False

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE</div>', unsafe_allow_html=True)

# --- Prediction Output Box ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำทำนาย:</b>", unsafe_allow_html=True)

if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(st.session_state.prediction, "❓")
    st.markdown(f"## {emoji} <b>{st.session_state.prediction}</b>", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        st.caption(f"📊 เค้าไพ่: {st.session_state.pattern_name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence}%")
else:
    if st.session_state.oracle.show_initial_wait_message and not st.session_state.initial_shown:
        st.warning("⚠️ รอข้อมูลครบ 20 ตา (P/B) ก่อนเริ่มทำนาย")
    else:
        st.info("⏳ กำลังวิเคราะห์ข้อมูล")

st.markdown("</div>", unsafe_allow_html=True)

# --- Miss Streak Warning ---
miss = st.session_state.oracle.calculate_miss_streak()
st.warning(f"❌ แพ้ติดกัน: {miss} ครั้ง")
if miss == 3:
    st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
elif miss >= 6:
    st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")

# --- Big Road ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<b>🕒 Big Road:</b>", unsafe_allow_html=True)
history = st.session_state.oracle.history
if history:
    max_row = 6
    columns = []
    col = []
    last = None
    tie_streak = 0
    for result in history:
        if result == "T":
            tie_streak += 1
            continue
        else:
            tie_str = f"{tie_streak}" if tie_streak > 0 else ""
            if result == last:
                if len(col) < max_row:
                    col.append((result, tie_str))
                else:
                    columns.append(col)
                    col = [(result, tie_str)]
            else:
                if col:
                    columns.append(col)
                col = [(result, tie_str)]
                last = result
            tie_streak = 0
    if col:
        columns.append(col)

    html = "<div class='big-road-container'>"
    for col in columns:
        html += "<div class='big-road-column'>"
        for cell in col:
            emoji = "🔵" if cell[0] == "P" else "🔴"
            tie = cell[1]
            html += f"<div class='big-road-cell'>{emoji}{tie}</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons ---
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
st.markdown("<hr>")
st.markdown("### 📈 ความแม่นยำรายโมดูล")
modules = st.session_state.oracle.get_module_accuracy()
if modules:
    for name, acc in modules.items():
        st.write(f"✅ {name}: {acc:.1f}%")
