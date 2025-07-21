import streamlit as st
from oracle_engine import OracleEngine
import pandas as pd

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

# --- การเริ่มต้น Session State ---
if "history" not in st.session_state:
    st.session_state.history = []
if "money_balance" not in st.session_state:
    st.session_state.money_balance = 1000
if "bet_amount" not in st.session_state:
    st.session_state.bet_amount = 100
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []
if "oracle_engine" not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()

# --- ฟังก์ชัน Callback ---
def add_to_history(result):
    st.session_state.history.append(result)

def remove_last_from_history():
    if st.session_state.history:
        st.session_state.history.pop()
        
def reset_all_history():
    st.session_state.history = []
    st.session_state.money_balance = 1000
    st.session_state.bet_log = []
    st.session_state.oracle_engine = OracleEngine()

def record_bet_result(predicted_side, actual_result):
    bet_amt = st.session_state.bet_amount
    win_loss = 0
    outcome = "Miss"

    if predicted_side in ['P', 'B', 'T']:
        if predicted_side == actual_result:
            outcome = "Hit"
            if predicted_side == 'P':
                win_loss = bet_amt
            elif predicted_side == 'B':
                win_loss = bet_amt * 0.95
            elif predicted_side == 'T':
                win_loss = bet_amt * 8
            st.session_state.money_balance += win_loss
        else:
            win_loss = -bet_amt
            st.session_state.money_balance -= bet_amt

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

# --- ส่วนแสดงสถานะเงินและป้อนจำนวนเงินเดิมพัน ---
st.markdown("---")
st.markdown(f"### 💰 สถานะเงินทุนปัจจุบัน: **{st.session_state.money_balance:.2f} บาท**")
st.session_state.bet_amount = st.number_input(
    "💸 จำนวนเงินเดิมพันต่อตา:", 
    min_value=1, 
    value=st.session_state.bet_amount, 
    step=10
)

# เช็คประวัติ 20 ตา
if len(engine.history) < 20:
    st.warning(f"⚠️ กรุณาบันทึกผลย้อนหลังอย่างน้อย 20 ตา เพื่อให้ระบบวิเคราะห์ได้แม่นยำ\n(ตอนนี้บันทึกไว้ **{len(engine.history)}** ตา)")

# --- การทำนายและแสดงผลลัพธ์ ---
prediction_data = None
next_pred_side = '?' # Default value
conf = 0 # Default confidence

# ทำนายเมื่อมีข้อมูลครบ 20 ตา
if len(engine.history) >= 20:
    prediction_data = engine.predict_next() 
    
    if isinstance(prediction_data, dict) and 'prediction' in prediction_data and 'recommendation' in prediction_data:
        next_pred_side = prediction_data['prediction']
        conf = engine.confidence_score() 
        
        emoji_map = {'P': '🔵 Player', 'B': '🔴 Banker', 'T': '🟢 Tie', '?': '— ไม่มีคำแนะนำ'}

        st.markdown(f"### 🔮 ทำนายตาถัดไป: **{emoji_map.get(next_pred_side, '?')}** (Confidence: {conf}%)")
        st.markdown(f"**📍 ความเสี่ยง:** {prediction_data['risk']}")
        st.markdown(f"**🧾 คำแนะนำ:** **{prediction_data['recommendation']}**")
        st.markdown(f"**🧬 Developer View:** {prediction_data['developer_view']}")
    else:
        st.error("❌ เกิดข้อผิดพลาดในการรับผลการทำนายจาก OracleEngine. กรุณาตรวจสอบ 'oracle_engine.py'")
        st.markdown("### 🔮 ทำนายตาถัดไป: — (ไม่สามารถทำนายได้)")
else:
    st.markdown("### 🔮 ทำนายตาถัดไป: — (กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา)")

# --- ส่วนบันทึกผลลัพธ์จริงของตาที่ผ่านมา ---
st.markdown("---")
st.markdown("### 📝 บันทึกผลลัพธ์จริงของตาที่ผ่านมา:")

# เพิ่มเงื่อนไขการตรวจสอบ prediction_data ก่อนใช้งาน
if prediction_data and isinstance(prediction_data, dict) and 'recommendation' in prediction_data:
    if prediction_data['recommendation'] == "Play ✅":
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
    elif prediction_data['recommendation'] == "Avoid ❌":
        st.warning("⚠️ ระบบแนะนำให้ **งดเดิมพัน** ในตานี้. บันทึกผลลัพธ์จริงเพื่ออัปเดตประวัติเท่านั้น")
        col_avoid_p, col_avoid_b, col_avoid_t = st.columns(3)
        with col_avoid_p:
            if st.button(f"บันทึก: ออก 🔵 (P)", key="no_bet_P", use_container_width=True):
                add_to_history('P')
                st.rerun()
        with col_avoid_b:
            if st.button(f"บันทึก: ออก 🔴 (B)", key="no_bet_B", use_container_width=True):
                add_to_history('B')
                st.rerun()
        with col_avoid_t:
            if st.button(f"บันทึก: ออก 🟢 (T)", key="no_bet_T", use_container_width=True):
                add_to_history('T')
                st.rerun()
else: # กรณีที่ยังไม่มี prediction_data ที่สมบูรณ์ (เช่น ประวัติยังไม่ครบ 20 ตา)
    st.info("กรุณาบันทึกผลย้อนหลังให้ครบ 20 ตา เพื่อเริ่มการวิเคราะห์")
    col_init_p, col_init_b, col_init_t = st.columns(3)
    with col_init_p:
        if st.button(f"บันทึก: ออก 🔵 (P)", key="init_P", use_container_width=True):
            add_to_history('P')
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
    st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มีการเดิมพันบันทึกไว้")

# --- แสดงประวัติผลย้อนหลัง ---
st.markdown("---")
st.markdown("### 📜 ประวัติผลย้อนหลัง (ใช้สำหรับการวิเคราะห์ระบบ)")
history_emojis = engine.get_history_emojis()
if history_emojis:
    display_history = []
    for i in range(0, len(history_emojis), 10):
        display_history.append(" ".join(history_emojis[i:i+10]))
    st.markdown("\n".join(display_history))
else:
    st.info("ยังไม่มีข้อมูล")

# --- ปุ่มควบคุมประวัติ (ลบ/รีเซ็ต) ---
col_hist1, col_hist2 = st.columns(2)
with col_hist1:
    if st.button("↩️ ลบล่าสุด", key="delLastHist", use_container_width=True, on_click=remove_last_from_history):
        st.rerun()
with col_hist2:
    if st.button("🧹 รีเซ็ตทั้งหมด", key="resetAllHist", use_container_width=True, on_click=reset_all_history):
        st.rerun()

st.markdown("---")
st.caption("ระบบวิเคราะห์ Oracle Baccarat AI โดยคุณ")
