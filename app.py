import streamlit as st
from oracle_core import OracleBrain

st.set_page_config(page_title="🔮 ORACLE v5", layout="centered")

# โหลด Oracle
if 'oracle' not in st.session_state:
    st.session_state.oracle = OracleBrain()
if 'initial_shown' not in st.session_state:
    st.session_state.initial_shown = True

st.markdown("<h1 style='text-align:center;'>🔮 ORACLE v5</h1>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 P"):
        st.session_state.oracle.add_result('P')
with col2:
    if st.button("🔴 B"):
        st.session_state.oracle.add_result('B')
with col3:
    if st.button("⚪️ T"):
        st.session_state.oracle.add_result('T')

# แสดงคำทำนาย
result = st.session_state.oracle.predict()
if result:
    prediction, module, confidence, pattern, miss_streak = result
    color = '🔵' if prediction == 'P' else '🔴'
    st.markdown(f"<h3>📍 คำทำนาย:</h3>", unsafe_allow_html=True)
    st.markdown(f"<span style='font-size: 48px'>{color} {prediction}</span>", unsafe_allow_html=True)
    st.markdown(f"🧠 โมดูล: <b>{module}</b>", unsafe_allow_html=True)
    st.markdown(f"📊 เค้าไพ่: {pattern}")
    st.markdown(f"🔎 ความมั่นใจ: {confidence}%")
    st.markdown(f"❌ แพ้ติดกัน: <span style='color:red'>{miss_streak} ครั้ง</span>", unsafe_allow_html=True)

# ปุ่มจัดการ
col4, col5 = st.columns(2)
with col4:
    if st.button("↩️ ลบรายการล่าสุด"):
        st.session_state.oracle.undo_last()
with col5:
    if st.button("🔄 เริ่มใหม่ทั้งหมด"):
        st.session_state.oracle.reset()

# แสดง Big Road
st.markdown("### 🕒 Big Road:")

# เพิ่ม Auto Scroll CSS
scroll_code = """
<style>
.big-road {
    max-width: 100%;
    overflow-x: auto;
    white-space: nowrap;
    padding: 10px;
    background: #111;
    border-radius: 10px;
}
</style>
<div class="big-road">
"""
st.markdown(scroll_code, unsafe_allow_html=True)
st.markdown(st.session_state.oracle.render_big_road_html(), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
