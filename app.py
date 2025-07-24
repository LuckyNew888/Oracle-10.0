
import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="OracleEngine", layout="centered")
st.title("🔮 OracleEngine Predictor")

oracle = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []

# ผลล่าสุด
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🟦 P"):
        st.session_state.oracle_history.append({'main_outcome': 'P'})
with col2:
    if st.button("🟥 B"):
        st.session_state.oracle_history.append({'main_outcome': 'B'})
with col3:
    if st.button("⚪️ T"):
        st.session_state.oracle_history.append({'main_outcome': 'T'})

if st.button("🔄 Reset"):
    st.session_state.oracle_history.clear()

# แสดงผลย้อนหลัง
if st.session_state.oracle_history:
    st.markdown("### 📋 ผลย้อนหลัง")
    st.write(' '.join(item['main_outcome'] for item in st.session_state.oracle_history))

# ตั้งค่าข้อมูลให้ OracleEngine
oracle.history = st.session_state.oracle_history

# ทำนายผล
if len(oracle.history) >= 6:
    result = oracle.predict_next()
    st.markdown("### 🔮 การทำนาย")
    st.write(f"✅ **Prediction:** {result['prediction']}")
    st.write(f"🎯 **Recommendation:** {result['recommendation']}")
    st.write(f"📊 **Risk Level:** {result['risk']}")
    st.write(f"🧬 **Developer View:** {result['developer_view']}")
else:
    st.info("กรุณาใส่ผลย้อนหลังอย่างน้อย 6 ตา")
