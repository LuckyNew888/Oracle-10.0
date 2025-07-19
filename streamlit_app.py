import streamlit as st
from oracle_core import OracleBrain, Outcome

# --- Setup ---
st.set_page_config(page_title="🔮 Oracle 5.0", layout="centered")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif !important;
}
.big-title {
    font-size: 22px;
    text-align: center;
    font-weight: bold;
    margin-bottom: 10px;
}
.predict-box {
    padding: 8px;
    background-color: #111;
    border-radius: 10px;
    color: white;
    font-size: 16px;
    margin-bottom: 8px;
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
    width: 24px;
    height: 24px;
    text-align: center;
    line-height: 24px;
    font-size: 16px;
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
if 'tie_buffer' not in st.session_state:
    st.session_state.tie_buffer = 0

# --- Functions ---
def handle_click(outcome: Outcome):
    if outcome == "T":
        st.session_state.tie_buffer += 1
    else:
        st.session_state.oracle.add_result(outcome, st.session_state.tie_buffer)
        st.session_state.tie_buffer = 0
        prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
        st.session_state.prediction = prediction
        st.session_state.source = source
        st.session_state.confidence = confidence
        pattern_names = {
            "PBPB": "ปิงปอง",
            "BPBP": "ปิงปอง",
            "PPBB": "สองตัวติด",
            "BBPP": "สองตัวติด",
            "PPPP": "มังกร P",
            "BBBB": "มังกร B"
        }
        st.session_state.pattern_name = pattern_names.get(pattern_code, pattern_code if pattern_code else None)

def handle_remove():
    st.session_state.oracle.remove_last()
    prediction, source, confidence, pattern_code = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.pattern_name = None
    st.session_state.tie_buffer = 0

def handle_reset():
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.tie_buffer = 0

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
    st.warning("⚠️ รอข้อมูลก่อนเริ่มทำนาย")
st.markdown("</div>", unsafe_allow_html=True)

# --- Big Road ---
st.markdown("### 🕒 Big Road")
history = st.session_state.oracle.history
ties = st.session_state.oracle.ties
if history:
    max_row = 6
    columns = []
    col = []
    last = None
    for i, result in enumerate(history):
        tie_mark = f"{'⚪'*ties[i]}" if ties[i] else ""
        if result == last and len(col) < max_row:
            col.append((result, tie_mark))
        else:
            if col:
                columns.append(col)
            col = [(result, tie_mark)]
            last = result
    if col:
        columns.append(col)

    html = "<div class='big-road-container'>"
    for col in columns:
        html += "<div class='big-road-column'>"
        for outcome, tie in col:
            icon = "🔵" if outcome == "P" else "🔴"
            html += f"<div class='big-road-cell'>{icon}{tie}</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🌀 ยังไม่มีข้อมูล")

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
st.markdown("### 📈 ความแม่นยำ")
modules = st.session_state.oracle.get_module_accuracy()
for name, acc in modules.items():
    st.write(f"✅ {name}: {acc:.1f}%")
