import streamlit as st
from oracle_engine import OracleEngine

st.set_page_config(page_title="OracleEngine", layout="centered")
st.title("🔮 OracleEngine Predictor")

oracle = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []

# ============ กลยุทธ์การเล่น ==============
strategy = st.selectbox("🎲 กลยุทธ์ที่คุณใช้", ['แทง P ทุกตา', 'แทง B ทุกตา'])

# ====== คำนวณจำนวนตาแพ้ติดกัน (ไม่รวม T) =======
def calculate_losing_streak(history, strategy_choice):
    lose_against = {'แทง P ทุกตา': 'B', 'แทง B ทุกตา': 'P'}
    target = lose_against[strategy_choice]
    count = 0
    for item in reversed(history):
        outcome = item['main_outcome']
        if outcome == 'T':
            continue  # ข้ามผลเสมอ
        if outcome == target:
            count += 1
        else:
            break
    return count

# ตั้งค่าข้อมูลให้ OracleEngine
oracle.history = st.session_state.oracle_history

# ทำนายผล
if len(oracle.history) >= 6:
    result = oracle.predict_next()

    # รวมข้อความ Developer View
    raw_view = ''.join(result['developer_view'])  # ex: 'Broken Pattern'

    # แปลเป็นข้อความเข้าใจง่าย
    dev_parts = []
    if 'Broken Pattern' in raw_view:
        dev_parts.append("📉 แพทเทิร์นขาด")
    if 'Dragon' in raw_view:
        dev_parts.append("🐉 Dragon Pattern")
    if 'Momentum' in raw_view:
        dev_parts.append("⚡ โมเมนตัมแรง")
    if not dev_parts:
        dev_parts.append("🧠 ไม่มีแพทเทิร์นชัดเจน")

    # แสดงทำนาย
    emoji_map = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    prediction_display = f"{emoji_map.get(result['prediction'], '')} {result['prediction']}"
    st.markdown("### 🔮 การทำนาย")
    st.markdown(f"## ✅ Prediction: {prediction_display}")
    st.write(f"🎯 **Recommendation:** {result['recommendation']} ✅")
    st.write(f"📊 **Risk Level:** {result['risk']}")
    st.write(f"🧬 **Developer View:** {' + '.join(dev_parts)}")
    
    # แพ้ติดกัน
    losing_streak = calculate_losing_streak(oracle.history, strategy)
    st.warning(f"📉 คุณแพ้ติดกัน {losing_streak} ตา (ตามกลยุทธ์ {strategy})")
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
