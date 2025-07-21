import streamlit as st
from oracle_engine import OracleEngine
import pandas as pd # เพิ่ม import สำหรับ DataFrame

st.set_page_config(page_title="🔮 Oracle Baccarat AI", layout="centered")

# CSS สำหรับหัวข้อ
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

# เริ่มต้น session state ที่จำเป็นทั้งหมด
if "history" not in st.session_state:
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000 # เงินเริ่มต้น
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100 # จำนวนเงินเดิมพันต่อตา
if "bet_log" not in st.session_state:
    st.session_state.bet_log = [] # บันทึกการเดิมพัน (pred, actual, win/loss, amount, balance, outcome)

# ฟังก์ชันสำหรับอัปเดต history ของ engine
def add_to_history(result):
    st.session_state.history.append(result)

def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        # ถ้าลบ history แล้ว มีผลต่อ bet_log ด้วยหรือไม่? ในที่นี้ไม่ได้ผูกกันโดยตรง
        # หากต้องการให้ผูกกันต้องมีลอจิกซับซ้อนขึ้น
        
def reset_all_history():
    st.session_state.history = []
    st.session_state.money_balance = 1000 # รีเซ็ตเงินด้วย
    st.session_state.bet_log = []
    # สร้าง OracleEngine ใหม่เพื่อรีเซ็ต memory_failed_patterns
    st.session_state.oracle_engine = OracleEngine()

# ฟังก์ชันสำหรับบันทึกผลการเดิมพันและอัปเดตเงิน
def record_bet_result(predicted_side, actual_result):
    bet_amt = st.session_state.bet_amount
    win_loss = 0
    outcome = "Miss"

    # คำนวณกำไร/ขาดทุน
    # หากมีการทำนาย (ไม่ใช่ '?') และไม่ได้อยู่ในโหมด Avoid
    if predicted_side != '?' and predicted_side != '-':
        if predicted_side == actual_result:
            outcome = "Hit"
            if predicted_side == 'P':
                win_loss = bet_amt
            elif predicted_side == 'B':
                win_loss = bet_amt * 0.95 # แบงค์เกอร์หัก 5%
            elif predicted_side == 'T': # ถ้าทำนาย T และถูก
                win_loss = bet_amt * 8 # อัตราจ่าย Tie
            st.session_state.money_balance += win_loss
        else: # ทำนายผิด
            win_loss = -bet_amt
            st.session_state.money_balance -= bet_amt
    # ถ้ามีการทำนายเป็น '?' หรือ '-'' และผู้ใช้คลิกบันทึกผล หมายถึงระบบแนะนำให้หลีกเลี่ยง
    # ดังนั้นจะไม่มีการหักเงินเดิมพัน

    st.session_state.bet_log.append({
        "Predict": predicted_side,
        "Actual": actual_result,
        "Win/Loss": f"{win_loss:+.2f}", # แสดงเครื่องหมาย + หรือ -
        "Balance": f"{st.session_state.money_balance:.2f}",
        "Outcome": outcome
    })
    
    # อัปเดต history ของ engine ด้วยผลลัพธ์จริง
    st.session_state.history.append(actual_result)

    # แจ้ง engine เกี่ยวกับผลการทำนาย (เพื่อ Memory Logic)
    # สมมติว่า OracleEngine จะจัดการเรื่อง Memory Logic ภายใน predict_next หลังจากรู้ผลจริง
    # หรืออาจจะต้องเรียกเมธอด update_memory_logic(predicted, actual)
    # เพื่อความง่ายในตอนนี้, memory logic จะทำงานใน predict_next จาก history ล่าสุด

# สร้าง/โหลด engine จาก session state
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
engine = st.session_state.oracle_engine
engine.history = st.session_state.history.copy() # อัปเดต history ใน engine

# ส่วนแสดงสถานะเงินและป้อนจำนวนเงินเดิมพัน
st.markdown("---")
st.markdown(f"### 💰 สถานะเงินทุนปัจจุบัน: **{st.session_state.money_balance:.2f} บาท**")
st.session_state.bet_amount = st.number_input("💸 จำนวนเงินเดิมพันต่อตา:", min_value=1, value=st.session_state.bet_amount, step=10)

# เช็คประวัติ 20 ตา
if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ {len(engine.history)} ตา)")

# แสดงทำนายเมื่อมีข้อมูลครบ 20 ตา
prediction_data = None
if len(engine.history) >= 20:
    prediction_data = engine.predict_next() # predict_next ควรคืนค่าเป็น dict แล้ว
    next_pred_side = prediction_data['prediction']
    conf = engine.confidence_score() # Confidence ยังเรียกใช้เหมือนเดิม

    emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— (ไม่มีคำแนะนำ)'}

    st.markdown(f"### 🔮 ทำนายตาถัดไป: **{emoji_map.get(next_pred_side, '?')}** (Confidence: {conf}%)")
    st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
    st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")
    st.markdown(f"**🧬 Developer View:** {prediction_data['developer_view']}")
else:
    st.markdown("### 🔮 ทำนายตาถัดไป: — (กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา)")

# ปุ่มสำหรับบันทึกผลลัพธ์จริงหลังการเดิมพัน (เพื่อคำนวณกำไร/ขาดทุน)
st.markdown("---")
st.markdown("### 📝 บันทึกผลลัพธ์จริงของตาที่ผ่านมา:")

if prediction_data and prediction_data['recommendation'] == "Play ✅":
    st.info(f"ระบบแนะนำให้ **{emoji_map.get(prediction_data['prediction'], '')}** ในตานี้. คลิกผลลัพธ์จริงเมื่อตาจบรอบ")
    col_play_p, col_play_b, col_play_t = st.columns(3)
    with col_play_p:
        if st.button(f"ผลออก 🔵 (P)", key="result_P_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'P')
            st.rerun()
    with col_play_b:
        if st.button(f"ผลออก 🔴 (B)", key="result_B_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'B')
            st.rerun()
    with col_play_t:
        if st.button(f"ผลออก 🟢 (T)", key="result_T_play", use_container_width=True):
            record_bet_result(prediction_data['prediction'], 'T')
            st.rerun()
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
else: # กรณีที่ยังไม่มีคำแนะนำ (เช่น ประวัติยังไม่ครบ)
    st.info("กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา เพื่อเริ่มการวิเคราะห์")
    col_init_p, col_init_b, col_init_t = st.columns(3)
    with col_init_p:
        if st.button(f"บันทึก: ออก 🔵 (P)", key="init_P", use_container_width=True):
            add_to_history('P') # แค่อัปเดต history ไม่ได้คิดเงิน
            st.rerun()
    with col_init_b:
        if st.button(f"บันทึก: ออก 🔴 (B)", key="init_B", use_container_width=True):
            add_to_history('B')
            st.rerun()
    with col_init_t:
        if st.button(f"บันทึก: ออก 🟢 (T)", key="init_T", use_container_width=True):
            add_to_history('T')
            st.rerun()


# แสดง Bet Log
st.markdown("### 📊 บันทึกการเดิมพัน")
if st.session_state.bet_log:
    df_log = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(df_log, use_container_width=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# แสดงประวัติเป็น emoji
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

# ปุ่มควบคุมประวัติ (แยกส่วนจากปุ่มบันทึกผลจริง)
col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        st.rerun() # Rerun หลังจากลบเพื่ออัปเดต UI ทันที
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun() # Rerun หลังจากรีเซ็ตเพื่ออัปเดต UI ทันที


st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")
