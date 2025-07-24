import streamlit as st
import asyncio
import time
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
if 'gemini_analysis_result' not in st.session_state:
    st.session_state.gemini_analysis_result = None

# ดึง instance ของ OracleEngine จาก session_state มาใช้งาน
oracle = st.session_state.oracle_engine
# อัปเดต history ใน OracleEngine ด้วยข้อมูลจาก session_state
oracle.history = st.session_state.oracle_history

# ====== คำนวณสตรีคปัจจุบันของ P หรือ B (ไม่รวม T) =======
def get_current_pb_streak(history_data):
    """
    Calculates the current streak length of P or B, ignoring T.
    Returns (outcome_type, streak_length) e.g., ('P', 5) or (None, 0) if no P/B.
    """
    if not history_data:
        return None, 0

    streak_type = None
    streak_length = 0

    # Find the last non-T outcome to start the streak
    start_index = -1
    for i in range(len(history_data) - 1, -1, -1):
        if history_data[i]['main_outcome'] != 'T':
            streak_type = history_data[i]['main_outcome']
            start_index = i
            break
    
    if streak_type is None: # Only T's or empty history
        return None, 0

    # Count the streak backwards from start_index
    for i in range(start_index, -1, -1):
        current_outcome = history_data[i]['main_outcome']
        if current_outcome == 'T':
            continue # T doesn't break the streak, it's ignored
        if current_outcome == streak_type:
            streak_length += 1
        else:
            break # Streak broken by a different outcome

    return streak_type, streak_length

# --- ส่วนการแสดงผลการทำนาย ---
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
    
    # แสดงสตรีคปัจจุบัน (P/B)
    current_streak_type, current_streak_length = get_current_pb_streak(oracle.history)
    if current_streak_type and current_streak_length > 0:
        st.info(f"📈 ห้องนี้กำลังมีสตรีค **{current_streak_type}** ติดกัน **{current_streak_length}** ตา (ไม่นับเสมอ)")
    else:
        st.info("📊 ยังไม่มีสตรีค P/B ที่ชัดเจน (ไม่นับเสมอ)")

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
        st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
        st.rerun() # บังคับให้ Streamlit refresh เพื่อแสดงผลล่าสุด
with col2:
    if st.button("🟥 B", use_container_width=True, key="add_b"):
        oracle.add_result('B')
        st.session_state.oracle_history.append({'main_outcome': 'B'})
        st.session_state.gemini_analysis_result = None
        st.rerun()
with col3:
    if st.button("⚪️ T", use_container_width=True, key="add_t"):
        oracle.add_result('T')
        st.session_state.oracle_history.append({'main_outcome': 'T'})
        st.session_state.gemini_analysis_result = None
        st.rerun()
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
            st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
            st.rerun()

# --- ปุ่มรีเซ็ตเต็มจอ ---
st.markdown("---")
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear()
    st.session_state.oracle_engine.reset_history() # เรียก reset_history ของ OracleEngine ด้วย
    st.session_state.gemini_analysis_result = None # Clear previous Gemini analysis
    st.rerun()

# --- Gemini Integration ---
st.markdown("---")
st.markdown("### 🧠 Gemini AI Insights")

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
        
        # --- Conceptual Real API Call (Not runnable in this environment) ---
        # import requests
        # payload = {
        #     "contents": [
        #         {
        #             "role": "user",
        #             "parts": [
        #                 {"text": f"Based on this Baccarat history: {history_str}. Provide a concise analysis of patterns, momentum, and potential risks. Focus on actionable insights for prediction. Use Thai language. Format as a markdown summary."},
        #             ]
        #         }
        #     ],
        #     "generationConfig": {
        #         "responseMimeType": "text/plain", # or "application/json" if you need structured output
        #     }
        # }
        # api_key = "" # API key provided by environment
        # api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
        # response = requests.post(api_url, json=payload)
        # if response.status_code == 200:
        #     response_data = response.json()
        #     gemini_analysis = response_data['candidates'][0]['content']['parts'][0]['text']
        # else:
        #     gemini_analysis = "เกิดข้อผิดพลาดในการเชื่อมต่อกับ Gemini หรือ API Key ไม่ถูกต้อง."
        # --- End of Conceptual Real API Call ---

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
    if len(oracle.history) > 0: # Only call if there's some history
        st.session_state.gemini_analysis_result = asyncio.run(call_gemini_analysis(oracle.history))
    else:
        st.warning("กรุณาใส่ผลลัพธ์อย่างน้อยหนึ่งตา เพื่อให้ Gemini มีข้อมูลสำหรับวิเคราะห์")

if st.session_state.gemini_analysis_result:
    st.markdown(st.session_state.gemini_analysis_result)

