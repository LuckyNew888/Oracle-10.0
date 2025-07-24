import streamlit as st
import asyncio
import time
from oracle_engine import OracleEngine # ตรวจสอบให้แน่ใจว่าไฟล์ oracle_engine.py อยู่ในไดเรกทอรีเดียวกัน

# กำหนดค่าเริ่มต้นของหน้า Streamlit
st.set_page_config(page_title="ORACLE Baccarat Predictor", layout="centered") # เปลี่ยน title ใน browser tab

# Custom CSS for centered gold text - ฟอนต์จะขึ้นอยู่กับเบราว์เซอร์และการตั้งค่า Streamlit
st.markdown("""
<style>
.center-gold-title {
    text-align: center;
    color: gold;
    font-size: 3.5em; /* Adjust font size as needed */
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 0px; /* Reduce space below title */
    padding-bottom: 0px;
}
.stForm {
    margin-bottom: 0px; /* Reduce space around forms */
}
.stButton>button {
    margin-top: 5px; /* Adjust button spacing */
    margin-bottom: 5px;
}
/* Reduce vertical spacing between elements */
.stMarkdown, .stText, .stInfo, .stWarning {
    margin-top: 0.5rem; /* Default is 1rem */
    margin-bottom: 0.5rem;
}
h3 {
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}
.block-container {
    padding-top: 1rem; /* Adjust overall padding if needed */
    padding-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="center-gold-title">🔮 ORACLE</h1>', unsafe_allow_html=True)

# --- การจัดการสถานะของ OracleEngine ---
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []
if 'gemini_analysis_result' not in st.session_state:
    st.session_state.gemini_analysis_result = None
if 'losing_streak_prediction' not in st.session_state:
    st.session_state.losing_streak_prediction = 0

# ดึง instance ของ OracleEngine จาก session_state มาใช้งาน
oracle = st.session_state.oracle_engine

# --- ส่วนการแสดงผลการทำนาย ---
st.markdown("<h3>🔮 ผลการวิเคราะห์และทำนาย</h3>", unsafe_allow_html=True)

if len(st.session_state.oracle_history) >= 20: 
    # ส่ง history จาก session_state ให้ Engine ทำนาย
    result = oracle.predict_next(st.session_state.oracle_history)

    # แสดงผลการทำนายในรูปแบบที่กำหนด
    emoji_map = {'P': '🟦', 'B': '🟥', 'T': '⚪️', '⚠️': '⚠️'}
    
    # Text for prediction based on result['prediction']
    prediction_text = ""
    if result['prediction'] == 'P':
        prediction_text = "🔵 P"
    elif result['prediction'] == 'B':
        prediction_text = "🔴 B"
    elif result['prediction'] == '⚠️':
        prediction_text = "⚠️ งดเดิมพัน"
    else:
        prediction_text = result['prediction'] # Fallback for '?'

    st.markdown(f"**ทำนาย:** {prediction_text}")
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
        # Check and update losing streak BEFORE adding the result to history
        if oracle.last_prediction_context['prediction'] != '?' and oracle.last_prediction_context['prediction'] != '⚠️':
            prev_predicted_outcome = oracle.last_prediction_context['prediction']
            
            if actual_outcome_for_prev_pred == 'T': # Tie, no change to streak
                pass
            elif prev_predicted_outcome == actual_outcome_for_prev_pred: # Correct prediction
                st.session_state.losing_streak_prediction = 0
            else: # Incorrect prediction
                st.session_state.losing_streak_prediction += 1
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred}) # เพิ่มลง history
        oracle.update_learning_state(actual_outcome_for_prev_pred) # อัปเดตการเรียนรู้ของ Engine
        st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
        st.rerun() 
with col2:
    if st.button("🟥 B", use_container_width=True, key="add_b"):
        actual_outcome_for_prev_pred = 'B'
        if oracle.last_prediction_context['prediction'] != '?' and oracle.last_prediction_context['prediction'] != '⚠️':
            prev_predicted_outcome = oracle.last_prediction_context['prediction']
            if actual_outcome_for_prev_pred == 'T':
                pass
            elif prev_predicted_outcome == actual_outcome_for_prev_pred:
                st.session_state.losing_streak_prediction = 0
            else:
                st.session_state.losing_streak_prediction += 1
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred})
        oracle.update_learning_state(actual_outcome_for_prev_pred)
        st.session_state.gemini_analysis_result = None
        st.rerun()
with col3:
    if st.button("⚪️ T", use_container_width=True, key="add_t"):
        actual_outcome_for_prev_pred = 'T'
        # Ties do not affect losing streak, so only update learning state
        if oracle.last_prediction_context['prediction'] != '?' and oracle.last_prediction_context['prediction'] != '⚠️':
            # Note: We don't change losing_streak_prediction on a 'T'
            pass
        
        st.session_state.oracle_history.append({'main_outcome': actual_outcome_for_prev_pred})
        oracle.update_learning_state(actual_outcome_for_prev_pred)
        st.session_state.gemini_analysis_result = None
        st.rerun()
with col4:
    if st.button("❌ ลบล่าสุด", use_container_width=True, key="remove_last"):
        if st.session_state.oracle_history:
            st.session_state.oracle_history.pop() # ลบจาก history ใน session_state
            
            # ต้องรีเซ็ต Engine และให้มัน "เรียนรู้" ใหม่จากประวัติที่เหลือ เพื่อความถูกต้องของสถานะภายใน
            st.session_state.oracle_engine = OracleEngine() # สร้าง OracleEngine instance ใหม่
            # ใส่ผลลัพธ์ที่เหลือกลับเข้าไปใน Engine ทีละตัว เพื่อให้ Engine เรียนรู้ใหม่ตามลำดับ
            # ในกระบวนการนี้ losing_streak_prediction จะถูกคำนวณใหม่ด้วย
            st.session_state.losing_streak_prediction = 0 # Reset for recalculation
            
            for i in range(len(st.session_state.oracle_history)):
                # Simulate the process: predict, then update learning
                current_history_segment_for_learning = st.session_state.oracle_history[:i+1]
                
                # Check if enough data to predict for this hand
                if len(current_history_segment_for_learning) >= 20:
                    temp_result = st.session_state.oracle_engine.predict_next(current_history_segment_for_learning)
                    # Manually set last_prediction_context for learning
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': temp_result['prediction'],
                        'patterns': temp_result['developer_view'].split(';')[1].replace('DNA Patterns: ', '').split(', ') if 'DNA Patterns: ' in temp_result['developer_view'] else [],
                        'momentum': temp_result['developer_view'].split(';')[2].replace('Momentum: ', '').split(', ') if 'Momentum: ' in temp_result['developer_view'] else [],
                        'intuition_applied': 'Intuition:' in temp_result['developer_view']
                    }
                    
                    # Update losing streak during replay
                    if temp_result['prediction'] != '?' and temp_result['prediction'] != '⚠️':
                        if current_history_segment_for_learning[-1]['main_outcome'] == 'T':
                            pass
                        elif temp_result['prediction'] == current_history_segment_for_learning[-1]['main_outcome']:
                            st.session_state.losing_streak_prediction = 0
                        else:
                            st.session_state.losing_streak_prediction += 1
                else: # Clear last_prediction_context if not enough data for this hand
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False
                    }
                
                # Update learning state after each hand in replay
                st.session_state.oracle_engine.update_learning_state(current_history_segment_for_learning[-1]['main_outcome'])


            st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
            st.rerun()

# --- ปุ่มรีเซ็ตเต็มจอ ---
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear() # ล้างประวัติทั้งหมด
    st.session_state.oracle_engine = OracleEngine() # สร้าง OracleEngine instance ใหม่เพื่อรีเซ็ตสถานะทั้งหมด
    st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
    st.session_state.losing_streak_prediction = 0 # Reset losing streak
    st.rerun()

# --- Gemini Integration ---
st.markdown("<h3>🧠 Gemini AI Insights</h3>", unsafe_allow_html=True)

# Function to simulate API call to Gemini
async def call_gemini_analysis(history_data):
    """
    Simulates an API call to Gemini to get an analysis of the Baccarat history.
    In a real app, this would make an actual network request.
    """
    with st.spinner("กำลังให้ Gemini AI วิเคราะห์สถานการณ์ปัจจุบัน... กรุณารอสักครู่"):
        # Simulate network delay and API call
        await asyncio.sleep(3) # Simulate 3 seconds of processing time

        # Prepare context for Gemini (mocked for now)
        history_str = ' '.join([item['main_outcome'] for item in history_data[-30:]]) # last 30 hands for context
        
        # Mocked Gemini Analysis for demonstration
        mock_analysis = f"""
**การวิเคราะห์โดย Gemini AI (จากประวัติ {len(history_data)} ตา):**

* **รูปแบบปัจจุบัน:** จากประวัติล่าสุด ({history_str}), ห้องนี้แสดงแนวโน้มของ {'**Pingpong (สลับ)**' if 'PBP' in history_str or 'BPB' in history_str else '**Dragon (ลากยาว)**' if 'BBB' in history_str or 'PPP' in history_str else '**การเปลี่ยนแปลงที่ไม่แน่นอน**'}.
* **โมเมนตัม:** {'มีโมเมนตัมของ **เจ้ามือ (B)** ที่แข็งแกร่ง' if history_str.endswith('BBBB') else 'มีโมเมนตัมของ **ผู้เล่น (P)** ที่แข็งแกร่ง' if history_str.endswith('PPPP') else 'โมเมนตัมยัง **ไม่ชัดเจน** หรือกำลังเปลี่ยนทิศทาง'}.
* **ข้อควรพิจารณา:**
    * ระวังโซน `{'**Trap Zone** (ไม่เสถียร/เปลี่ยนเร็ว)' if len(history_data) >= 2 and (history_data[-1]['main_outcome'] != history_data[-2]['main_outcome']) else 'การกลับตัวของรูปแบบเดิม'}`.
    * พิจารณาว่าความยาวของสตรีคปัจจุบัน (ถ้ามี) บ่งชี้ถึงการสิ้นสุดของแนวโน้มหรือไม่.
* **สรุปสำหรับมือถัดไป:** ห้องนี้อยู่ในช่วงที่ {'**คาดเดายาก**' if history_str.count('P') - history_str.count('B') < 3 and history_str.count('B') - history_str.count('P') < 3 else '**มีแนวโน้มชัดเจน**'}. ควรเดิมพันอย่างระมัดระวังเป็นพิเศษ.

"""
        return mock_analysis

if st.button("✨ เรียก Gemini เพื่อวิเคราะห์สถานการณ์ปัจจุบัน", use_container_width=True, key="call_gemini_btn"):
    if len(st.session_state.oracle_history) > 0: # Only call if there's some history
        st.session_state.gemini_analysis_result = asyncio.run(call_gemini_analysis(st.session_state.oracle_history))
    else:
        st.warning("กรุณาใส่ผลลัพธ์อย่างน้อยหนึ่งตา เพื่อให้ Gemini มีข้อมูลสำหรับวิเคราะห์")

if st.session_state.gemini_analysis_result:
    st.markdown(st.session_state.gemini_analysis_result)

# --- Developer View (Moved to bottom and in expander) ---
if len(st.session_state.oracle_history) >= 20: # Only show if enough history for a prediction
    # Call predict_next again just to get the developer_view string
    # This is a bit redundant but ensures dev view is always fresh after all updates
    current_prediction_info = oracle.predict_next(st.session_state.oracle_history)
    with st.expander("🧬 Developer View: คลิกเพื่อดูรายละเอียด"):
        st.code(current_prediction_info['developer_view'], language='text')
