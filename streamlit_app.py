import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="🔮 Oracle Baccarat Oracle AI", layout="centered")

# --- ตั้งค่า style CSS เล็กน้อยเพื่อจัดกลางและลดขนาด font ---
st.markdown(
    """
    <style>
    .title-center {
        text-align: center;
        font-size: 1.25rem;  /* ประมาณ h4 */
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# โหลด engine จาก session หรือสร้างใหม่
if "engine" not in st.session_state:
    st.session_state.engine = OracleEngine()
engine = st.session_state.engine

# --- หัวข้อ ให้อยู่กลาง และตัวหนังสือเล็กลง 2 ระดับ ---
st.markdown('<div class="title-center">🔮 Oracle Baccarat AI</div>', unsafe_allow_html=True)

# --- ทำนายตาถัดไป ---
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

# --- ปุ่มกดผล (แก้บั๊ก กดแล้วเพิ่มแค่ครั้งเดียว) ---
col1, col2, col3 = st.columns(3)

def add_result(r):
    engine.update_history(r)
    # รีเฟรชหน้าเลย (force rerun)
    st.experimental_rerun()

with col1:
    if st.button("🔵 Player (P)", use_container_width=True):
        add_result('P')
with col2:
    if st.button("🔴 Banker (B)", use_container_width=True):
        add_result('B')
with col3:
    if st.button("🟢 Tie (T)", use_container_width=True):
        add_result('T')

# --- ปุ่มลบล่าสุด / รีเซ็ต ---
col4, col5 = st.columns(2)

def remove_last():
    engine.remove_last()
    st.experimental_rerun()

def reset_all():
    engine.reset_history()
    st.experimental_rerun()

with col4:
    if st.button("↩️ ลบล่าสุด", use_container_width=True):
        remove_last()
with col5:
    if st.button("🧹 รีเซ็ต", use_container_width=True):
        reset_all()

# --- แจ้งเตือน Trap Zone ---
if engine.in_trap_zone():
    st.warning("⚠️ โซนอันตราย (Trap Zone) - ระวังการเปลี่ยนแปลงเร็ว")

st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")

