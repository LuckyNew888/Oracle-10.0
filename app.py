import streamlit as st
import asyncio
import time
from oracle_engine import OracleEngine # ตรวจสอบให้แน่ใจว่าไฟล์ oracle_engine.py อยู่ในไดเรกทอรีเดียวกัน

# กำหนดค่าเริ่มต้นของหน้า Streamlit
st.set_page_config(page_title="ORACLE Baccarat Predictor", layout="centered") # เปลี่ยน title ใน browser tab

# Custom CSS for centered gold title and reduced spacing
st.markdown("""
<style>
.center-gold-title {
    text-align: center;
    color: gold;
    font-size: 3.5em; /* Adjust font size as needed */
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 0.5rem; /* Reduced space below title */
    padding-bottom: 0px;
}
h3 {
    margin-top: 0.5rem; /* Reduced space above h3 */
    margin-bottom: 0.5rem; /* Reduced space below h3 */
}
.stMarkdown, .stText, .stInfo, .stWarning, .stSuccess {
    margin-top: 0.2rem; /* Reduced space above various text elements */
    margin-bottom: 0.2rem; /* Reduced space below various text elements */
}
.stButton>button {
    margin-top: 0.2rem; /* Reduced space around buttons */
    margin-bottom: 0.2rem;
}
/* Specific style for prediction text to make it larger */
.prediction-text {
    font-size: 1.5em; /* Larger font size for prediction */
    font-weight: bold;
}
/* Reduce padding around columns to make buttons closer */
.st-emotion-cache-1colbu6 { /* This is a Streamlit generated class, might change */
    padding-left: 0.2rem;
    padding-right: 0.2rem;
}

</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="center-gold-title">🔮 ORACLE</h1>', unsafe_allow_html=True)

# --- การจัดการสถานะของ OracleEngine ---
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []
if 'losing_streak_prediction' not in st.session_state:
    st.session_state.losing_streak_prediction = 0

# ดึง instance ของ OracleEngine จาก session_state มาใช้งาน
oracle = st.session_state.oracle_engine

# --- ส่วนการแสดงผลการทำนาย ---
st.markdown("<h3>ผลวิเคราะห์:</h3>", unsafe_allow_html=True) # เปลี่ยนหัวข้อ

if len(st.session_state.oracle_history) >= 20: 
    # ส่ง history จาก session_state ให้ Engine ทำนาย
    result = oracle.predict_next(st.session_state.oracle_history)

    # แสดงผลการทำนายในรูปแบบที่กำหนด
    emoji_map = {'P': '🟦', 'B': '🟥', 'T': '⚪️', '⚠️': '⚠️'}
    
    # Text for prediction based on result['prediction']
    prediction_text = ""
    if result['prediction'] == 'P':
        prediction_text = f"🔵 P"
    elif result['prediction'] == 'B':
        prediction_text = f"🔴 B"
    elif result['prediction'] == '⚠️':
        prediction_text = f"⚠️ งดเดิมพัน"
    else:
        prediction_text = result['prediction'] # Fallback for '?'

    # Adjust font size for prediction using HTML/CSS
    st.markdown(f'<p class="prediction-text">ทำนาย: {prediction_text}</p>', unsafe_allow_html=True)
    
    st.markdown(f"**🎯 Accuracy:** {result['accuracy']}")
    st.markdown(f"**📍 Risk:** {result['risk']}")
    st.markdown(f"**🧾 Recommendation:** {result['recommendation']}")
    
    # แสดงผลแพ้ติดกันของระบบ
    if st.session_state.losing_streak_prediction > 0:
        st.warning(f"**❌ แพ้ติดกัน:** {st.session_state.losing_streak_prediction} ครั้ง")
    else:
        st.success(f"**✅ แพ้ติดกัน:** 0 ครั้ง") # แสดงเป็น 0 เมื่อไม่แพ้ติดกัน
else:
    # แก้ไขข้อความแจ้งเตือนตามที่ร้องขอ
    st.info(f"🔮 ผลการทำนาย กรุณาใส่ผลย้อนหลังอย่างน้อย 20 ตา เพื่อเริ่มต้นการวิเคราะห์ (ปัจจุบันมี {len(st.session_state.oracle_history)} ตา)")

# --- ส่วนแสดงผลย้อนหลัง ---
st.markdown("<h3>📋 ประวัติผลลัพธ์</h3>", unsafe_allow_html=True)
if st.session_state.oracle_history:
    emoji_history = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    st.write(' '.join(emoji_history.get(item['main_outcome'], '') for item in st.session_state.oracle_history))
else:
    st.info("ยังไม่มีผลลัพธ์ในประวัติ")

# --- ปุ่มควบคุมการเพิ่มผลลัพธ์ ---
st.markdown("<h3>➕ บันทึกผลลัพธ์</h3>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🟦 P", use_container_width=True, key="add_p"):
        actual_outcome_for_prev_pred = 'P'
        # ต้องมีข้อมูลเพียงพอสำหรับการทำนายในรอบก่อนหน้าก่อนที่จะอัปเดต losing streak
        if len(st.session_state.oracle_history) >= 20 and oracle.last_prediction_context['prediction'] != '?' and oracle.last_prediction_context['prediction'] != '⚠️':
            prev_predicted_outcome = oracle.last_prediction_context['prediction']
            
            if actual_outcome_for_prev_pred == 'T': # Tie, no change to streak
                pass
            elif prev_predicted_outcome == actual_outcome_for_prev_pred: # Correct prediction
                st.session_state.losing_streak_prediction = 0
            else: # Incorrect prediction
                st.session_state.losing_streak_prediction += 1
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred}) # เพิ่มลง history
        oracle.update_learning_state(actual_outcome_for_prev_pred) # อัปเดตการเรียนรู้ของ Engine
        st.rerun() 
with col2:
    if st.button("🟥 B", use_container_width=True, key="add_b"):
        actual_outcome_for_prev_pred = 'B'
        if len(st.session_state.oracle_history) >= 20 and oracle.last_prediction_context['prediction'] != '?' and oracle.last_prediction_context['prediction'] != '⚠️':
            prev_predicted_outcome = oracle.last_prediction_context['prediction']
            if actual_outcome_for_prev_pred == 'T':
                pass
            elif prev_predicted_outcome == actual_outcome_for_prev_pred:
                st.session_state.losing_streak_prediction = 0
            else:
                st.session_state.losing_streak_prediction += 1
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred})
        oracle.update_learning_state(actual_outcome_for_prev_pred)
        st.rerun()
with col3:
    if st.button("⚪️ T", use_container_width=True, key="add_t"):
        actual_outcome_for_prev_pred = 'T'
        # Ties do not affect losing streak, so only update learning state
        # No need to check for len(history) here, as update_learning_state will handle prediction context
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred})
        oracle.update_learning_state(actual_outcome_for_prev_pred)
        st.rerun()
with col4:
    if st.button("❌ ลบล่าสุด", use_container_width=True, key="remove_last"):
        if st.session_state.oracle_history:
            st.session_state.oracle_history.pop() # ลบจาก history ใน session_state
            
            # เมื่อลบประวัติ ต้องรีเซ็ต Engine และให้มัน "เรียนรู้" ใหม่จากประวัติที่เหลือ
            # สร้าง OracleEngine instance ใหม่ เพื่อล้างสถานะการเรียนรู้ทั้งหมด
            st.session_state.oracle_engine = OracleEngine() 
            st.session_state.losing_streak_prediction = 0 # Reset for recalculation during replay
            
            # ลูปเพิ่มผลลัพธ์ที่เหลือกลับเข้าไปใน Engine ทีละตัวเพื่อให้มัน "เรียนรู้" ใหม่
            for i in range(len(st.session_state.oracle_history)):
                # Simulate the process: predict, then update learning
                current_history_segment_for_replay = st.session_state.oracle_history[:i+1] # History up to this point
                
                # We need to simulate the prediction process for each hand to correctly
                # update the internal state for losing streak and learning
                temp_result = None
                if len(current_history_segment_for_replay) >= 20:
                    temp_result = st.session_state.oracle_engine.predict_next(current_history_segment_for_replay)
                    # Manually set last_prediction_context for learning
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': temp_result['prediction'],
                        'patterns': temp_result['developer_view'].split(';')[1].replace('DNA Patterns: ', '').split(', ') if 'DNA Patterns: ' in temp_result['developer_view'] else [],
                        'momentum': temp_result['developer_view'].split(';')[2].replace('Momentum: ', '').split(', ') if 'Momentum: ' in temp_result['developer_view'] else [],
                        'intuition_applied': 'Intuition:' in temp_result['developer_view']
                    }
                    
                    # Update losing streak during replay
                    if temp_result['prediction'] != '?' and temp_result['prediction'] != '⚠️':
                        if current_history_segment_for_replay[-1]['main_outcome'] == 'T':
                            pass
                        elif temp_result['prediction'] == current_history_segment_for_replay[-1]['main_outcome']:
                            st.session_state.losing_streak_prediction = 0
                        else:
                            st.session_state.losing_streak_prediction += 1
                else: # Clear last_prediction_context if not enough data for this hand
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False
                    }
                
                # Update learning state after each hand in replay
                st.session_state.oracle_engine.update_learning_state(current_history_segment_for_replay[-1]['main_outcome'])
            st.rerun()

# --- ปุ่มรีเซ็ตเต็มจอ ---
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear() # ล้างประวัติทั้งหมด
    st.session_state.oracle_engine = OracleEngine() # สร้าง OracleEngine instance ใหม่เพื่อรีเซ็ตสถานะทั้งหมด
    st.session_state.losing_streak_prediction = 0 # Reset losing streak
    st.rerun()

# --- Developer View (Moved to bottom and in expander) ---
# Call predict_next again just to get the developer_view string
# This is a bit redundant but ensures dev view is always fresh after all updates
if len(st.session_state.oracle_history) >= 20: 
    current_prediction_info = oracle.predict_next(st.session_state.oracle_history)
    with st.expander("🧬 Developer View: คลิกเพื่อดูรายละเอียด"):
        st.code(current_prediction_info['developer_view'], language='text')
