import streamlit as st
from oracle_core import OracleBrain

st.set_page_config(layout="wide")

if "oracle" not in st.session_state:
    st.session_state.oracle = OracleBrain()
if "initial_shown" not in st.session_state:
    st.session_state.initial_shown = False

oracle = st.session_state.oracle

st.markdown("## 🔮 ORACLE v5")

# --- ปุ่มใส่ผลลัพธ์ ---
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

# --- ปุ่มคำสั่งอื่น ---
if st.button("🔮 ทำนายผลลัพธ์ถัดไป"):
    result = oracle.predict_next()
    st.session_state.prediction = result
    st.session_state.initial_shown = True

if st.button("🅿️ ลบรายการล่าสุด"):
    oracle.remove_last()

if st.button("🧹 เริ่มใหม่ทั้งหมด"):
    oracle.reset()
    st.session_state.prediction = None
    st.session_state.initial_shown = False

# --- แสดงค่าทำนายล่าสุด ---
if st.session_state.get("prediction"):
    pred, module, conf, pattern, miss = st.session_state.prediction
    st.markdown(f"### 📍 คำทำนาย: **{pred}**")
    st.write(f"🧠 โมดูล: {module}")
    st.write(f"📊 เค้าไพ่: {pattern}")
    st.write(f"🔎 ความมั่นใจ: {conf}%")
    st.write(f"❌ แพ้ติดกัน: {miss} ครั้ง")

# --- แสดง Big Road ---
st.markdown("### 🕒 Big Road:")

grid = oracle.result_log
cols_per_row = 20
rows = [[] for _ in range(6)]  # สูงสุด 6 แถว

col_idx = 0
for i, val in enumerate(grid):
    row = i % 6
    if val == "P":
        rows[row].append("🔵")
    elif val == "B":
        rows[row].append("🔴")
    elif val == "T":
        rows[row].append("⚪️")

# สลับแถวเป็นคอลัมน์ (แนวนอน)
for r in rows:
    if r:
        st.write(" ".join(r))
