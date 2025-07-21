# streamlit_app.py

import streamlit as st
from oracle_engine import OracleBaccarat

st.set_page_config(page_title="🔮 Oracle Baccarat", layout="centered")

st.title("🔮 Oracle Baccarat Analyzer")
st.markdown("AI วิเคราะห์เค้าไพ่บาคาร่าแบบเรียลไทม์")

# โหลด AI
oracle = st.session_state.get("oracle", OracleBaccarat())

# เซฟเข้า session
st.session_state["oracle"] = oracle

# ปุ่มกดผล
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 Player", use_container_width=True):
        oracle.update_history('P')
with col2:
    if st.button("🔴 Banker", use_container_width=True):
        oracle.update_history('B')
with col3:
    if st.button("🟢 Tie", use_container_width=True):
        oracle.update_history('T')

# ปุ่มจัดการประวัติ
col4, col5 = st.columns(2)
with col4:
    if st.button("↩️ ลบล่าสุด", use_container_width=True):
        oracle.remove_last()
with col5:
    if st.button("🧹 รีเซ็ต", use_container_width=True):
        oracle.reset_history()

# แสดงประวัติเป็น emoji
st.markdown("### ✅ ประวัติ:")
st.markdown("".join(oracle.get_history_emojis()) or "ยังไม่มีข้อมูล")

# วิเคราะห์ผลทันที
prediction = oracle.get_prediction()
predict_emoji = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '❓': '❓ ยังไม่แน่ใจ'}
st.markdown("### 🔍 ทำนายตาถัดไป:")
st.subheader(predict_emoji.get(prediction, "❓ ยังไม่แน่ใจ"))

# ส่วนท้าย
st.markdown("---")
st.caption("ระบบวิเคราะห์เค้าไพ่ 🔮 Oracle AI | เวอร์ชันทดลองใช้")
