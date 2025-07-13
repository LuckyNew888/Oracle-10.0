import streamlit as st
from oracle_core import OracleBrain, Outcome

st.set_page_config(page_title="🔮 Oracle", layout="centered")

# --- CSS Styling ---
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
    scroll-behavior: smooth;
}
.big-road-container::-webkit-scrollbar {
    height: 6px;
}
.big-road-container::-webkit-scrollbar-thumb {
    background: #555;
    border-radius: 3px;
}
.big-road-column {
    display: inline-block;
    vertical-align: top;
    margin-right: 4px;
}
.big-road-cell {
    width: 26px;
    height: 26px;
    text-align: center;
    line-height: 26px;
    font-size: 16px;
    margin-bottom: 2px;
    color: white;
    background-color: transparent !important;
    border: none !important;
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
if 'miss_streak' not in st.session_state:
    st.session_state.miss_streak = 0
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = False

# --- UI Functions ---
def handle_click(outcome: Outcome):
    st.session_state.oracle.add_result(outcome)
    prediction, source, confidence, pattern_code, current_miss_streak = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = min(confidence, 95) if confidence else None
    st.session_state.pattern_name = pattern_code
    st.session_state.miss_streak = current_miss_streak
    if not st.session_state.initial_shown:
        st.session_state.initial_shown = True

def handle_remove():
    st.session_state.oracle.remove_last()
    prediction, source, confidence, pattern_code, current_miss_streak = st.session_state.oracle.predict_next()
    st.session_state.prediction = prediction
    st.session_state.source = source
    st.session_state.confidence = min(confidence, 95) if confidence else None
    st.session_state.pattern_name = pattern_code
    st.session_state.miss_streak = current_miss_streak

def handle_reset():
    st.session_state.oracle.reset()
    st.session_state.prediction = None
    st.session_state.source = None
    st.session_state.confidence = None
    st.session_state.pattern_name = None
    st.session_state.miss_streak = 0
    st.session_state.initial_shown = False

# --- Pattern Name Map ---
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

# --- Prediction Display ---
st.markdown("<div class='predict-box'>", unsafe_allow_html=True)
st.markdown("**📍 คำทำนาย:**", unsafe_allow_html=True)

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

# --- Miss Streak Display ---
miss = st.session_state.miss_streak 
st.markdown(f"**❌ แพ้ติดกัน: {miss} ครั้ง**")
if miss > 0:
    if miss == 3:
        st.warning("🧪 เริ่มกระบวนการฟื้นฟู")
    elif miss >= 6:
        st.error("🚫 หยุดระบบชั่วคราว (แพ้ 6 ไม้ติด)")

# --- Big Road ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("**🕒 Big Road:**", unsafe_allow_html=True)

raw_history = st.session_state.oracle.history
history = []
t_counters = []

for outcome in raw_history:
    if outcome == "T":
        if t_counters:
            t_counters[-1] += 1
        elif history:
            t_counters.append(1)
        else:
            history.append("P")  # dummy cell
            t_counters.append(1)
    elif outcome in ("P", "B"):
        history.append(outcome)
        t_counters.append(0)

if history:
    max_row = 6
    columns, col, last = [], [], None
    for res in history:
        if res == last and len(col) < max_row:
            col.append(res)
        else:
            if col:
                columns.append(col)
            col = [res]
            last = res
    if col:
        columns.append(col)

    html = "<div class='big-road-container' id='bigroad'>"
    for i, col in enumerate(columns):
        html += "<div class='big-road-column'>"
        for j, cell in enumerate(col):
            idx = sum(len(c) for c in columns[:i]) + j
            t = t_counters[idx] if idx < len(t_counters) else 0
            emoji = "🔵" if cell == "P" else "🔴"
            label = f"{emoji}{t}" if t > 0 else emoji
            html += f"<div class='big-road-cell'>{label}</div>"
        html += "</div>"
    html += "</div><script>setTimeout(()=>{let el = document.getElementById('bigroad'); el.scrollLeft = el.scrollWidth;}, 100);</script>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.info("🔄 ยังไม่มีข้อมูล")

# --- Input Buttons ---
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 P", on_click=handle_click, args=("P",))
with col2:
    st.button("🔴 B", on_click=handle_click, args=("B",))
with col3:
    st.button("⚪ T", on_click=handle_click, args=("T",))

# --- Control Buttons ---
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
