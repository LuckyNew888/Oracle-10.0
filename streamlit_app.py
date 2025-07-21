# streamlit_app.py
import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="🔮 Oracle Baccarat Oracle AI", layout="centered")

st.title("🔮 Oracle Baccarat AI (SYNAPSE VISION)")

# โหลด engine จาก session state หรือสร้างใหม่
engine = st.session_state.get("engine", OracleEngine())
st.session_state["engine"] = engine

# --- ทำนายตาถัดไป (แสดงบนสุด) ---
next_pred = engine.predict_next()
emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie'}
conf = engine.confidence_score()

st.markdown(f"### 🔮 ทำนายตาถัดไป: {emoji_map.get(next_pred, '?')}  (Confidence: {conf}%)")

# --- ประวัติผลย้อนหลัง ---
st.markdown("### 📜 ประวัติผลย้อนหลัง")
history_emojis = engine.get_history_emojis()
if history_emojis:
    st.markdown(" ".join(history_emojis))
else:
    st.info("ยังไม่มีข้อมูล")

# --- ปุ่มกดผล (P,B,T) และ ลบ / รีเซ็ต ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 Player (P)", use_container_width=True):
        engine.update_history('P')
with col2:
    if st.button("🔴 Banker (B)", use_container_width=True):
        engine.update_history('B')
with col3:
    if st.button("🟢 Tie (T)", use_container_width=True):
        engine.update_history('T')

col4, col5 = st.columns(2)
with col4:
    if st.button("↩️ ลบล่าสุด", use_container_width=True):
        engine.remove_last()
with col5:
    if st.button("🧹 รีเซ็ต", use_container_width=True):
        engine.reset_history()

# แสดงคะแนนความมั่นใจ + การแจ้งเตือน Trap Zone
if engine.in_trap_zone():
    st.warning("⚠️ โซนอันตราย (Trap Zone) - ระวังการเปลี่ยนแปลงเร็ว")

st.markdown("---")
st.caption("ระบบวิเคราะห์ SYNAPSE VISION Baccarat - Oracle AI โดยคุณ")

