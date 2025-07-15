import streamlit as st
from oracle_core import OracleBrain

st.set_page_config(layout="wide")
if "oracle" not in st.session_state:
    st.session_state.oracle = OracleBrain()
if "initial_shown" not in st.session_state:
    st.session_state.initial_shown = False

oracle = st.session_state.oracle

st.markdown("## 🔮 ORACLE v5")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 P"):
        oracle.add_result("P")
with col2:
    if st.button("🔴 B"):
        oracle.add_result("B")
with col3:
    if st.button("⚪️ T"):
        oracle.add_result("T")

if st.button("🔮 ทำนายผลลัพธ์ถัดไป"):
    result = oracle.predict_next()
    st.session_state.initial_shown = True
    st.session_state.prediction = result

if st.button("🅿️ ลบรายการล่าสุด"):
    oracle.remove_last()

if st.button("🧹 เริ่มใหม่ทั้งหมด"):
    oracle.reset()
    st.session_state.initial_shown = False
    st.session_state.prediction = None

if hasattr(st.session_state, "prediction") and st.session_state.prediction:
    pred, module, conf, pattern, miss_streak = st.session_state.prediction
    st.subheader("📍 คำทำนาย:")
    st.write(f"ผลลัพธ์ที่คาดการณ์: {pred}")
    st.write(f"โมดูล: {module}")
    st.write(f"เค้าไพ่: {pattern}")
    st.write(f"ความมั่นใจ: {conf}%")
    st.write(f"❌ แพ้ติดกัน: {miss_streak} ครั้ง")

# แสดง Big Road
st.markdown("### 🕒 Big Road:")
grid = []
for outcome in oracle.result_log:
    grid.append(outcome)

# แสดงผลแบบตาราง
for i in range(0, len(grid), 6):
    row = grid[i:i+6]
    cols = st.columns(len(row))
    for j, val in enumerate(row):
        with cols[j]:
            if val == "P":
                st.markdown("🔵")
            elif val == "B":
                st.markdown("🔴")
            else:
                st.markdown("⚪️")
