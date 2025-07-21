import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="🔮 Oracle Baccarat Oracle AI", layout="centered")

# --- CSS สำหรับหัวข้อ ---
st.markdown(
    """
    <style>
    .title-center {
        text-align: center;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="title-center">🔮 Oracle Baccarat AI</div>', unsafe_allow_html=True)

# --- เริ่มต้น session history ถ้ายังไม่มี ---
if "history" not in st.session_state:
    st.session_state.history = []

def update_history(result):
    st.session_state.history.append(result)

def remove_last():
    if st.session_state.history:
        st.session_state.history.pop()

def reset_history():
    st.session_state.history = []

# --- สร้าง OracleEngine ใหม่ทุกครั้งจาก history ปัจจุบัน ---
engine = OracleEngine()
engine.history = st.session_state.history.copy()  # copy เพื่อความปลอดภัย

# --- ทำนาย ---
next_pred = engine.predict_next()
emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie'}
conf = engine.confidence_score()
st.markdown(f"### 🔮 ทำนายตาถัดไป: {emoji_map.get(next_pred, '?')}  (Confidence: {conf}%)")

# --- แสดงประวัติเป็น emoji ---
st.markdown("### 📜 ประวัติผลย้อนหลัง")
history_emojis = engine.get_history_emojis()
if history_emojis:
    st.markdown(" ".join(history_emojis))
else:
    st.info("ยังไม่มีข้อมูล")

# --- ปุ่มกด ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔵 Player (P)", use_container_width=True):
        update_history('P')
with col2:
    if st.button("🔴 Banker (B)", use_container_width=True):
        update_history('B')
with col3:
    if st.button("🟢 Tie (T)", use_container_width=True):
        update_history('T')

col4, col5 = st.columns(2)
with col4:
    if st.button("↩️ ลบล่าสุด", use_container_width=True):
        remove_last()
with col5:
    if st.button("🧹 รีเซ็ต", use_container_width=True):
        reset_history()

# --- แจ้งเตือน Trap Zone ---
if engine.in_trap_zone():
    st.warning("⚠️ โซนอันตราย (Trap Zone) - ระวังการเปลี่ยนแปลงเร็ว")

st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")
