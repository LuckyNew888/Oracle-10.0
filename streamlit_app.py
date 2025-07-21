import streamlit as st
from oracle_engine import OracleEngine
import pandas as pd # เพิ่ม import สำหรับ DataFrame เพื่อใช้แสดงผลตาราง

st.set_page_config(page_title="🔮 Oracle Baccarat AI", layout="centered")

# CSS สำหรับหัวข้อ - จัดหัวข้อให้อยู่กึ่งกลาง
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

# --- การเริ่มต้น Session State ---
# Session State ใช้สำหรับเก็บข้อมูลที่จะคงอยู่ตลอดการใช้งานแอปของผู้ใช้
if "history" not in st.session_state:
    st.session_state.history = [] # เก็บประวัติผล B/P/T
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000 # เงินทุนเริ่มต้น
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100 # จำนวนเงินเดิมพันต่อตาเริ่มต้น
if "bet_log" not in st.session_state:
    st.session_state.bet_log = [] # บันทึกรายละเอียดการเดิมพันแต่ละตา
if "oracle_engine" not in st.session_state:
    # สร้าง OracleEngine ครั้งแรก และเก็บไว้ใน session state
    st.session_state.oracle_engine = OracleEngine()

# --- ฟังก์ชัน Callback สำหรับการจัดการประวัติและการเดิมพัน ---
# ฟังก์ชันเหล่านี้จะถูกเรียกเมื่อปุ่มต่างๆ ถูกคลิก

def add_to_history(result):
    """เพิ่มผลลัพธ์ (P/B/T) ลงในประวัติ"""
    st.session_state.history.append(result)

def remove_last_from_history():
    """ลบผลลัพธ์ล่าสุดออกจากประวัติ"""
    if st.session_state.history:
        st.session_state.history.pop()
        
def reset_all_history():
    """รีเซ็ตประวัติทั้งหมด, เงินทุน, บันทึกการเดิมพัน และสร้าง OracleEngine ใหม่"""
    st.session_state.history = []
    st.session_state.money_balance = 1000 # รีเซ็ตเงินทุน
    st.session_state.bet_log = [] # รีเซ็ตบันทึกการเดิมพัน
    st.session_state.oracle_engine = OracleEngine() # สร้าง Engine ใหม่ เพื่อรีเซ็ต Memory Logic

def record_bet_result(predicted_side, actual_result):
    """
    บันทึกผลการเดิมพันและอัปเดตยอดเงินทุน
    
    Args:
        predicted_side (str): ด้านที่ระบบทำนาย (P, B, T หรือ '?')
        actual_result (str): ผลลัพธ์ที่ออกจริง (P, B, T)
    """
    bet_amt = st.session_state.bet_amount
    win_loss = 0
    outcome = "Miss"

    # คำนวณกำไร/ขาดทุน เฉพาะกรณีที่มีการทำนายและเป็นการเล่น ไม่ใช่การเลี่ยง
    if predicted_side in ['P', 'B', 'T']: # ถ้ามีการทำนาย P/B/T
        if predicted_side == actual_result:
            outcome = "Hit"
            if predicted_side == 'P':
                win_loss = bet_amt
            elif predicted_side == 'B':
                win_loss = bet_amt * 0.95 # แบงค์เกอร์หัก 5%
            elif predicted_side == 'T': # ถ้าทำนาย T และถูก
                win_loss = bet_amt * 8 # อัตราจ่าย Tie (ปกติ 8 เท่า)
            st.session_state.money_balance += win_loss
        else: # ทำนายผิด (P/B/T แต่ผลออกไม่ตรง)
            win_loss = -bet_amt
            st.session_state.money_balance -= bet_amt
    # หาก predicted_side เป็น '?' (ระบบแนะนำให้หลีกเลี่ยง) จะไม่มีการคิดเงินเข้าออก

    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}", # แสดงเครื่องหมาย + หรือ -
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
    })
    
    # เพิ่มผลลัพธ์จริงลงในประวัติของ engine ด้วย
    st.session_state.history.append(actual_result)

# --- โหลดและอัปเดต Engine ---
# โหลด OracleEngine จาก session state
engine = st.session_state.oracle_engine
# อัปเดตประวัติใน Engine ให้ตรงกับ session state เสมอ
engine.history = st.session_state.history.copy() 

# --- ส่วนแสดงสถานะเงินและป้อนจำนวนเงินเดิมพัน ---
st.markdown("---")
st.markdown(f"### 💰 สถานะเงินทุนปัจจุบัน: **{st.session_state.money_balance:.2f} บาท**")
# ผู้ใช้สามารถกำหนดจำนวนเงินเดิมพันต่อตาได้
st.session_state.bet_amount = st.number_input(
    "💸 จำนวนเงินเดิมพันต่อตา:", 
    min_value=1, # เดิมพันขั้นต่ำ 1 บาท
    value=st.session_state.bet_amount, 
    step=10 # เพิ่ม/ลดทีละ 10 บาท
)

# --- ตรวจสอบประวัติเพื่อเริ่มการวิเคราะห์ ---
if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(engine.history)}** ตา)")

# --- การทำนายและแสดงผลลัพธ์ ---
prediction_data = None
if len(engine.history) >= 20:
    # เรียกใช้ predict_next จาก engine เพื่อรับผลการทำนายแบบ dictionary
    prediction_data = engine.predict_next() 
    
    # **สำคัญ:** ตรวจสอบว่า prediction_data เป็น dictionary ที่ถูกต้องหรือไม่
    if isinstance(prediction_data, dict) and 'prediction' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score() # Confidence Score

        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f"### 🔮 ทำนายตาถัดไป: **{emoji_map.get(next_pred_side, '?')}** (Confidence: {conf}%)")
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")
        st.markdown(f"**🧬 Developer View:** {prediction_data['developer_view']}")
    else:
        # แสดงข้อผิดพลาดหากการทำนายไม่ถูกต้อง
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("### 🔮 ทำนายตาถัดไป: — (ไม่สามารถทำนายได้)")
else:
    st.markdown("### 🔮 ทำนายตาถัดไป: — (กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา)")

# --- ส่วนบันทึกผลลัพธ์จริงของตาที่ผ่านมา ---
# ปุ่มเหล่านี้จะใช้หลังจากที่เกมจบรอบแล้ว ผู้ใช้ต้องบันทึกผลลัพธ์ที่ออกจริง
st.markdown("---")
st.markdown("### 📝 บันทึกผลลัพธ์จริงของตาที่ผ่านมา:")

# กรณีที่ระบบมีคำแนะนำให้ 'Play'
if prediction_data and prediction_data['recommendation'] == "Play ✅":
    st.info(f"ระบบแนะนำให้ **{emoji_map.get(prediction_data['prediction'], '')}** ในตานี้. คลิกผลลัพธ์จริงเมื่อตาจบรอบ")
    col_play_p, col_play_b, col_play_t = st.columns(3)
    with col_play_p:
        # เมื่อคลิก, จะบันทึกผลและคำนวณเงิน
        if st.button(f"ผลออก 🔵 (P)", key="result_P_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'P')
            st.rerun() # รีโหลดแอปเพื่ออัปเดต UI
    with col_play_b:
        if st.button(f"ผลออก 🔴 (B)", key="result_B_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'B')
            st.rerun()
    with col_play_t:
        if st.button(f"ผลออก 🟢 (T)", key="result_T_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'T')
            st.rerun()
# กรณีที่ระบบแนะนำให้ 'Avoid'
elif prediction_data and prediction_data['recommendation'] == "Avoid ❌":
    st.warning("⚠️ ระบบแนะนำให้ **งดเดิมพัน** ในตานี้. บันทึกผลลัพธ์จริงเพื่ออัปเดตประวัติเท่านั้น")
    col_avoid_p, col_avoid_b, col_avoid_t = st.columns(3)
    with col_avoid_p:
        if st.button(f"บันทึก: ออก 🔵 (P)", key="no_bet_P", use_container_width=True):
            add_to_history('P') # แค่อัปเดต history ไม่ได้คิดเงิน
            st.rerun()
    with col_avoid_b:
        if st.button(f"บันทึก: ออก 🔴 (B)", key="no_bet_B", use_container_width=True):
            add_to_history('B')
            st.rerun()
    with col_avoid_t:
        if st.button(f"บันทึก: ออก 🟢 (T)", key="no_bet_T", use_container_width=True):
            add_to_history('T')
            st.rerun()
# กรณีที่ยังไม่มีคำแนะนำ (เช่น ประวัติยังไม่ครบ 20 ตา)
else: 
    st.info("กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา เพื่อเริ่มการวิเคราะห์")
    col_init_p, col_init_b, col_init_t = st.columns(3)
    with col_init_p:
        if st.button(f"บันทึก: ออก 🔵 (P)", key="init_P", use_container_width=True):
            add_to_history('P') # แค่อัปเดต history
            st.rerun()
    with col_init_b:
        if st.button(f"บันทึก: ออก 🔴 (B)", key="init_B", use_container_width=True):
            add_to_history('B')
            st.rerun()
    with col_init_t:
        if st.button(f"บันทึก: ออก 🟢 (T)", key="init_T", use_container_width=True):
            add_to_history('T')
            st.rerun()

# --- แสดงบันทึกการเดิมพัน (Bet Log) ---
st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True) # ซ่อน index ของ DataFrame เพื่อความสวยงาม
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# --- แสดงประวัติผลย้อนหลัง ---
st.markdown("---")
st.markdown("### 📜 ประวัติผลย้อนหลัง (ใช้สำหรับการวิเคราะห์ระบบ)")
history_emojis = engine.get_history_emojis()
if history_emojis:
    # แบ่งประวัติเป็นบรรทัดละ 10 ตาเพื่อให้อ่านง่าย
    display_history = []
    for i in range(0, len(history_emojis), 10):
        display_history.append(" ".join(history_emojis[i:i+10]))
    st.markdown("\n".join(display_history))
else:
    st.info("ยังไม่มีข้อมูล")

# --- ปุ่มควบคุมประวัติ (ลบ/รีเซ็ต) ---
# แยกปุ่มเหล่านี้ออกจากส่วนบันทึกผลจริง เพื่อความชัดเจนในการใช้งาน
col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        st.rerun() # รีโหลดแอปหลังจากลบ
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun() # รีโหลดแอปหลังจากรีเซ็ต

# --- ข้อความปิดท้าย ---
st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")
