import streamlit as st
import asyncio 
import time
from oracle_engine import OracleEngine # Ensure oracle_engine.py is in the same directory

# Set Streamlit page configuration
st.set_page_config(page_title=f"ORACLE Predictor", layout="centered") 

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

# Custom CSS for centered gold title, reduced spacing, and prediction text size
st.markdown(f"""
<style>
/* Font import from Google Fonts - This might be blocked by CSP in some environments */
/* Attempt to use Orbitron font for ORACLE, Inter for general text */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@700;900&display=swap');

/* Ensure the main container has no unnecessary padding */
.stApp {{
    padding-top: 1rem; /* Adjust as needed to pull content up */
}}

.center-gold-title {{
    text-align: center;
    color: gold; /* Explicitly set gold color */
    font-size: 3.5em; /* Main ORACLE text size */
    font-weight: 900; /* Make it extra bold for emphasis */
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    margin-bottom: 0.2rem; /* Reduced space below title */
    padding-bottom: 0px;
    font-family: 'Orbitron', 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; /* Orbitron for ORACLE */
}}
.version-text {{
    font-size: 0.5em; /* Smaller font size for version */
    font-weight: normal;
    color: #CCCCCC; /* Lighter color for less emphasis */
    vertical-align: super; /* Slightly raise it */
    margin-left: 0.2em; /* Space from ORACLE text */
    font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; /* Standard font for version */
}}
h3 {{
    margin-top: 0.5rem; /* Reduced space above h3 */
    margin-bottom: 0.5rem; /* Reduced space below h3 */
}}
.stMarkdown, .stText, .stInfo, .stWarning, .stSuccess {{
    margin-top: 0.2rem; /* Reduced space above various text elements */
    margin-bottom: 0.2rem; /* Reduced space below various text elements */
    font-family: 'Inter', sans-serif; /* General text font */
}}
.stButton>button {{
    margin-top: 0.2rem; /* Reduced space around buttons */
    margin-bottom: 0.2rem;
    line-height: 1.2; /* Adjust line height for button text if needed */
    font-family: 'Inter', sans-serif; /* Button text font */
}}

/* Prediction text will now use h1 tag for main sizing */
.prediction-h1 {{
    text-align: center; /* Center the prediction text */
    font-size: 2.5em; /* Make it even larger for clear visibility */
    margin-top: 0.2rem;
    margin-bottom: 0.2rem;
    font-family: 'Inter', sans-serif; /* Prediction text font */
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

# Main title of the app, now showing version with smaller text
st.markdown(f'<h1 class="center-gold-title">🔮 ORACLE <span class="version-text">{oracle.VERSION}</span></h1>', unsafe_allow_html=True)

# --- Prediction Display Section ---
# Determine prediction mode for display
current_prediction_mode = None
if len(st.session_state.oracle_history) >= 15:
    # Need to get prediction result to determine mode
    temp_result = oracle.predict_next(st.session_state.oracle_history, is_backtest=False)
    current_prediction_mode = temp_result['prediction_mode']

mode_text = ""
if current_prediction_mode == 'ตาม':
    mode_text = "ผลวิเคราะห์: ⏮️ ตาม"
elif current_prediction_mode == 'สวน':
    mode_text = "ผลวิเคราะห์: ⏭️ สวน"
elif current_prediction_mode == '⚠️': # If confidence too low to even counter
    mode_text = "ผลวิเคราะห์: ⚠️ งดเดิมพัน"
else: # Not enough data
    mode_text = "ผลวิเคราะห์:"

st.markdown(f"<h3>{mode_text}</h3>", unsafe_allow_html=True)


# Check if enough history is available for analysis
if len(st.session_state.oracle_history) >= 15: # Data threshold for prediction
    # Pass the full history to the engine for prediction
    result = oracle.predict_next(st.session_state.oracle_history)

    # Prepare prediction text with emojis and style
    prediction_text = ""
    if result['prediction'] == 'P':
        prediction_text = f"🔵 P"
    elif result['prediction'] == 'B':
        prediction_text = f"🔴 B"
    elif result['prediction'] == '⚠️':
        prediction_text = f"⚠️" # Just the warning sign, text is in mode_text
    else:
        prediction_text = result['prediction'] # Fallback for '?'

    # Display prediction using h1 tag for large size
    st.markdown(f'<h1 class="prediction-h1">{prediction_text}</h1>', unsafe_allow_html=True)
    
    # NEW: Display ตามสูตรชนะ / สวนสูตรชนะ
    st.markdown(f"📈 **ตามสูตรชนะ** : {oracle.tam_sutr_wins} ครั้ง")
    st.markdown(f"📉 **สวนสูตรชนะ** : {oracle.suan_sutr_wins} ครั้ง")

    # Display Accuracy, Risk, Recommendation (Risk/Recommendation hidden in UI, still returned by engine for dev view)
    st.markdown(f"**🎯 Accuracy:** {result['accuracy']}")
    
    # Display the system's losing streak
    if st.session_state.losing_streak_prediction > 0:
        st.warning(f"**❌ แพ้ติดกัน:** {st.session_state.losing_streak_prediction} ครั้ง")
    else:
        st.success(f"**✅ แพ้ติดกัน:** 0 ครั้ง")
else:
    # Message when not enough data for analysis
    st.info(f"🔮 ผลการทำนาย กรุณาใส่ผลย้อนหลังอย่างน้อย 15 ตา เพื่อเริ่มต้นการวิเคราะห์ (ปัจจุบันมี {len(st.session_state.oracle_history)} ตา)")

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
    # Get the prediction result for the *current state* (before this new hand is added)
    # This is needed to get the prediction and associated patterns/momentum for learning
    # Only predict if enough history
    if len(st.session_state.oracle_history) >= 15: # Data threshold for prediction
        prediction_for_learning = oracle.predict_next(st.session_state.oracle_history, is_backtest=False) 

        # Update losing streak based on this prediction and the actual outcome
        # Only count if the system actually predicted P or B (not '⚠️')
        if prediction_for_learning['prediction'] in ['P', 'B']: 
            if outcome == 'T': 
                pass # Tie, losing streak does not change
            elif prediction_for_learning['prediction'] == outcome: # Correct prediction
                st.session_state.losing_streak_prediction = 0
            else: # Incorrect prediction
                st.session_state.losing_streak_prediction += 1
    
    st.session_state.oracle_history.append({'main_outcome': outcome}) 
    
    # Pass the full current history to update_learning_state to trigger backtest calculation
    oracle.update_learning_state(outcome, st.session_state.oracle_history) 
    st.rerun() 

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
            # Remove the last item
            st.session_state.oracle_history.pop()
            
            # Re-initialize engine and re-run history to update learning state correctly
            # This is necessary because OracleEngine is stateless and needs to rebuild its internal state
            # from the modified history.
            st.session_state.oracle_engine = OracleEngine() # Create a fresh engine
            
            # Recalculate losing streak for the *remaining* history
            current_losing_streak = 0
            if len(st.session_state.oracle_history) >= 15: # Only if enough history for predictions
                temp_oracle_for_streak = OracleEngine() # Use a temporary oracle to simulate predictions for streak calc
                for i in range(15, len(st.session_state.oracle_history)):
                    history_segment_for_pred = st.session_state.oracle_history[:i]
                    actual_outcome_for_streak_calc = st.session_state.oracle_history[i]['main_outcome']

                    pred_result_for_streak = temp_oracle_for_streak.predict_next(history_segment_for_pred)
                    
                    if pred_result_for_streak['prediction'] in ['P', 'B']:
                        if actual_outcome_for_streak_calc != 'T': # Only count if not Tie
                            if pred_result_for_streak['prediction'] == actual_outcome_for_streak_calc:
                                current_losing_streak = 0
                            else:
                                current_losing_streak += 1
            st.session_state.losing_streak_prediction = current_losing_streak

            # Rebuild the main oracle engine's state correctly by replaying remaining history
            main_oracle_rebuild = OracleEngine()
            if len(st.session_state.oracle_history) > 0:
                for i in range(len(st.session_state.oracle_history)):
                    # For each step in history, simulate adding it
                    history_segment_for_learning = st.session_state.oracle_history[:i+1] # History up to this point
                    actual_outcome_to_learn = st.session_state.oracle_history[i]['main_outcome']
                    
                    # Need to simulate prediction to get context for update_learning_state, but only if enough data
                    temp_prediction_context = {'prediction': '?', 'prediction_mode': None} # Default for short history
                    if len(history_segment_for_learning) > 0: # Ensure history_segment_for_learning is not empty for next_pred
                        # To correctly rebuild learning state, we need to know what the engine *would have predicted* at each step
                        # This is a bit tricky with stateless engine and last_prediction_context
                        # Simplest robust way: if it was long enough to predict, get prediction_context
                        if len(history_segment_for_learning) >= 15: # Only if history was long enough for a prediction
                            # Pass history *before* this outcome was added to get accurate context
                            temp_pred_result = main_oracle_rebuild.predict_next(history_segment_for_learning[:-1], is_backtest=False)
                            main_oracle_rebuild.last_prediction_context = {
                                'prediction': temp_pred_result['prediction'],
                                'patterns': main_oracle_rebuild.detect_dna_patterns(history_segment_for_learning[:-1]),
                                'momentum': main_oracle_rebuild.detect_momentum(history_segment_for_learning[:-1]),
                                'intuition_applied': 'Intuition' in temp_pred_result['predicted_by'] if temp_pred_result['predicted_by'] else False,
                                'predicted_by': temp_pred_result['predicted_by'],
                                'dominant_pattern_id_at_prediction': main_oracle_rebuild.last_dominant_pattern_id, # This is tricky, might need to re-detect
                                'prediction_mode': temp_pred_result['prediction_mode']
                            }
                        
                    main_oracle_rebuild.update_learning_state(actual_outcome_to_learn, history_segment_for_learning)
                
                st.session_state.oracle_engine = main_oracle_rebuild
            else: # If history becomes empty after pop
                st.session_state.oracle_engine = OracleEngine() # Reset fully
                st.session_state.losing_streak_prediction = 0
        st.rerun()

# --- Reset All Button ---
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear() 
    st.session_state.oracle_engine = OracleEngine() 
    st.session_state.losing_streak_prediction = 0 
    st.rerun()

# --- Developer View (Moved to bottom and in an expander) ---
# Only show if enough history is present
if len(st.session_state.oracle_history) >= 15: # Data threshold for prediction
    current_prediction_info = oracle.predict_next(st.session_state.oracle_history)
    with st.expander("🧬 Developer View: คลิกเพื่อดูรายละเอียด"):
        st.code(current_prediction_info['developer_view'], language='text')

