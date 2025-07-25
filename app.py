import streamlit as st
import random
from collections import Counter

# --- Configuration ---
MIN_HISTORY_FOR_PREDICTION = 15 # Adjusted from 20 to 15 for 'Enhanced Predict'
MAX_HISTORY_DISPLAY = 50 # Max history to store and display
MAX_HISTORY_FOR_ANALYSIS = 30 # For pattern analysis
PREDICTION_THRESHOLD = 0.55 # Minimum confidence for a prediction
COUNTER_PREDICTION_THRESHOLD = 0.65 # Higher threshold for 'สวน' prediction
DNA_PATTERN_LENGTH = 5 # Length of pattern to look for in DNA analysis
MOMENTUM_THRESHOLD = 0.70 # Threshold for strong momentum
COUNTER_BIAS_STREAK_THRESHOLD = 3 # For counter bias detection

# --- Page Configuration ---
st.set_page_config(
    page_title="ORACLE Final V1.14 (Reliable Counter)",
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

# --- Helper Functions ---

# Function to get outcome emoji
def get_outcome_emoji(outcome):
    return "🟦" if outcome == 'P' else "🟥" if outcome == 'B' else "⚪️"

# Function to get latest history string
def get_latest_history_string(num_results=MAX_HISTORY_FOR_ANALYSIS):
    return "".join([h['main_outcome'] for h in st.session_state.history[-num_results:]])

# --- Prediction Logic ---

# 1. DNA Pattern Analysis
def analyze_dna_pattern(history_str):
    if len(history_str) < DNA_PATTERN_LENGTH:
        return None, 0

    target_pattern = history_str[-DNA_PATTERN_LENGTH:]
    
    # Try finding the pattern and what came after it
    # We look for patterns ending at different points in the history
    # to see what typically follows them.
    
    # Analyze what follows the pattern
    followers = Counter()
    for i in range(len(history_str) - DNA_PATTERN_LENGTH):
        if history_str[i : i + DNA_PATTERN_LENGTH] == target_pattern:
            if (i + DNA_PATTERN_LENGTH) < len(history_str):
                followers[history_str[i + DNA_PATTERN_LENGTH]] += 1
    
    total_followers = sum(followers.values())
    
    if total_followers == 0:
        return None, 0
    
    most_common_follower = followers.most_common(1)
    
    if most_common_follower:
        predicted_outcome = most_common_follower[0][0]
        confidence = most_common_follower[0][1] / total_followers
        return predicted_outcome, confidence
    return None, 0

# 2. Momentum Tracker
def analyze_momentum(history_str):
    if len(history_str) < 5: # Need at least 5 for a short trend
        return None, 0

    # Check recent streaks
    last_outcome = history_str[-1]
    last_streak_length = 0
    for i in reversed(range(len(history_str))):
        if history_str[i] == last_outcome:
            last_streak_length += 1
        else:
            break
            
    if last_streak_length >= 3: # Strong streak
        return last_outcome, min(1.0, 0.5 + (last_streak_length - 3) * 0.1) # Confidence increases with length
    
    # Check for alternating patterns (Ping-pong like)
    if len(history_str) >= 4 and history_str[-4:] in ["PBPB", "BPBP"]:
        # Predict the opposite of the last if it's alternating
        predicted_outcome = 'P' if history_str[-1] == 'B' else 'B'
        return predicted_outcome, 0.65 # Good confidence for clear alternating
    
    return None, 0

# 3. Intuition (Simple Pattern Matching & Counter Bias)
def analyze_intuition(history_str):
    if len(history_str) < 3:
        return None, 0, False # Outcome, Confidence, IsCounter

    last_3 = history_str[-3:]
    last_2 = history_str[-2:]
    
    # Counter Bias Logic (New from V1.14)
    # If there's a strong streak, consider countering it IF it's not a common 'dragon' pattern
    # This is an intuitive counter, not purely statistical.
    if len(history_str) >= COUNTER_BIAS_STREAK_THRESHOLD:
        last_outcome = history_str[-1]
        streak_count = 0
        for i in reversed(range(len(history_str))):
            if history_str[i] == last_outcome:
                streak_count += 1
            else:
                break
        
        if streak_count >= COUNTER_BIAS_STREAK_THRESHOLD:
            # Check if this streak has been consistently followed (DNA-like check for counter)
            # Find instances of this exact streak
            streak_pattern = history_str[len(history_str) - streak_count:]
            
            # Count how often this streak continues vs. breaks
            continue_count = 0
            break_count = 0
            for i in range(len(history_str) - streak_count):
                if history_str[i : i + streak_count] == streak_pattern:
                    if (i + streak_count) < len(history_str):
                        if history_str[i + streak_count] == last_outcome:
                            continue_count += 1
                        else:
                            break_count += 1
            
            total_instances = continue_count + break_count
            if total_instances > 0:
                if break_count / total_instances >= 0.5: # If it breaks more than it continues
                    return ('P' if last_outcome == 'B' else 'B'), COUNTER_PREDICTION_THRESHOLD, True # Predict counter with high confidence
                elif continue_count / total_instances == 0 and total_instances >= 2: # If it never continued
                    return ('P' if last_outcome == 'B' else 'B'), COUNTER_PREDICTION_THRESHOLD, True

    # Simple Intuition (from previous versions, less prominent now)
    if last_3 == "BBP" or last_3 == "PBB": # Two-cut pattern
        return ('P' if last_3[-1] == 'B' else 'B'), 0.6, False
    if last_3 == "PPB" or last_3 == "BPP": # Two-cut pattern
        return ('B' if last_3[-1] == 'P' else 'P'), 0.6, False
    
    # Simple Ping-Pong
    if last_2 == "BP" or last_2 == "PB":
        return ('B' if last_2[-1] == 'P' else 'P'), 0.55, False # Predict opposite
        
    return None, 0, False # No intuition pattern found

def predict_outcome():
    history_str = get_latest_history_string()
    
    if len(history_str) < MIN_HISTORY_FOR_PREDICTION:
        return {"prediction": "ไม่เพียงพอ", "confidence": 0, "predicted_by": [], "is_counter": False}

    predictions = []
    
    # 1. DNA Analysis
    dna_pred, dna_conf = analyze_dna_pattern(history_str)
    if dna_pred:
        predictions.append({"outcome": dna_pred, "confidence": dna_conf, "source": "DNA"})

    # 2. Momentum Analysis
    momentum_pred, momentum_conf = analyze_momentum(history_str)
    if momentum_pred:
        predictions.append({"outcome": momentum_pred, "confidence": momentum_conf, "source": "Momentum"})

    # 3. Intuition (incl. Counter Bias)
    intuition_pred, intuition_conf, is_counter_intuition = analyze_intuition(history_str)
    if intuition_pred:
        predictions.append({"outcome": intuition_pred, "confidence": intuition_conf, "source": "Intuition", "is_counter": is_counter_intuition})
    
    # Combine predictions
    if not predictions:
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    # Prioritize Counter if very confident and from Intuition
    for p in predictions:
        if p.get('is_counter', False) and p['confidence'] >= COUNTER_PREDICTION_THRESHOLD:
            return {"prediction": p['outcome'], 
                    "confidence": p['confidence'], 
                    "predicted_by": [p['source']], 
                    "is_counter": True}

    # Otherwise, find the strongest prediction (average confidence for same outcome)
    outcome_scores = Counter()
    outcome_sources = {} # To keep track of sources for each outcome
    is_any_counter = False

    for p in predictions:
        outcome_scores[p['outcome']] += p['confidence']
        if p['outcome'] not in outcome_sources:
            outcome_sources[p['outcome']] = []
        outcome_sources[p['outcome']].append(p['source'])
        if p.get('is_counter', False):
            is_any_counter = True

    if not outcome_scores:
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    # Sort by highest score first
    sorted_outcomes = sorted(outcome_scores.items(), key=lambda item: item[1], reverse=True)
    
    best_outcome = sorted_outcomes[0][0]
    best_confidence = sorted_outcomes[0][1] / len(outcome_sources[best_outcome]) # Average confidence
    
    # Final check against general prediction threshold
    if best_confidence >= PREDICTION_THRESHOLD:
        return {"prediction": best_outcome, 
                "confidence": best_confidence, 
                "predicted_by": outcome_sources[best_outcome],
                "is_counter": is_any_counter}
    else:
        return {"prediction": "ไม่ชัดเจน", "confidence": best_confidence, "predicted_by": outcome_sources[best_outcome], "is_counter": is_any_counter}


# --- UI Functions ---

# Function to record outcome
def record_outcome(outcome):
    if st.session_state.last_prediction_data:
        predicted_outcome = st.session_state.last_prediction_data['prediction']
        confidence = st.session_state.last_prediction_data['confidence']
        is_counter = st.session_state.last_prediction_data['is_counter']

        if predicted_outcome != "ไม่เพียงพอ" and predicted_outcome != "ไม่พบรูปแบบ" and predicted_outcome != "ไม่ชัดเจน":
            st.session_state.total_predictions += 1
            if predicted_outcome == outcome:
                st.session_state.correct_predictions += 1
                if is_counter:
                    st.session_state.counter_streak_count += 1
                else:
                    st.session_state.counter_streak_count = 0 # Reset if not counter or counter failed
            else:
                st.session_state.counter_streak_count = 0 # Reset on wrong prediction

            # Update prediction win/loss counts per outcome type (P/B)
            st.session_state.prediction_counts[predicted_outcome] = st.session_state.prediction_counts.get(predicted_outcome, 0) + 1
            if predicted_outcome == outcome:
                st.session_state.prediction_wins[predicted_outcome] = st.session_state.prediction_wins.get(predicted_outcome, 0) + 1

            # Update counter stats if it was a counter prediction
            if is_counter:
                st.session_state.total_counter_predictions += 1
                if predicted_outcome == outcome:
                    st.session_state.correct_counter_predictions += 1

    st.session_state.history.append({'main_outcome': outcome, 'timestamp': st.session_state.get('current_timestamp', 'N/A')})
    # Keep history within MAX_HISTORY_DISPLAY limit
    if len(st.session_state.history) > MAX_HISTORY_DISPLAY:
        st.session_state.history = st.session_state.history[-MAX_HISTORY_DISPLAY:]
    
    # Clear last prediction data after recording outcome
    st.session_state.last_prediction_data = None


def delete_last_outcome():
    if st.session_state.history:
        # Revert prediction stats if the deleted outcome was the one that followed a prediction
        if st.session_state.last_prediction_data:
            # This logic is tricky if user deletes multiple outcomes.
            # For simplicity, we only revert if the *immediately* previous action was a prediction and recording.
            # A more robust system would timestamp predictions and outcomes more carefully.
            
            # Reset prediction data if the deleted outcome was the last one recorded and it affected stats
            if st.session_state.total_predictions > 0 and st.session_state.last_prediction_data['prediction'] != "ไม่เพียงพอ":
                # Assuming the last recorded outcome was the one related to the last prediction
                last_recorded_outcome_info = st.session_state.history[-1]
                last_predicted_outcome = st.session_state.last_prediction_data['prediction']
                last_is_counter = st.session_state.last_prediction_data['is_counter']

                st.session_state.total_predictions -= 1
                if last_predicted_outcome == last_recorded_outcome_info['main_outcome']:
                    st.session_state.correct_predictions -= 1
                    # Revert counter streak only if it was incremented by this exact correct counter prediction
                    if last_is_counter:
                        st.session_state.counter_streak_count = max(0, st.session_state.counter_streak_count - 1)
                else:
                    # If it was a wrong prediction, and counter streak was reset, we can't easily undo its effect.
                    # For simplicity, if it was wrong, the streak was already 0.
                    pass 

                st.session_state.prediction_counts[last_predicted_outcome] = st.session_state.prediction_counts.get(last_predicted_outcome, 1) - 1
                if last_predicted_outcome == last_recorded_outcome_info['main_outcome']:
                    st.session_state.prediction_wins[last_predicted_outcome] = st.session_state.prediction_wins.get(last_predicted_outcome, 0) - 1

                if last_is_counter:
                    st.session_state.total_counter_predictions -= 1
                    if last_predicted_outcome == last_recorded_outcome_info['main_outcome']:
                        st.session_state.correct_counter_predictions -= 1
        
        st.session_state.history.pop()
        # After deleting, we need to re-run prediction to update the UI
        st.session_state.last_prediction_data = None # Clear this to force re-prediction on next run

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
    
    # --- START OF MODIFIED SECTION FOR HISTORY DISPLAY ---
    # Removed the wrapping logic to display as a single long line as in v1.13
    st.markdown(f"<p style='font-size: 1.5em;'>{history_display}</p>", unsafe_allow_html=True)
    # --- END OF MODIFIED SECTION ---

    st.markdown(f"**จำนวนตาที่บันทึก: {len(st.session_state.history)}**")
else:
    st.write("ยังไม่มีประวัติ กรุณาเริ่มบันทึกผล")

# Prediction Display
st.subheader("🧠 ผลการวิเคราะห์และทำนาย")

current_prediction = predict_outcome()
st.session_state.last_prediction_data = current_prediction # Store for later use

pred_emoji = get_outcome_emoji(current_prediction['prediction']) if current_prediction['prediction'] in ['P', 'B', 'T'] else "❓"
confidence_percent = f"{current_prediction['confidence']*100:.1f}%"

prediction_text = f"**ผลวิเคราะห์: {pred_emoji} {current_prediction['prediction']}** (ความมั่นใจ: {confidence_percent})"

if current_prediction['predicted_by']:
    predicted_by_str = ", ".join(current_prediction['predicted_by'])
    prediction_text += f"\n*ทำนายโดย: {predicted_by_str}*"
    if current_prediction.get('is_counter', False):
        prediction_text += " (สวน)"

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
    st.write(get_latest_history_string())

    st.write("---")
    st.write("**ผลลัพธ์จากการวิเคราะห์แต่ละส่วน (Debug):**")
    debug_history_str = get_latest_history_string()
    
    st.write(f"DNA Analysis: {analyze_dna_pattern(debug_history_str)}")
    st.write(f"Momentum Analysis: {analyze_momentum(debug_history_str)}")
    st.write(f"Intuition Analysis: {analyze_intuition(debug_history_str)}")

    st.write("---")
    st.write("**Predicted by (Debugging the KeyError location):**")
    if st.session_state.last_prediction_data and 'predicted_by' in st.session_state.last_prediction_data:
        st.write(f"st.session_state.last_prediction_data['predicted_by']: {st.session_state.last_prediction_data['predicted_by']}")
    else:
        st.write("st.session_state.last_prediction_data หรือ 'predicted_by' key ไม่มีอยู่")
