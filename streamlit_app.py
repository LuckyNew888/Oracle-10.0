import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="🔮 Oracle Baccarat Oracle AI", layout="centered")

# CSS สำหรับหัวข้อ
st.markdown("""
    <style>
    .title-center {
        text-align: center;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="title-center">🔮 Oracle Baccarat AI</div>', unsafe_allow_html=True)

# เริ่มต้น session history
if "history" not in st.session_state:
    st.session_state.history = []

# Define callback functions
def add_to_history(result):
    st.session_state.history.append(result)

def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()

def reset_all_history():
    st.session_state.history = []

# สร้าง engine ใหม่จาก history
engine = OracleEngine()
engine.history = st.session_state.history.copy()

# เช็คประวัติ 20 ตา
if len(engine.history) < 20:
    st.warning(f"กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ {len(engine.history)} ตา)")

# แสดงทำนายเมื่อมีข้อมูลครบ 20 ตา
if len(engine.history) >= 20:
    next_pred = engine.predict_next()
    emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie'}
    conf = engine.confidence_score()
    st.markdown(f"### 🔮 ทำนายตาถัดไป: {emoji_map.get(next_pred, '?')}  (Confidence: {conf}%)")
else:
    st.markdown("### 🔮 ทำนายตาถัดไป: — (กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา)")

# แสดงประวัติเป็น emoji
st.markdown("### 📜 ประวัติผลย้อนหลัง")
history_emojis = engine.get_history_emojis()
if history_emojis:
    st.markdown(" ".join(history_emojis))
else:
    st.info("ยังไม่มีข้อมูล")

# ปุ่มกดพร้อม key และ callback
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🔵 Player (P)", key="btnP", use_container_width=True, on_click=add_to_history, args=('P',))
with col2:
    st.button("🔴 Banker (B)", key="btnB", use_container_width=True, on_click=add_to_history, args=('B',))
with col3:
    st.button("🟢 Tie (T)", key="btnT", use_container_width=True, on_click=add_to_history, args=('T',))

col4, col5 = st.columns(2)
with col4:
    st.button("↩️ ลบล่าสุด", key="btnDel", use_container_width=True, on_click=remove_last_from_history)
with col5:
    st.button("🧹 รีเซ็ต", key="btnReset", use_container_width=True, on_click=reset_all_history)

# แจ้งเตือน Trap Zone ถ้ามีประวัติมากพอ
if len(engine.history) >= 20 and engine.in_trap_zone():
    st.warning("⚠️ โซนอันตราย (Trap Zone) - ระวังการเปลี่ยนแปลงเร็ว")

st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")
