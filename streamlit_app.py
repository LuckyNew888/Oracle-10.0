
import streamlit as st
import pandas as pd
import time

from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data

st.set_page_config(page_title="ORACLE Baccarat AI v2.0", layout="centered")

# =========================== UI: TITLE =============================
st.markdown("<h2 style='text-align: center; color: gold;'>🔮 ORACLE Baccarat Analyzer v2.0</h2>", unsafe_allow_html=True)

# =========================== SIDEBAR =============================
st.sidebar.header("📋 ตัวเลือกวิเคราะห์")
uploaded_file = st.sidebar.file_uploader("📤 อัปโหลดไฟล์ผลบาคาร่า (.csv)", type="csv")

system_options = ["Martingale", "Fibonacci", "Labouchere"]
current_system = st.sidebar.selectbox("🎯 ระบบเดินเงิน", system_options)
start_money = st.sidebar.number_input("💰 เงินเริ่มต้น", value=1000)
base_bet = st.sidebar.number_input("🎯 หน่วยเดิมพันเริ่มต้น", value=10)

if "money_balance" not in st.session_state:
    st.session_state.money_balance = start_money
if "fibonacci_current_index" not in st.session_state:
    st.session_state.fibonacci_current_index = 0
if "labouchere_current_sequence" not in st.session_state:
    st.session_state.labouchere_current_sequence = [1, 2, 3, 4]
if "labouchere_unit_bet" not in st.session_state:
    st.session_state.labouchere_unit_bet = base_bet
if "bet_log" not in st.session_state:
    st.session_state.bet_log = []

# =========================== MAIN LOGIC =============================
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = df["Result"].tolist()
    oracle = OracleEngine()
    predictions = oracle.predict_all(results[:-1])
    fib_seq = [1, 1, 2, 3, 5, 8, 13, 21]

    for i, pred in enumerate(predictions):
        actual_result = results[i+1]  # next result
        predicted_side = pred["prediction"]
        win_loss = 0
        outcome = "❌ แพ้"

        # ==== เดินเงินตามระบบ ====
        if current_system == "Martingale":
            last_log = st.session_state.bet_log[-1] if st.session_state.bet_log else None
            if last_log and last_log["ผลลัพธ์"] != last_log["ฝั่งที่เลือก"]:
                bet_amt = last_log["เดิมพัน"] * 2
            else:
                bet_amt = base_bet

        elif current_system == "Fibonacci":
            current_idx = st.session_state.fibonacci_current_index
            bet_amt = fib_seq[current_idx]
        elif current_system == "Labouchere":
            seq = st.session_state.labouchere_current_sequence
            if len(seq) >= 2:
                bet_amt = (seq[0] + seq[-1]) * st.session_state.labouchere_unit_bet
            elif len(seq) == 1:
                bet_amt = seq[0] * st.session_state.labouchere_unit_bet
            else:
                bet_amt = base_bet
        else:
            bet_amt = base_bet

        # ===== ประมวลผลผลลัพธ์และอัปเดตเงิน ====
        if predicted_side == actual_result:
            win_loss = bet_amt
            st.session_state.money_balance += bet_amt
            outcome = "✅ ชนะ"
        else:
            win_loss = -bet_amt
            st.session_state.money_balance -= bet_amt

        # ===== อัปเดตระบบเดินเงิน ====
        if current_system == "Fibonacci":
            if predicted_side == actual_result:
                st.session_state.fibonacci_current_index = max(0, st.session_state.fibonacci_current_index - 2)
            else:
                st.session_state.fibonacci_current_index = min(current_idx + 1, len(fib_seq) - 1)

        elif current_system == "Labouchere":
            current_seq = st.session_state.labouchere_current_sequence
            unit_bet = st.session_state.labouchere_unit_bet

            if predicted_side == actual_result:
                if len(current_seq) >= 2:
                    st.session_state.labouchere_current_sequence = current_seq[1:-1]
                elif len(current_seq) == 1:
                    st.session_state.labouchere_current_sequence = []
            else:
                total = current_seq[0] + current_seq[-1] if len(current_seq) >= 2 else current_seq[0]
                st.session_state.labouchere_current_sequence.append(total)

        st.session_state.bet_log.append({
            "รอบ": len(st.session_state.bet_log) + 1,
            "ฝั่งที่เลือก": predicted_side,
            "ผลลัพธ์": actual_result,
            "เดิมพัน": bet_amt,
            "กำไร/ขาดทุน": win_loss,
            "สถานะ": outcome,
            "ยอดเงินคงเหลือ": st.session_state.money_balance
        })

    # =========================== สรุปผล =============================
    st.subheader("📈 ผลลัพธ์การวิเคราะห์")
    bet_df = pd.DataFrame(st.session_state.bet_log)
    st.dataframe(bet_df, use_container_width=True)

    st.success(f"💵 ยอดเงินคงเหลือสุดท้าย: {st.session_state.money_balance} หน่วย")

else:
    st.info("กรุณาอัปโหลดไฟล์ผลลัพธ์บาคาร่า (.csv) เพื่อเริ่มต้นวิเคราะห์")
