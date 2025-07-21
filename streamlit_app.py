import streamlit as st
from oracle_engine import OracleEngine
import pandas as pd

# --- ตั้งค่าหน้าเว็บและ CSS ---
st.set_page_config(page_title="🔮 Oracle AI", layout="centered")

st.markdown("""
    <style>
    /* CSS สำหรับส่วนหัวข้อหลัก */
    .custom-title {
        font-family: 'Georgia', serif; /* ฟอนต์สไตล์คลาสสิก */
        font-size: 3rem; /* ขนาดใหญ่พิเศษ */
        text-align: center;
        color: #FFD700; /* สีทอง */
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7); /* เงาเข้มขึ้น */
        margin-bottom: 1rem;
        font-weight: bold; /* ตัวหนา */
    }
    /* CSS สำหรับข้อความขนาดเล็ก (ใช้กับส่วนเงินทุน) */
    .small-text {
        font-size: 0.95rem; /* ขนาดเล็กลงเล็กน้อย */
        font-weight: normal;
        margin-bottom: 0.25rem; /* ระยะห่างด้านล่าง */
    }
    /* CSS สำหรับ Label ของ st.number_input (เงินทุน, เงินเดิมพัน) */
    .stNumberInput > label {
        font-size: 0.95rem; /* ปรับขนาด label ของ st.number_input ให้เล็กลง */
        font-weight: bold;
    }
    /* CSS สำหรับตัวเลขในช่อง input ของ st.number_input */
    .stNumberInput div[data-baseweb="input"] input {
        font-size: 0.95rem; /* ปรับขนาดตัวเลขในช่อง input ให้เล็กลง */
    }
    /* CSS สำหรับประวัติผลย้อนหลัง */
    .history-display {
        font-size: 1.2rem; /* ขนาดตัวอักษรของ emoji ใหญ่ขึ้นเล็กน้อย */
        word-wrap: break-word; /* ให้ขึ้นบรรทัดใหม่ได้ถ้าข้อความยาว */
        background-color: #f0f2f6; /* สีพื้นหลังอ่อนๆ */
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
        min-height: 40px; /* ขั้นต่ำเพื่อให้มีพื้นที่ */
        display: flex;
        flex-wrap: wrap; /* ให้ emoji ขึ้นบรรทัดใหม่ได้ */
        gap: 5px; /* ช่องว่างระหว่าง emoji */
    }
    /* CSS สำหรับหัวข้อ h4 ที่ต้องการให้เล็กและกระชับ */
    h4 {
        margin-top: 1rem; /* ระยะห่างด้านบน */
        margin-bottom: 0.5rem; /* ระยะห่างด้านล่าง */
        font-size: 1.25rem; /* ขนาดที่เล็กกว่า h3 */
    }
    /* CSS สำหรับผลการทำนาย (ใหม่) */
    .prediction-text {
        font-size: 2rem; /* ทำให้ผลทำนายใหญ่ขึ้น */
        font-weight: bold;
        color: #4CAF50; /* สีเขียว */
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ส่วนหัวของแอป
st.markdown('<div class="custom-title">🔮 Oracle AI</div>', unsafe_allow_html=True)

# --- การเริ่มต้น Session State ---
if "history" not in st.session_state:
    st.session_state.history = [] # เก็บประวัติผล B/P/T
if "money_balance" not in st.session_state: 
    st.session_state.money_balance = 1000.0 # กำหนดค่าเริ่มต้นเป็น float
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100.0 # กำหนดค่าเริ่มต้นเป็น float
if "bet_log" not in st.session_state:
    st.session_state.bet_log = [] # บันทึกรายละเอียดการเดิมพันแต่ละตา
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()

# --- ฟังก์ชัน Callback สำหรับการจัดการประวัติและการเดิมพัน ---
def add_to_history(result):
    """เพิ่มผลลัพธ์ (P/B/T) ลงในประวัติ"""
    st.session_state.history.append(result)

def remove_last_from_history():
    """ลบผลลัพธ์ล่าสุดออกจากประวัติ"""
    if st.session_state.history:
        st.session_state.history.pop()
        
def reset_all_history():
    """รีเซ็ตประวัติทั้งหมด, เงินทุน (กลับไปเป็น 1000.0), บันทึกการเดิมพัน และสร้าง OracleEngine ใหม่"""
    st.session_state.history = []
    st.session_state.money_balance = 1000.0 # รีเซ็ตเงินทุนกลับเป็น 1000.0 (float)
    st.session_state.bet_log = []
    st.session_state.oracle_engine = OracleEngine() # สร้าง Engine ใหม่ เพื่อรีเซ็ต Memory Logic

def record_bet_result(predicted_side, actual_result):
    """
    บันทึกผลการเดิมพันและอัปเดตยอดเงินทุน
    """
    bet_amt = st.session_state.bet_amount
    win_loss = 0.0 # เปลี่ยนเป็น float
    outcome = "Miss"

    if predicted_side in ['P', 'B', 'T']:
        if predicted_side == actual_result:
            outcome = "Hit"
            if predicted_side == 'P':
                win_loss = bet_amt
            elif predicted_side == 'B':
                win_loss = bet_amt * 0.95
            elif predicted_side == 'T':
                win_loss = bet_amt * 8.0 # เปลี่ยนเป็น float
            st.session_state.money_balance += win_loss
        else:
            win_loss = -bet_amt
            st.session_state.money_balance -= bet_amt
    else: # กรณีที่ระบบแนะนำให้ Avoid หรือ prediction_side เป็น '?'
        win_loss = 0.0 # ไม่มีได้เสียเงินจริง
        outcome = "Avoided"

    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}",
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
    })
    
    st.session_state.history.append(actual_result)

# โหลดและอัปเดต Engine
engine = st.session_state.oracle_engine
engine.history = st.session_state.history.copy() 

# --- สถานะเงินทุนและจำนวนเงินเดิมพัน ---
st.markdown("---")
st.session_state.money_balance = st.number_input(
    "💰 เงินทุนปัจจุบัน:", 
    min_value=1.0, # เปลี่ยน min_value เป็น float
    value=st.session_state.money_balance, 
    step=100.0, # เปลี่ยน step เป็น float
    format="%.2f", # ใช้ format สำหรับ float (ทศนิยม 2 ตำแหน่ง)
    help="กำหนดจำนวนเงินทุนเริ่มต้นของคุณ"
)

st.session_state.bet_amount = st.number_input(
    "💸 เงินเดิมพันต่อตา:", 
    min_value=1.0, # เปลี่ยน min_value เป็น float
    value=st.session_state.bet_amount,
    step=10.0, # เปลี่ยน step เป็น float
    format="%.2f", # ใช้ format สำหรับ float (ทศนิยม 2 ตำแหน่ง)
    help="กำหนดจำนวนเงินที่คุณจะเดิมพันในแต่ละตา"
)

if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(engine.history)}** ตา)")

# --- การทำนายและแสดงผลลัพธ์ ---
st.markdown("---")
st.markdown("#### 🔮 ทำนายตาถัดไป:")
prediction_data = None 
next_pred_side = '?' 
conf = 0 

if len(engine.history) >= 20:
    prediction_data = engine.predict_next() 
    
    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score() 
        
        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        # ปรับขนาดผลทำนายให้ใหญ่ขึ้นโดยใช้ CSS class
        st.markdown(f'<div class="prediction-text">{emoji_map.get(next_pred_side, "?")} (Confidence: {conf}%)</div>', unsafe_allow_html=True)
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")
        
        with st.expander("🧬 Developer View"): 
            st.write(prediction_data['developer_view'])
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("— (ไม่สามารถทำนายได้)")
else:
    st.markdown("— (ประวัติไม่ครบ)")

# --- ส่วนบันทึกผลลัพธ์ + ประวัติ + ปุ่มควบคุม ---
st.markdown("---")
st.markdown("#### 📝 บันทึกผลลัพธ์:")
history_emojis = engine.get_history_emojis()

if history_emojis:
    display_history_str = " ".join(history_emojis[-30:]) 
    if len(history_emojis) > 30: 
        display_history_str = "... " + display_history_str
    st.markdown(f"<p class='history-display'>{display_history_str}</p>", unsafe_allow_html=True)
else:
    st.info("ยังไม่มีข้อมูลประวัติ")

col_p_b_t = st.columns(3) 

if prediction_data and isinstance(prediction_data, dict) and 'recommendation' in prediction_data:
    if prediction_data['recommendation'] == "Play ✅":
        with col_p_b_t[0]:
            if st.button(f"🔵 P", key="result_P_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'P')
                st.rerun()
        with col_p_b_t[1]:
            if st.button(f"🔴 B", key="result_B_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'B')
                st.rerun()
        with col_p_b_t[2]:
            if st.button(f"🟢 T", key="result_T_play", use_container_width=True):
                record_bet_result(prediction_data['prediction'], 'T')
                st.rerun()
    elif prediction_data['recommendation'] == "Avoid ❌":
        with col_p_b_t[0]:
            if st.button(f"บันทึก: 🔵 P", key="no_bet_P", use_container_width=True):
                record_bet_result('?', 'P') 
                st.rerun()
        with col_p_b_t[1]:
            if st.button(f"บันทึก: 🔴 B", key="no_bet_B", use_container_width=True):
                record_bet_result('?', 'B')
                st.rerun()
        with col_p_b_t[2]:
            if st.button(f"บันทึก: 🟢 T", key="no_bet_T", use_container_width=True):
                record_bet_result('?', 'T')
                st.rerun()
else: 
    with col_p_b_t[0]:
        if st.button(f"บันทึก: 🔵 P", key="init_P", use_container_width=True):
            record_bet_result('?', 'P')
            st.rerun()
    with col_p_b_t[1]:
        if st.button(f"บันทึก: 🔴 B", key="init_B", use_container_width=True):
            record_bet_result('?', 'B')
            st.rerun()
    with col_p_b_t[2]:
        if st.button(f"บันทึก: 🟢 T", key="init_T", use_container_width=True):
            record_bet_result('?', 'T')
            st.rerun()

col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        st.rerun()
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun()

# --- บันทึกการเดิมพัน (Bet Log) ---
st.markdown("---")
st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# --- ข้อความปิดท้าย ---
st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle AI โดยคุณ")
