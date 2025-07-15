import streamlit as st
from oracle_core import OracleBrain, Outcome

st.set_page_config(page_title="🔮 Oracle v4.7", layout="centered")

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
    border: 1px solid #444;
    padding: 4px;
    background: #1c1c1c;
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
    font-size: 16px;
    margin-bottom: 2px;
    color: white;
    background-color: transparent !important;
    border: none !important;
}
</style>
<script>
window.addEventListener('load', function() {
    var container = window.parent.document.querySelectorAll('[data-testid="stMarkdownContainer"]');
    if (container.length > 0) {
        var last = container[container.length - 1];
        last.scrollIntoView({ behavior: "smooth", inline: "end" });
    }
});
</script>
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
if 'miss_streak' not in st.session_state:
    st.session_state.miss_streak = 0
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = False
if 'tie_count' not in st.session_state:
    st.session_state.tie_count = 0

# --- UI Logic ---
def handle_click(outcome: Outcome):
    st.session_state.oracle.add_result(outcome)
    prediction, source, confidence, pattern_code, miss = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.pattern_name = pattern_code
    st.session_state.miss_streak = miss
    st.session_state.initial_shown = True
    if outcome == "T":
        st.session_state.tie_count += 1
    else:
        st.session_state.tie_count = 0

def handle_remove():
    st.session_state.oracle.remove_last()
    prediction, source, confidence, pattern_code, miss = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = confidence
    st.session_state.pattern_name = pattern_code
    st.session_state.miss_streak = miss

def handle_reset():
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.miss_streak = 0
    st.session_state.initial_shown = False
    st.session_state.tie_count = 0

# --- Pattern Name Mapping ---
pattern_name_map = {
    "PBPB": "ปิงปอง",
    "BPBP": "ปิงปอง",
    "PPBB": "สองตัด",
    "BBPP": "สองตัด",
    "PPBPP": "สามตัด",
    "BBPBB": "สามตัด",
    "BBBB": "มังกรแดง",
    "PPPP": "มังกรน้ำเงิน"
}

# --- Header ---
st.markdown('<div class="big-title">🔮 ORACLE</div>', unsafe_allow_html=True)

# --- Prediction Box ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("<b>📍 คำทำนาย:</b>", unsafe_allow_html=True)
if st.session_state.prediction:
    emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(st.session_state.prediction, "❓")
    st.markdown(f"## {emoji} <b>{st.session_state.prediction}</b>", unsafe_allow_html=True)
    if st.session_state.source:
        st.caption(f"🧠 โมดูล: {st.session_state.source}")
    if st.session_state.pattern_name:
        name = pattern_name_map.get(st.session_state.pattern_name, st.session_state.pattern_name)
        st.caption(f"📊 เค้าไพ่: {name}")
    if st.session_state.confidence is not None:
        st.caption(f"🔎 ความมั่นใจ: {st.session_state.confidence}%")
else:
    if st.session_state.oracle.show_initial_wait_message and not st.session_state.initial_shown:
        st.warning("⚠️ รอข้อมูลครบ 20 ตา (P/B) ก่อนเริ่มทำนาย")
    else:
        st.info("⏳ กำลังวิเคราะห์ข้อมูล")
st.markdown("</div>", unsafe_allow_html=True)

# --- Miss Streak ---
miss = st.session_state.miss_streak 
st.markdown(f"**❌ แพ้ติดกัน: {miss} ครั้ง**")
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
    columns, col, last = [], [], None
    for i, result in enumerate(history):
        if result in ("P", "B"):
            if result == last and len(col) < max_row:
                col.append(result)
            else:
                if col:
                    columns.append(col)
                col = [result]
                last = result
        elif result == "T" and columns:
            # Append Tie count to last column if possible
            if isinstance(columns[-1], list) and columns[-1]:
                columns[-1][-1] += f"{st.session_state.tie_count}"

    if col:
        columns.append(col)

    html = "<div class='big-road-container'>"
    for col in columns:
        html += "<div class='big-road-column'>"
        for cell in col:
            if isinstance(cell, str) and "P" in cell:
                count = "".join(filter(str.isdigit, cell))
                html += f"<div class='big-road-cell'>🔵{count}</div>" if count else "<div class='big-road-cell'>🔵</div>"
            elif isinstance(cell, str) and "B" in cell:
                count = "".join(filter(str.isdigit, cell))
                html += f"<div class='big-road-cell'>🔴{count}</div>" if count else "<div class='big-road-cell'>🔴</div>"
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Buttons ---
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",), key="btn_P")
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",), key="btn_B")
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",), key="btn_T")

col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ลบรายการล่าสุด", on_click=handle_remove)
with col5:
    st.button("🔄 เริ่มใหม่ทั้งหมด", on_click=handle_reset)

# --- Accuracy ---
st.markdown("<hr>")
st.markdown("### 📈 ความแม่นยำรายโมดูล")
modules = st.session_state.oracle.get_module_accuracy()
for name, acc in modules.items():
    st.write(f"✅ {name}: {acc:.1f}%")
