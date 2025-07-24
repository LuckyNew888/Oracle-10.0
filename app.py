import streamlit as st
import asyncio 
import time
from oracle_engine import OracleEngine # Ensure oracle_engine.py is in the same directory

# Set Streamlit page configuration
st.set_page_config(page_title=f"ORACLE {OracleEngine.VERSION} Predictor", layout="centered")

# Custom CSS for centered gold title, reduced spacing, and prediction text size
st.markdown(f"""
<style>
/* Font import from Google Fonts - This might be blocked by CSP in some environments */
/* Attempt to use Inter font if available on system */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap');

.center-gold-title {{
    text-align: center;
    color: gold;
    font-size: 3.5em; /* Adjust font size as needed */
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 0.5rem; /* Reduced space below title */
    padding-bottom: 0px;
    /* Prioritize system fonts like Inter, Segoe UI, Roboto, Arial.
       If Inter from Google Fonts is blocked, system fonts will be used. */
    font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}}
h3 {{
    margin-top: 0.5rem; /* Reduced space above h3 */
    margin-bottom: 0.5rem; /* Reduced space below h3 */
}}
.stMarkdown, .stText, .stInfo, .stWarning, .stSuccess {{
    margin-top: 0.2rem; /* Reduced space above various text elements */
    margin-bottom: 0.2rem; /* Reduced space below various text elements */
}}
.stButton>button {{
    margin-top: 0.2rem; /* Reduced space around buttons */
    margin-bottom: 0.2rem;
    line-height: 1.2; /* Adjust line height for button text if needed */
}}

/* Prediction text will now use h1 tag for main sizing */
.prediction-h1 {{
    text-align: center; /* Center the prediction text */
    font-size: 2.5em; /* Make it even larger for clear visibility */
    margin-top: 0.2rem;
    margin-bottom: 0.2rem;
}}

/* Reduce padding around columns to make buttons closer */
div[data-testid="stColumns"] > div {{
    padding-left: 0.2rem;
    padding-right: 0.2rem;
}}
/* Ensure the history display also has less padding */
.stMarkdown p {{ 
    padding: 0px;
    margin: 0px;
}}
</style>
""", unsafe_allow_html=True)

# Main title of the app, now showing version
st.markdown(f'<h1 class="center-gold-title">🔮 ORACLE {OracleEngine.VERSION}</h1>', unsafe_allow_html=True)

# --- State Management for OracleEngine ---
# Initialize OracleEngine only once
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
# Initialize history
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []
# Initialize losing streak counter for the system's predictions
if 'losing_streak_prediction' not in st.session_state:
    st.session_state.losing_streak_prediction = 0

# Retrieve the OracleEngine instance from session_state
oracle = st.session_state.oracle_engine

# --- Prediction Display Section ---
st.markdown("<h3>ผลวิเคราะห์:</h3>", unsafe_allow_html=True) # Shortened title

# Check if enough history is available for analysis
if len(st.session_state.oracle_history) >= 20: 
    # Pass the full history to the engine for prediction
    # Get the full result object including confidence for display
    result = oracle.predict_next(st.session_state.oracle_history)

    # Prepare prediction text with emojis and style
    prediction_text = ""
    if result['prediction'] == 'P':
        prediction_text = f"🔵 P"
    elif result['prediction'] == 'B':
        prediction_text = f"🔴 B"
    elif result['prediction'] == '⚠️':
        prediction_text = f"⚠️ งดเดิมพัน"
    else:
        prediction_text = result['prediction'] # Fallback for '?'

    # Display prediction using h1 tag for large size
    st.markdown(f'<h1 class="prediction-h1">{prediction_text}</h1>', unsafe_allow_html=True)
    
    # Display Accuracy, Risk, Recommendation
    st.markdown(f"**🎯 Accuracy:** {result['accuracy']}")
    st.markdown(f"**📍 Risk:** {result['risk']}")
    st.markdown(f"**🧾 Recommendation:** {result['recommendation']}")
    
    # Display the system's losing streak
    if st.session_state.losing_streak_prediction > 0:
        st.warning(f"**❌ แพ้ติดกัน:** {st.session_state.losing_streak_prediction} ครั้ง")
    else:
        st.success(f"**✅ แพ้ติดกัน:** 0 ครั้ง")
else:
    # Message when not enough data for analysis
    st.info(f"🔮 ผลการทำนาย กรุณาใส่ผลย้อนหลังอย่างน้อย 20 ตา เพื่อเริ่มต้นการวิเคราะห์ (ปัจจุบันมี {len(st.session_state.oracle_history)} ตา)")

# --- History Display Section ---
st.markdown("<h3>📋 ประวัติผลลัพธ์</h3>", unsafe_allow_html=True)
if st.session_state.oracle_history:
    emoji_history = {'P': '🟦', 'B': '🟥', 'T': '⚪️'}
    # Display history as a single string of emojis for compactness
    st.write(' '.join(emoji_history.get(item['main_outcome'], '') for item in st.session_state.oracle_history))
else:
    st.info("ยังไม่มีผลลัพธ์ในประวัติ")

# --- Record Outcome Buttons Section ---
st.markdown("<h3>➕ บันทึกผลลัพธ์</h3>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

# Function to handle adding a new result and updating learning/streak
def add_new_result(outcome):
    # Retrieve the state of the engine *before* adding the new outcome
    # to compare against the actual outcome for learning and streak calculation
    if len(st.session_state.oracle_history) >= 20: 
        # Get the prediction result for the *current state* (before this new hand is added)
        # This is needed to get the prediction and associated patterns/momentum for learning
        prediction_for_learning = oracle.predict_next(st.session_state.oracle_history, is_backtest=False) # is_backtest=False for main app flow

        # Update losing streak based on this prediction and the actual outcome
        if prediction_for_learning['prediction'] not in ['?', '⚠️']: # If system made a valid prediction
            if outcome == 'T': # Tie, losing streak does not change
                pass
            elif prediction_for_learning['prediction'] == outcome: # Correct prediction
                st.session_state.losing_streak_prediction = 0
            else: # Incorrect prediction
                st.session_state.losing_streak_prediction += 1
    
    st.session_state.oracle_history.append({'main_outcome': outcome}) # Add the actual outcome to history
    oracle.update_learning_state(outcome) # Update engine's internal learning state with the actual outcome
    st.rerun() # Rerun the app to update UI

with col1:
    if st.button("🟦 P", use_container_width=True, key="add_p"):
        add_new_result('P')
with col2:
    if st.button("🟥 B", use_container_width=True, key="add_b"):
        add_new_result('B')
with col3:
    if st.button("⚪️ T", use_container_width=True, key="add_t"):
        add_new_result('T')
with col4:
    if st.button("❌ ลบล่าสุด", use_container_width=True, key="remove_last"):
        if st.session_state.oracle_history:
            st.session_state.oracle_history.pop() # Remove last outcome from history
            
            # When removing an item, we must re-initialize the engine
            # and replay the remaining history to correctly rebuild its learning state.
            st.session_state.oracle_engine = OracleEngine() # Create a fresh engine instance
            st.session_state.losing_streak_prediction = 0 # Reset streak, it will be recalculated
            
            # Replay history to rebuild the engine's state and recalculate losing streak
            for i in range(len(st.session_state.oracle_history)):
                current_sub_history = st.session_state.oracle_history[:i+1]
                actual_outcome_for_replay = current_sub_history[-1]['main_outcome']

                # Predict for this sub-history point if enough data
                if len(current_sub_history) >= 20:
                    # Get the prediction context that would have been formed *before* this actual_outcome
                    # This is tricky in replay. We need to simulate predict_next to get the context.
                    # Temporarily store original context
                    original_last_prediction_context = st.session_state.oracle_engine.last_prediction_context 
                    
                    # Simulate predict_next for this point in history to get the context for learning
                    replay_prediction_result = st.session_state.oracle_engine.predict_next(current_sub_history, is_backtest=False) # Not truly backtest for single step
                    
                    # Manually set last_prediction_context for the update_learning_state call
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': replay_prediction_result['prediction'],
                        # Extract patterns/momentum/intuition from developer_view string - this is still brittle
                        'patterns': [p.strip() for p in replay_prediction_result['developer_view'].split('DNA Patterns: ')[1].split(';')[0].split(',') if p.strip() != 'None'],
                        'momentum': [m.strip() for m in replay_prediction_result['developer_view'].split('Momentum: ')[1].split(';')[0].split(',') if m.strip() != 'None'],
                        'intuition_applied': 'Intuition' in replay_prediction_result['developer_view'],
                        'predicted_by': replay_prediction_result['developer_view'].split('Predicted by: ')[1].split(';')[0].strip(),
                        'dominant_pattern_id_at_prediction': replay_prediction_result['developer_view'].split('Predicted by: ')[1].split(';')[0].strip() if 'Predicted by: ' in replay_prediction_result['developer_view'] else None # Simplified extraction
                    }

                    # Re-calculate losing streak for replay
                    if st.session_state.oracle_engine.last_prediction_context['prediction'] not in ['?', '⚠️']:
                        if actual_outcome_for_replay == 'T':
                            pass
                        elif st.session_state.oracle_engine.last_prediction_context['prediction'] == actual_outcome_for_replay:
                            st.session_state.losing_streak_prediction = 0
                        else:
                            st.session_state.losing_streak_prediction += 1
                    
                    # Update learning state after each hand in replay
                    st.session_state.oracle_engine.update_learning_state(actual_outcome_for_replay)

                    # Restore original context for the main app loop
                    st.session_state.oracle_engine.last_prediction_context = original_last_prediction_context
                else:
                    # If not enough data, reset learning context for this point
                    st.session_state.oracle_engine.last_prediction_context = {
                        'prediction': '?', 'patterns': [], 'momentum': [], 'intuition_applied': False, 'predicted_by': None, 'dominant_pattern_id_at_prediction': None
                    }
                    st.session_state.oracle_engine.update_learning_state(actual_outcome_for_replay) # Call update_learning_state even if no prediction made to clear context
            st.rerun()

# --- Reset All Button ---
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear() # Clear all history
    st.session_state.oracle_engine = OracleEngine() # Create a fresh OracleEngine instance to reset all its states
    st.session_state.losing_streak_prediction = 0 # Reset losing streak
    st.rerun()

# --- Developer View (Moved to bottom and in an expander) ---
# Only show if enough history is present
if len(st.session_state.oracle_history) >= 20: 
    # Recalculate prediction context just to get the full developer_view string for display
    current_prediction_info = oracle.predict_next(st.session_state.oracle_history)
    with st.expander("🧬 Developer View: คลิกเพื่อดูรายละเอียด"):
        st.code(current_prediction_info['developer_view'], language='text')

