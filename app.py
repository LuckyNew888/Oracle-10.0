# app.py (สำหรับ Oracle v5.0)
import streamlit as st
from oracle_core import OracleBrain

# --- เตรียม Session State ---
if "oracle" not in st.session_state:
    st.session_state.oracle = OracleBrain()

if "initial_shown" not in st.session_state:
    st.session_state.initial_shown = False

st.title("🔮 ORACLE v5")

# ปุ่มใส่ผล
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 P"):
        st.session_state.oracle.add_result("P")
with col2:
    if st.button("🔴 B"):
        st.session_state.oracle.add_result("B")
with col3:
    if st.button("⚪ T"):
        st.session_state.oracle.add_result("T")

# ทำนาย
if st.button("🔮 ทำนายผลลัพธ์ถัดไป"):
    result = st.session_state.oracle.predict()
    if result:
        outcome, module, confidence, pattern, streak = result
        st.markdown(f"### 📍 คำทำนาย: {outcome}")
        st.markdown(f"🧠 โมดูล: {module}")
        st.markdown(f"📊 เค้าไพ่: {pattern}")
        st.markdown(f"🔎 ความมั่นใจ: {confidence}%")
        st.markdown(f"❌ แพ้ติดกัน: {streak} ครั้ง")
    else:
        st.warning("ไม่สามารถทำนายได้")

# ปุ่มลบ/รีเซ็ต
col4, col5 = st.columns(2)
with col4:
    if st.button("↩️ ลบรายการล่าสุด"):
        st.session_state.oracle.remove_last()
with col5:
    if st.button("🧹 เริ่มใหม่ทั้งหมด"):
        st.session_state.oracle.reset()

# แสดงผล Big Road
st.markdown("## 🕒 Big Road:")
history = st.session_state.oracle.history
if not history:
    st.info("ยังไม่มีผลลัพธ์")
else:
    cols = st.columns(len(history))
    for i, result in enumerate(history):
        with cols[i]:
            color = {"P": "blue", "B": "red", "T": "white"}.get(result, "gray")
            emoji = {"P": "🔵", "B": "🔴", "T": "⚪"}.get(result, "❔")
            st.markdown(f"<div style='text-align: center;'>{emoji}</div>", unsafe_allow_html=True)
