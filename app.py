import streamlit as st
# Import everything needed from oracle_engine.py
from oracle_engine import (
    MIN_HISTORY_FOR_PREDICTION, MAX_HISTORY_FOR_ANALYSIS,
    PREDICTION_THRESHOLD, COUNTER_PREDICTION_THRESHOLD,
    get_outcome_emoji, get_latest_history_string, # These are also helper functions now in oracle_engine
    analyze_dna_pattern, analyze_momentum, analyze_intuition, predict_outcome
)

# --- Configuration for app.py (UI specific) ---
MAX_HISTORY_DISPLAY = 50 # Max history to store and display in UI


# --- Page Configuration ---
st.set_page_config(
    page_title="🔮 ORACLE Final V1.14 (Reliable Counter)", # Title updated for V1.14 with counter focus
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Session State Initialization ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'total_predictions' not in st.session_state:
    st.session_state.total_predictions = 0
if 'correct_predictions' not in st.session_state:
    st.session_state.correct_predictions = 0
if 'correct_counter_predictions' not in st.session_state:
    st.session_state.correct_counter_predictions = 0
if 'total_counter_predictions' not in st.session_state:
    st.session_state.total_counter_predictions = 0
if 'last_prediction_data' not in st.session_state:
    st.session_state.last_prediction_data = None # Stores data of the last prediction made
if 'prediction_counts' not in st.session_state:
    st.session_state.prediction_counts = {} # {'P': count, 'B': count}
if 'prediction_wins' not in st.session_state:
    st.session_state.prediction_wins = {} # {'P': wins, 'B': wins}
if 'counter_streak_count' not in st.session_state:
    st.session_state.counter_streak_count = 0 # Streak of wins when countering

# --- UI Functions ---

def record_outcome(outcome):
    if st.session_state.last_prediction_data:
        predicted_outcome = st.session_state.last_prediction_data['prediction']
        is_counter = st.session_state.last_prediction_data['is_counter']

        if predicted_outcome not in ["ไม่เพียงพอ", "ไม่พบรูปแบบ", "ไม่ชัดเจน"]:
            st.session_state.total_predictions += 1
            if predicted_outcome == outcome:
                st.session_state.correct_predictions += 1
                if is_counter:
                    st.session_state.counter_streak_count += 1
                else:
                    st.session_state.counter_streak_count = 0
            else:
                st.session_state.counter_streak_count = 0

            st.session_state.prediction_counts[predicted_outcome] = st.session_state.prediction_counts.get(predicted_outcome, 0) + 1
            if predicted_outcome == outcome:
                st.session_state.prediction_wins[predicted_outcome] = st.session_state.prediction_wins.get(predicted_outcome, 0) + 1

            if is_counter:
                st.session_state.total_counter_predictions += 1
                if predicted_outcome == outcome:
                    st.session_state.correct_counter_predictions += 1

    st.session_state.history.append({'main_outcome': outcome, 'timestamp': st.session_state.get('current_timestamp', 'N/A')})
    if len(st.session_state.history) > MAX_HISTORY_DISPLAY:
        st.session_state.history = st.session_state.history[-MAX_HISTORY_DISPLAY:]
    
    st.session_state.last_prediction_data = None


def delete_last_outcome():
    if st.session_state.history:
        if st.session_state.last_prediction_data:
            predicted_outcome_for_deleted_hand = st.session_state.last_prediction_data['prediction']
            is_counter_for_deleted_hand = st.session_state.last_prediction_data['is_counter']
            
            if predicted_outcome_for_deleted_hand not in ["ไม่เพียงพอ", "ไม่พบรูปแบบ", "ไม่ชัดเจน"]:
                deleted_actual_outcome = st.session_state.history[-1]['main_outcome']

                st.session_state.total_predictions = max(0, st.session_state.total_predictions - 1)
                
                if predicted_outcome_for_deleted_hand == deleted_actual_outcome:
                    st.session_state.correct_predictions = max(0, st.session_state.correct_predictions - 1)
                    if is_counter_for_deleted_hand:
                        st.session_state.counter_streak_count = max(0, st.session_state.counter_streak_count - 1)
                else:
                    pass 

                st.session_state.prediction_counts[predicted_outcome_for_deleted_hand] = \
                    max(0, st.session_state.prediction_counts.get(predicted_outcome_for_deleted_hand, 0) - 1)
                if predicted_outcome_for_deleted_hand == deleted_actual_outcome:
                    st.session_state.prediction_wins[predicted_outcome_for_deleted_hand] = \
                        max(0, st.session_state.prediction_wins.get(predicted_outcome_for_deleted_hand, 0) - 1)

                if is_counter_for_deleted_hand:
                    st.session_state.total_counter_predictions = max(0, st.session_state.total_counter_predictions - 1)
                    if predicted_outcome_for_deleted_hand == deleted_actual_outcome:
                        st.session_state.correct_counter_predictions = max(0, st.session_state.correct_counter_predictions - 1)
        
        st.session_state.history.pop()
        st.session_state.last_prediction_data = None


def reset_system():
    st.session_state.history = []
    st.session_state.total_predictions = 0
    st.session_state.correct_predictions = 0
    st.session_state.correct_counter_predictions = 0
    st.session_state.total_counter_predictions = 0
    st.session_state.last_prediction_data = None
    st.session_state.prediction_counts = {}
    st.session_state.prediction_wins = {}
    st.session_state.counter_streak_count = 0
    st.rerun()

# --- Main App Layout ---
st.title("🔮 ORACLE Final V1.14 (Reliable Counter)")
st.markdown("ระบบทำนายแนวโน้มบาคาร่า (สำหรับบันทึกผลด้วยตนเอง)")

# History Display
st.subheader("📋 ประวัติผลลัพธ์")
if st.session_state.history:
    history_emojis = [get_outcome_emoji(h['main_outcome']) for h in st.session_state.history]
    history_display = "".join(history_emojis)
    
    # This maintains the V1.13 long string display
    st.markdown(f"<p style='font-size: 1.5em;'>{history_display}</p>", unsafe_allow_html=True)
    
    st.markdown(f"**จำนวนตาที่บันทึก: {len(st.session_state.history)}**")
else:
    st.write("ยังไม่มีประวัติ กรุณาเริ่มบันทึกผล")

# Prediction Display
st.subheader("🧠 ผลการวิเคราะห์และทำนาย")

# Call predict_outcome from oracle_engine, passing the history list
current_prediction = predict_outcome(st.session_state.history)
st.session_state.last_prediction_data = current_prediction # Store for later use when outcome is recorded

pred_emoji = get_outcome_emoji(current_prediction['prediction']) if current_prediction['prediction'] in ['P', 'B', 'T'] else "❓"
confidence_percent = f"{current_prediction['confidence']*100:.1f}%"

prediction_text = f"**ผลวิเคราะห์: {pred_emoji} {current_prediction['prediction']}** (ความมั่นใจ: {confidence_percent})"

# Display prediction source and counter status if available
if current_prediction.get('predicted_by'):
    predicted_by_str = ", ".join(current_prediction['predicted_by'])
    prediction_text += f"\n*ทำนายโดย: {predicted_by_str}*"
    if current_prediction.get('is_counter', False):
        prediction_text += " (สวน)"

# Display appropriate message based on prediction status
if len(st.session_state.history) < MIN_HISTORY_FOR_PREDICTION:
    st.warning(f"บันทึกประวัติอย่างน้อย {MIN_HISTORY_FOR_PREDICTION} ตา เพื่อเริ่มการทำนาย (ปัจจุบัน: {len(st.session_state.history)} ตา)")
elif current_prediction['prediction'] == "ไม่พบรูปแบบ":
    st.info("ระบบยังไม่พบรูปแบบที่ชัดเจนในการทำนาย")
elif current_prediction['prediction'] == "ไม่ชัดเจน":
    st.warning(f"รูปแบบยังไม่ชัดเจนพอ (ความมั่นใจ {confidence_percent} < {PREDICTION_THRESHOLD*100:.0f}%)")
else:
    if current_prediction.get('is_counter', False):
        st.success(prediction_text)
    else:
        st.info(prediction_text)

# Record Outcome Buttons
st.subheader("➕ บันทึกผลลัพธ์")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.button("🟦 P", on_click=record_outcome, args=('P',))
with col2:
    st.button("🟥 B", on_click=record_outcome, args=('B',))
with col3:
    st.button("⚪️ T", on_click=record_outcome, args=('T',))
with col4:
    st.button("❌ ลบล่าสุด", on_click=delete_last_outcome)

st.markdown("---")

# Performance Statistics
st.subheader("📊 สถิติประสิทธิภาพ (รวม)")

total_preds_display = st.session_state.total_predictions
correct_preds_display = st.session_state.correct_predictions
accuracy = (correct_preds_display / total_preds_display * 100) if total_preds_display > 0 else 0

st.write(f"**🎯 ความแม่นยำ (รวม): {accuracy:.1f}%** ({correct_preds_display}/{total_preds_display} ครั้ง)")

if st.session_state.total_counter_predictions > 0:
    counter_accuracy = (st.session_state.correct_counter_predictions / st.session_state.total_counter_predictions * 100)
    st.write(f"**🎯 ความแม่นยำ (สวน): {counter_accuracy:.1f}%** ({st.session_state.correct_counter_predictions}/{st.session_state.total_counter_predictions} ครั้ง)")
    if st.session_state.correct_counter_predictions > 0 and st.session_state.total_counter_predictions > 0:
        st.write(f"🔥 สวนสูตรชนะต่อเนื่อง: **{st.session_state.counter_streak_count}** ครั้ง")


st.subheader("📈 สถิติแยกตามผลลัพธ์ที่ทำนาย")
if st.session_state.prediction_counts:
    for outcome, count in st.session_state.prediction_counts.items():
        wins = st.session_state.prediction_wins.get(outcome, 0)
        outcome_accuracy = (wins / count * 100) if count > 0 else 0
        st.write(f"- ทำนาย {get_outcome_emoji(outcome)} {outcome}: **{outcome_accuracy:.1f}%** ({wins}/{count} ครั้ง)")
else:
    st.write("ยังไม่มีสถิติการทำนาย")

st.markdown("---")

st.button("🔄 รีเซ็ตระบบทั้งหมด", on_click=reset_system)

# Developer View (Expandable Section)
with st.expander("🧬 มุมมองนักพัฒนา"):
    st.write("---")
    st.write("**สถานะ Session State:**")
    st.json(st.session_state.to_dict())
    
    st.write("---")
    st.write("**ประวัติ (สำหรับวิเคราะห์ DNA):**")
    st.write(get_latest_history_string(st.session_state.history))

    st.write("---")
    st.write("**ผลลัพธ์จากการวิเคราะห์แต่ละส่วน (Debug):**")
    debug_history_str = get_latest_history_string(st.session_state.history)
    
    st.write(f"DNA Analysis: {analyze_dna_pattern(debug_history_str)}")
    st.write(f"Momentum Analysis: {analyze_momentum(debug_history_str)}")
    st.write(f"Intuition Analysis: {analyze_intuition(debug_history_str)}")

    st.write("---")
    st.write("**Predicted by (Debugging the KeyError location):**")
    if st.session_state.last_prediction_data and st.session_state.last_prediction_data.get('predicted_by') is not None:
        st.write(f"st.session_state.last_prediction_data['predicted_by']: {st.session_state.last_prediction_data.get('predicted_by')}")
    else:
        st.write("st.session_state.last_prediction_data หรือ 'predicted_by' key ไม่มีอยู่")
