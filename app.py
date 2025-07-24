import streamlit as st
from oracle_engine import OracleEngine # ตรวจสอบให้แน่ใจว่าไฟล์ oracle_engine.py อยู่ในไดเรกทอรีเดียวกัน

# กำหนดค่าเริ่มต้นของหน้า Streamlit
st.set_page_config(page_title="SYNAPSE VISION Baccarat", layout="centered")
st.title("🧠 SYNAPSE VISION Baccarat Predictor")
st.markdown("---")

# --- การจัดการสถานะของ OracleEngine ---
# ตรวจสอบว่า OracleEngine และ history ถูกเก็บใน session_state หรือยัง
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []

# ดึง instance ของ OracleEngine จาก session_state มาใช้งาน
oracle = st.session_state.oracle_engine
# อัปเดต history ใน OracleEngine ด้วยข้อมูลจาก session_state
# การทำแบบนี้เพื่อให้แน่ใจว่า OracleEngine ใช้ข้อมูลประวัติที่ถูกต้องเสมอเมื่อมีการ re-run
oracle.history = st.session_state.oracle_history

# ============ กลยุทธ์ส่วนตัวของผู้ใช้ (สำหรับคำนวณตาแพ้เท่านั้น) ==============
st.markdown("### 🎲 กลยุทธ์ส่วนตัวของคุณ (สำหรับคำนวณตาแพ้ติดกันเท่านั้น)")
st.info("ส่วนนี้ใช้เพื่อช่วยคุณติดตาม 'ตาที่แพ้ติดกัน' จากกลยุทธ์ง่ายๆ ที่คุณเลือกเอง ไม่ใช่ส่วนหนึ่งของการทำนายของระบบ SYNAPSE VISION Baccarat")
strategy = st.selectbox("เลือกกลยุทธ์ของคุณ:", 
                        ['แทง P ทุกตา', 'แทง B ทุกตา'], 
                        key="strategy_select")

# ====== คำนวณจำนวนตาแพ้ติดกัน (ไม่รวม T) =======
def calculate_losing_streak(history_data, strategy_choice):
    """
    คำนวณจำนวนตาที่แพ้ติดต่อกันตามกลยุทธ์ที่เลือก
    โดยไม่นับผลเสมอ (T)
    """
    lose_against = {'แทง P ทุกตา': 'B', 'แทง B ทุกตา': 'P'}
    target_outcome_for_loss = lose_against.get(strategy_choice)

    if not target_outcome_for_loss:
        return 0 # หากไม่มีกลยุทธ์ที่เลือก

    count = 0
    # ย้อนกลับดูประวัติจากล่าสุด
    for item in reversed(history_data):
        outcome = item['main_outcome']
        if outcome == 'T':
            continue  # ข้ามผลเสมอ
        if outcome == target_outcome_for_loss:
            count += 1 # แพ้
        else:
            break # ชนะหรือเปลี่ยนฝั่งแล้ว
    return count

# --- ส่วนการแสดงผลการทำนาย ---
st.markdown("---")
st.markdown("### 🔮 ผลการวิเคราะห์และทำนาย")

# oracle.predict_next() มีเงื่อนไขว่าต้องมีประวัติอย่างน้อย 20 ตา
if len(oracle.history) >= 20: 
    result = oracle.predict_next()

    # แสดงผลตามโครงสร้าง Developer Mode
    emoji_map = {'P': '🟦', 'B': '🟥', 'T': '⚪️', '⚠️': '⚠️'}
    prediction_display = f"## {emoji_map.get(result['prediction'], '')} {result['prediction']}"
    
    st.markdown(f"🧬 **Developer View:** {result['developer_view']}")
    st.markdown(f"") # บรรทัดว่าง
    st.markdown(f"### {prediction_display}")
    st.markdown(f"🎯 **Accuracy:** {result['accuracy']}")
    st.markdown(f"📍 **Risk:** {result['risk']}")
    st.markdown(f"🧾 **Recommendation:** {result['recommendation']}")
    
    # แสดงจำนวนตาที่แพ้ติดกัน (UI เสริม)
    losing_streak = calculate_losing_streak(oracle.history, strategy)
    if losing_streak > 0:
        st.warning(f"📉 คุณแพ้ติดกัน {losing_streak} ตา (ตามกลยุทธ์ '{strategy}')")
    else:
        st.info(f"🎉 ยังไม่มีตาที่แพ้ติดกัน (ตามกลยุทธ์ '{strategy}')")

else:
    st.info(f"กรุณาใส่ผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ SYNAPSE VISION Baccarat เริ่มต้นการวิเคราะห์ (ปัจจุบันมี {len(oracle.history)} ตา)")

# --- ส่วนแสดงผลย้อนหลัง ---
st.markdown("---")
st.markdown("### 📋 ประวัติผลลัพธ์")
if st.session_state.oracle_history:
    emoji_history = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    st.write(' '.join(emoji_history.get(item['main_outcome'], '') for item in st.session_state.oracle_history))
else:
    st.info("ยังไม่มีผลลัพธ์ในประวัติ")

# --- ปุ่มควบคุมการเพิ่มผลลัพธ์ ---
st.markdown("---")
st.markdown("### ➕ บันทึกผลลัพธ์")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🟦 P", use_container_width=True, key="add_p"):
        oracle.add_result('P')
        st.session_state.oracle_history.append({'main_outcome': 'P'}) # อัปเดต UI history
        st.rerun() # <<< แก้ไขตรงนี้: ใช้ st.rerun() แทน st.experimental_rerun()
with col2:
    if st.button("🟥 B", use_container_width=True, key="add_b"):
        oracle.add_result('B')
        st.session_state.oracle_history.append({'main_outcome': 'B'})
        st.rerun() # <<< แก้ไขตรงนี้
with col3:
    if st.button("⚪️ T", use_container_width=True, key="add_t"):
        oracle.add_result('T')
        st.session_state.oracle_history.append({'main_outcome': 'T'})
        st.rerun() # <<< แก้ไขตรงนี้
with col4:
    if st.button("❌ ลบล่าสุด", use_container_width=True, key="remove_last"):
        if st.session_state.oracle_history:
            # เพื่อให้สถานะของ OracleEngine สอดคล้องกับการลบ
            # วิธีที่ดีที่สุดคือ reset Engine แล้วใส่ประวัติใหม่ที่ไม่รวมตัวที่ถูกลบ
            st.session_state.oracle_history.pop() # ลบจาก UI history
            oracle.reset_history() # รีเซ็ต Engine ทั้งหมด
            # ใส่ประวัติที่เหลือกลับเข้าไปใน Engine ทีละตัวเพื่อให้มัน "เรียนรู้" ใหม่
            for item in st.session_state.oracle_history:
                oracle.add_result(item['main_outcome'])
            st.rerun() # <<< แก้ไขตรงนี้

# ปุ่มรีเซ็ตเต็มจอ
st.markdown("")
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear()
    st.session_state.oracle_engine.reset_history() # เรียก reset_history ของ OracleEngine ด้วย
    st.rerun() # <<< แก้ไขตรงนี้
