import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="OracleEngine", layout="centered")
st.title("🔮 OracleEngine Predictor")

oracle = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []

# ตั้งค่าข้อมูลให้ OracleEngine
oracle.history = st.session_state.oracle_history

# ทำนายผล
if len(oracle.history) >= 6:
    result = oracle.predict_next()

    # แปลง Emoji ตามผล
    prediction = result['prediction']
    emoji_map = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    prediction_display = f"{emoji_map.get(prediction, '')} {prediction}"

    # แปลง developer view ให้อ่านง่าย
    dev_parts = []
    for item in result['developer_view']:
        if item == 'Broken Pattern':
            dev_parts.append("📉 แพทเทิร์นขาด")
        elif "Momentum" in item:
            dev_parts.append(f"⚡ {item}")
        elif "Dragon" in item:
            dev_parts.append("🐉 Dragon Pattern")
        else:
            dev_parts.append(item)
    developer_readable = " + ".join(dev_parts)

    st.markdown("### 🔮 การทำนาย")
    st.markdown(f"## ✅ Prediction: {prediction_display}")
    st.write(f"🎯 **Recommendation:** {result['recommendation']} ✅")
    st.write(f"📊 **Risk Level:** {result['risk']}")
    st.write(f"🧬 **Developer View:** {developer_readable}")
else:
    st.info("กรุณาใส่ผลย้อนหลังอย่างน้อย 6 ตา")

# แสดงผลย้อนหลัง
if st.session_state.oracle_history:
    st.markdown("### 📋 ผลย้อนหลัง")
    emoji_history = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    st.write(' '.join(emoji_history.get(item['main_outcome'], '') for item in st.session_state.oracle_history))

# ปุ่มควบคุม
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🟦 P", use_container_width=True):
        st.session_state.oracle_history.append({'main_outcome': 'P'})
with col2:
    if st.button("🟥 B", use_container_width=True):
        st.session_state.oracle_history.append({'main_outcome': 'B'})
with col3:
    if st.button("⚪️ T", use_container_width=True):
        st.session_state.oracle_history.append({'main_outcome': 'T'})
with col4:
    if st.button("❌ ลบล่าสุด", use_container_width=True):
        if st.session_state.oracle_history:
            st.session_state.oracle_history.pop()

# ปุ่มรีเซ็ตเต็มจอ
st.markdown("")
if st.button("🔄 Reset", use_container_width=True):
    st.session_state.oracle_history.clear()
