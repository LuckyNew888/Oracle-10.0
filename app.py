import streamlit as st
from oracle_core import OracleBrain

st.set_page_config(page_title="🔮 ORACLE v5", layout="centered")
st.title("🔮 ORACLE v5")

# Initialize session state
if "oracle" not in st.session_state:
    st.session_state.oracle = OracleBrain()
if "initial_shown" not in st.session_state:
    st.session_state.initial_shown = False

oracle: OracleBrain = st.session_state.oracle

# --- Function: Convert outcome to emoji
def outcome_to_emoji(outcome):
    return "🔵" if outcome == "P" else "🔴" if outcome == "B" else "⚪"

# --- Display prediction
if st.button("🔮 ทำนายผลลัพธ์ถัดไป"):
    result = oracle.predict_next()
    if result:
        predict, module, confidence, pattern, miss_streak = result
        oracle.last_prediction = predict
        st.session_state.initial_shown = True

# --- Show prediction info
if oracle.last_prediction:
    st.subheader("📍 คำทำนาย:")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h1 style='color:#00BFFF'>{outcome_to_emoji(oracle.last_prediction)} {oracle.last_prediction}</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"🧠 โมดูล: **{module}**")
        st.markdown(f"📊 เค้าไพ่: **{pattern}**")
        st.markdown(f"🔎 ความมั่นใจ: **{confidence}%**")
        st.markdown(f"❌ แพ้ติดกัน: **{miss_streak} ครั้ง**")

# --- Add outcome
cols = st.columns(3)
if cols[0].button("🔵 P"):
    oracle.add_result("P")
if cols[1].button("🔴 B"):
    oracle.add_result("B")
if cols[2].button("⚪ T"):
    oracle.add_result("T")

# --- Control buttons
control_cols = st.columns(3)
if control_cols[0].button("🔄 ลบรายการล่าสุด"):
    oracle.remove_last()
if control_cols[1].button("🧹 เริ่มใหม่ทั้งหมด"):
    oracle.reset()
if control_cols[2].button("📋 แสดงรายการทั้งหมด"):
    st.write("ผลย้อนหลัง:", oracle.result_log)

# --- Big Road Display
st.subheader("🕒 Big Road:")
br_cols = st.columns(20)
row = 0
col = 0
max_rows = 6

for i, outcome in enumerate(oracle.result_log):
    if outcome == "T":
        # Add white number inside previous circle
        continue

    emoji = outcome_to_emoji(outcome)
    label = ""

    # Count Ts before this point
    t_count = 0
    for j in range(i+1, len(oracle.result_log)):
        if oracle.result_log[j] == "T":
            t_count += 1
        else:
            break
    if t_count > 0:
        label = f"{t_count}"

    with br_cols[col]:
        st.markdown(f"<div style='font-size:30px;text-align:center'>{emoji}<sub style='color:white'>{label}</sub></div>", unsafe_allow_html=True)

    row += 1
    if row >= max_rows:
        row = 0
        col += 1

# Auto scroll (visually mimicked by showing last 20 columns)
