import streamlit as st
import pandas as pd
import asyncio
from oracle_engine import OracleEngine, _cached_backtest_accuracy, _build_big_road_data, get_gemini_analysis

# --- Page Configuration ---
st.set_page_config(
    page_title="Oracle AI Baccarat Predictor",
    page_icon="🔮",
    layout="centered", 
    initial_sidebar_state="collapsed" 
)

# --- Initialize Session State ---
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'drawdown' not in st.session_state:
    st.session_state.drawdown = 0 
if 'bet_log' not in st.session_state:
    st.session_state.bet_log = pd.DataFrame(columns=['Hand', 'Predict', 'Actual', 'Recommendation', 'Outcome'])
if 'gemini_analysis_result' not in st.session_state:
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
if 'gemini_analysis_loading' not in st.session_state:
    st.session_state.gemini_analysis_loading = False
if 'show_big_road_tooltip' not in st.session_state:
    st.session_state.show_big_road_tooltip = False


# --- Helper Function for Big Road Display ---
def display_big_road(big_road_data):
    """
    Renders the Big Road visualization using Streamlit components.
    Adjusted for better mobile viewing.
    """
    if not big_road_data:
        st.info("ไม่มีประวัติการเล่น (Big Road จะแสดงเมื่อมีผลลัพธ์).")
        return

    st.markdown("""
    <style>
    .big-road-container {
        display: flex;
        flex-wrap: nowrap; 
        overflow-x: auto; 
        border: 1px solid #333;
        padding: 5px;
        background-color: #1a1a1a;
        min-height: 120px; 
    }
    .big-road-column {
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        margin: 0 2px;
    }
    .big-road-cell {
        width: 25px; 
        height: 25px; 
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 10px; 
        font-weight: bold;
        color: white;
        margin: 1px;
        flex-shrink: 0; 
        position: relative; 
    }
    .player-cell { background-color: #007bff; } 
    .banker-cell { background-color: #dc3545; } 
    .s6-cell { background-color: #ffc107; color: black; } 
    .tie-indicator {
        position: absolute;
        width: 8px; 
        height: 8px;
        border-radius: 50%;
        background-color: green;
        top: 0;
        right: 0;
        transform: translate(25%, -25%); 
    }
    .natural-indicator { 
        position: absolute;
        width: 8px; 
        height: 8px;
        border-radius: 50%;
        background-color: purple; 
        bottom: 0;
        left: 0;
        transform: translate(-25%, 25%);
    }
    </style>
    """, unsafe_allow_html=True)

    big_road_html = '<div class="big-road-container">'
    for col in big_road_data:
        big_road_html += '<div class="big-road-column">'
        for cell_data in col:
            if cell_data:
                outcome, ties, is_natural = cell_data
                cell_class = ""
                cell_text = ""
                if outcome == 'P':
                    cell_class = "player-cell"
                elif outcome == 'B':
                    cell_class = "banker-cell"
                elif outcome == 'S6':
                    cell_class = "s6-cell"
                    cell_text = "S6" 
                
                tie_html = f'<div class="tie-indicator"></div>' if ties > 0 else ''
                natural_html = f'<div class="natural-indicator"></div>' if is_natural else '' 

                big_road_html += f'<div class="big-road-cell {cell_class}">{cell_text}{tie_html}{natural_html}</div>'
            else:
                big_road_html += '<div class="big-road-cell" style="background-color: transparent;"></div>' 
        big_road_html += '</div>'
    big_road_html += '</div>'
    st.markdown(big_road_html, unsafe_allow_html=True)


# --- Callback Functions ---
def record_result(outcome_type):
    current_prediction_output = st.session_state.oracle_engine.predict_next(
        current_live_drawdown=st.session_state.drawdown,
        current_big_road_data=_build_big_road_data(st.session_state.history),
        history_for_prediction=st.session_state.history 
    )
    predicted_side = current_prediction_output.get('prediction', '?')
    recommended_action = current_prediction_output.get('recommendation', 'Avoid ❌')

    is_any_natural = False 
    
    if outcome_type == 'T':
        if st.session_state.history:
            last_hand_main_outcome = st.session_state.history[-1]['main_outcome']
            if last_hand_main_outcome in ['P', 'B', 'S6']:
                st.session_state.history[-1]['ties'] += 1
            else: 
                st.session_state.history.append({'main_outcome': outcome_type, 'ties': 0, 'is_any_natural': is_any_natural})
        else: 
            st.session_state.history.append({'main_outcome': outcome_type, 'ties': 0, 'is_any_natural': is_any_natural})
    else:
        st.session_state.history.append({'main_outcome': outcome_type, 'ties': 0, 'is_any_natural': is_any_natural})


    outcome_status = "Recorded"
    if predicted_side != '?': 
        is_correct = False
        if predicted_side == outcome_type:
            is_correct = True
        elif predicted_side == 'B' and outcome_type == 'S6': 
            is_correct = True

        if recommended_action == 'Play ✅':
            if is_correct:
                st.session_state.drawdown = 0 
            else:
                st.session_state.drawdown += 1 
        
    st.session_state.oracle_engine._update_learning(
        predicted_outcome=predicted_side,
        actual_outcome=outcome_type, 
        patterns_detected=st.session_state.oracle_engine.detect_patterns(st.session_state.history, _build_big_road_data(st.session_state.history)),
        momentum_detected=st.session_state.oracle_engine.detect_momentum(st.session_state.history, _build_big_road_data(st.session_state.history)),
        sequences_detected=st.session_state.oracle_engine._detect_sequences(st.session_state.history)
    )

    new_log_entry = pd.DataFrame([{
        'Hand': len(st.session_state.history), 
        'Predict': predicted_side,
        'Actual': outcome_type,
        'Recommendation': recommended_action,
        'Outcome': outcome_status 
    }])
    st.session_state.bet_log = pd.concat([st.session_state.bet_log, new_log_entry], ignore_index=True)

    _cached_backtest_accuracy.clear() 

def undo_last_hand():
    if st.session_state.history:
        st.session_state.history.pop() 
        if not st.session_state.bet_log.empty:
            st.session_state.bet_log = st.session_state.bet_log.iloc[:-1] 
        
        st.session_state.drawdown = 0
        temp_engine_for_recalc = OracleEngine() 
        for i, hand_data in enumerate(st.session_state.history):
            if i >= 2: 
                sim_prediction_output = temp_engine_for_recalc.predict_next(
                    current_live_drawdown=0, 
                    current_big_road_data=_build_big_road_data(st.session_state.history[:i]), 
                    history_for_prediction=st.session_state.history[:i] 
                )
                sim_predicted_side = sim_prediction_output.get('prediction')
                sim_recommended_action = sim_prediction_output.get('recommendation')

                if sim_predicted_side != '?' and sim_recommended_action == 'Play ✅':
                    is_correct = False
                    if sim_predicted_side == hand_data['main_outcome']:
                        is_correct = True
                    elif sim_predicted_side == 'B' and hand_data['main_outcome'] == 'S6':
                        is_correct = True
                    
                    if is_correct:
                        st.session_state.drawdown = 0
                    else:
                        st.session_state.drawdown += 1
            
            temp_engine_for_recalc._update_learning(
                predicted_outcome=sim_predicted_side if 'sim_predicted_side' in locals() else '?', 
                actual_outcome=hand_data['main_outcome'],
                patterns_detected={}, 
                momentum_detected={},
                sequences_detected={}
            )

        st.session_state.oracle_engine.reset_learning_states_on_undo()
        _cached_backtest_accuracy.clear()

def reset_shoe():
    st.session_state.oracle_engine.reset_history()
    st.session_state.history = []
    st.session_state.drawdown = 0
    st.session_state.bet_log = pd.DataFrame(columns=['Hand', 'Predict', 'Actual', 'Recommendation', 'Outcome'])
    st.session_state.gemini_analysis_result = "ยังไม่มีการวิเคราะห์จาก Gemini"
    st.session_state.gemini_analysis_loading = False
    _cached_backtest_accuracy.clear() 

async def analyze_with_gemini_async():
    st.session_state.gemini_analysis_loading = True
    st.session_state.gemini_analysis_result = "กำลังวิเคราะห์ด้วย Gemini AI... กรุณารอสักครู่ ⏳"
    st.rerun() 
    
    try:
        if len(st.session_state.history) < 5:
            st.session_state.gemini_analysis_result = "❗ ประวัติการเล่นไม่เพียงพอสำหรับการวิเคราะห์เชิงลึก (ต้องการอย่างน้อย 5 ตา)"
        else:
            analysis = await get_gemini_analysis(st.session_state.history)
            st.session_state.gemini_analysis_result = analysis
    except Exception as e:
        st.session_state.gemini_analysis_result = f"❌ เกิดข้อผิดพลาดในการเรียกใช้ Gemini AI: {e}"
    finally:
        st.session_state.gemini_analysis_loading = False
        st.rerun() 

def analyze_with_gemini_sync():
    asyncio.run(analyze_with_gemini_async())


# --- UI Layout ---

st.markdown(
    """
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #f0f2f6; 
        background-color: #0e1117; 
    }

    .header-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 20px;
        padding-top: 10px;
    }
    .header-text {
        font-size: 2.8em; 
        font-weight: bold;
        color: gold; 
        margin: 0;
        line-height: 1;
    }
    .version-text {
        font-size: 1.1em; 
        color: #bbb; 
        margin: 0;
        line-height: 1;
        align-self: flex-end; 
    }
    .magic-ball-icon {
        font-size: 3.5em; 
        line-height: 1;
    }

    h3 {
        margin-top: 25px;
        margin-bottom: 15px;
        color: #f0f2f6; 
        border-bottom: 1px solid #333; 
        padding-bottom: 5px;
    }

    /* Button Styling */
    .stButton>button {
        width: 100%; 
        margin-bottom: 8px; 
        height: 55px; 
        font-size: 1.2em; 
        border-radius: 8px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); 
        border: none;
    }

    /* Specific Button Colors */
    .stButton button[data-testid="stButton-P"] {
        background-color: #007bff; /* Blue */
        color: white;
    }
    .stButton button[data-testid="stButton-P"]:hover {
        background-color: #0056b3;
    }
    .stButton button[data-testid="stButton-B"] {
        background-color: #dc3545; /* Red */
        color: white;
    }
    .stButton button[data-testid="stButton-B"]:hover {
        background-color: #b02a37;
    }
    .stButton button[data-testid="stButton-T"] {
        background-color: #28a745; /* Green */
        color: white;
    }
    .stButton button[data-testid="stButton-T"]:hover {
        background-color: #1e7e34;
    }
    .stButton button[data-testid="stButton-S6"] {
        background-color: #ffc107; /* Orange/Yellow */
        color: black; /* Black text for contrast on yellow */
    }
    .stButton button[data-testid="stButton-S6"]:hover {
        background-color: #e0a800;
    }

    /* General action buttons (Undo, Reset, Gemini) */
    .stButton button:not([data-testid*="stButton-P"]):not([data-testid*="stButton-B"]):not([data-testid*="stButton-T"]):not([data-testid*="stButton-S6"]) {
        background-color: #282b30; /* Darker background for general actions */
        color: white;
    }
    .stButton button:not([data-testid*="stButton-P"]):not([data-testid*="stButton-B"]):not([data-testid*="stButton-T"]):not([data-testid*="stButton-S6"]):hover {
        background-color: #3e4247;
    }


    /* Prediction/Recommendation Text Styling */
    .prediction-value {
        font-size: 2.2em; 
        font-weight: bold;
    }
    .recommendation-value {
        font-size: 1.6em; 
        font-weight: bold;
    }
    .confidence-value, .risk-value, .drawdown-value, .tie-opportunity-value {
        font-size: 1.3em; 
        font-weight: bold;
    }

    .stAlert {
        border-radius: 8px;
        padding: 10px 15px;
    }

    .stDataFrame {
        font-size: 0.9em; 
    }
    .stDataFrame table {
        background-color: #1a1a1a; 
        color: #f0f2f6;
    }
    .stDataFrame th {
        background-color: #282b30; 
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="header-container">
        <span class="magic-ball-icon">🔮</span>
        <div>
            <p class="header-text">Oracle AI</p>
            <p class="version-text">v{st.session_state.oracle_engine.__version__}</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown("<h3>บันทึกผลลัพธ์</h3>")
col_p, col_b = st.columns(2)
with col_p:
    st.button("P (Player)", on_click=record_result, args=('P',), key="stButton-P") # Added key for specific CSS targeting
with col_b:
    st.button("B (Banker)", on_click=record_result, args=('B',), key="stButton-B") # Added key

col_t, col_s6 = st.columns(2)
with col_t:
    st.button("T (Tie)", on_click=record_result, args=('T',), key="stButton-T") # Added key
with col_s6:
    st.button("S6 (Super6)", on_click=record_result, args=('S6',), key="stButton-S6") # Added key

st.button("ย้อนกลับ (Undo)", on_click=undo_last_hand, help="ย้อนกลับตาที่แล้ว")
st.button("เริ่มต้นขอนใหม่", on_click=reset_shoe, help="ล้างประวัติทั้งหมดและเริ่มต้นใหม่")

if not st.session_state.gemini_analysis_loading:
    st.button("วิเคราะห์ด้วย Gemini AI (แบบ Manual)", on_click=analyze_with_gemini_sync)
else:
    st.button("กำลังวิเคราะห์ด้วย Gemini AI... ⏳", disabled=True)


st.markdown("---") 


st.markdown("<h3>การทำนายและคำแนะนำ</h3>")
prediction_output = st.session_state.oracle_engine.predict_next(
    current_live_drawdown=st.session_state.drawdown,
    current_big_road_data=_build_big_road_data(st.session_state.history),
    history_for_prediction=st.session_state.history 
)

st.markdown(f"**ทำนาย:** <span class='prediction-value' style='color: {'red' if prediction_output['prediction'] == 'B' else ('blue' if prediction_output['prediction'] == 'P' else ('#ffc107' if prediction_output['prediction'] == 'S6' else 'white'))}'>{prediction_output['prediction']}</span>", unsafe_allow_html=True)
st.markdown(f"**คำแนะนำ:** <span class='recommendation-value' style='color: {'lightgreen' if 'Play' in prediction_output['recommendation'] else 'red'}'>{prediction_output['recommendation']}</span>", unsafe_allow_html=True)
st.markdown(f"**ความมั่นใจโดยรวม:** <span class='confidence-value'>{prediction_output['overall_confidence']:.1f}%</span>", unsafe_allow_html=True)
st.markdown(f"**ระดับความเสี่ยง:** <span class='risk-value'>{prediction_output['risk']}</span>", unsafe_allow_html=True)


st.markdown("<h3>สถานะ Drawdown</h3>")
drawdown_color = "lightgreen"
if st.session_state.drawdown >= 1: drawdown_color = "orange"
if st.session_state.drawdown >= 2: drawdown_color = "red"
if st.session_state.drawdown >= 3: drawdown_color = "#8b0000" 

st.markdown(f"**Drawdown ปัจจุบัน:** <span class='drawdown-value' style='color: {drawdown_color};'>{st.session_state.drawdown}</span>", unsafe_allow_html=True)
st.markdown(f"ระดับความเสี่ยงโดยรวม: **{prediction_output['risk']}** (จาก AI)")


st.markdown("<h3>โอกาส Tie / Super6</h3>")
tie_analysis = st.session_state.oracle_engine.get_tie_opportunity_analysis(st.session_state.history)
st.markdown(f"**โอกาส:** <span class='tie-opportunity-value' style='color: {'lightgreen' if tie_analysis['prediction'] == 'T' else 'white'}'>{tie_analysis['prediction']}</span>", unsafe_allow_html=True)
st.markdown(f"**ความมั่นใจ:** {tie_analysis['confidence']:.1f}%")
st.markdown(f"**เหตุผล:** {tie_analysis['reason']}")

st.markdown("---") 


st.markdown("<h3>ประวัติขอนปัจจุบัน (Big Road)</h3>")
current_big_road_data = _build_big_road_data(st.session_state.history)
display_big_road(current_big_road_data)

st.toggle("แสดงคำอธิบาย Big Road", key="show_big_road_tooltip")
if st.session_state.show_big_road_tooltip:
    st.info("""
    **Big Road (บิ๊กโรด)** แสดงผลลัพธ์การเล่น Baccarat ในรูปแบบตาราง:
    * **วงกลมสีน้ำเงิน:** แทน Player Win
    * **วงกลมสีแดง:** แทน Banker Win (รวมถึง Super6)
    * **วงกลมสีเหลือง:** แทน Super6 Win (มีข้อความ 'S6' ข้างใน)
    * **จุดสีเขียวเล็กๆ ที่มุมบนขวา:** แสดง Tie (จะปรากฏบนวงกลม Player/Banker/Super6 ล่าสุด)
    * **คอลัมน์ใหม่:** เริ่มขึ้นเมื่อผลลัพธ์เปลี่ยนจาก Player เป็น Banker หรือ Banker เป็น Player
    * **คอลัมน์เดียวกัน:** ผลลัพธ์เดิมจะเรียงลงมาในคอลัมน์เดียวกัน
    """)

st.markdown("---") 


st.markdown("<h3>การวิเคราะห์จาก Gemini AI</h3>")
if st.session_state.gemini_analysis_loading:
    st.info("กำลังวิเคราะห์ด้วย Gemini AI... กรุณารอสักครู่ ⏳") 
else:
    st.markdown(st.session_state.gemini_analysis_result)

st.markdown("---") 

st.markdown("<h3>Bet Log</h3>")
if not st.session_state.bet_log.empty:
    st.dataframe(
        st.session_state.bet_log,
        hide_row_index=True,
        use_container_width=True, 
        height=(min(len(st.session_state.bet_log), 10) * 35) + 38 
    )
else:
    st.info("ไม่มีบันทึกการเดิมพัน")


st.markdown("<h3>ความแม่นยำทางประวัติศาสตร์</h3>")
accuracy_results = _cached_backtest_accuracy(st.session_state.history)

st.markdown(f"**ความแม่นยำโดยรวม (จาก {accuracy_results['total_bets']} ครั้งที่ทำนาย):** <span class='confidence-value' style='color: {'lightgreen' if accuracy_results['overall_accuracy'] >= 60 else 'orange'}'>{accuracy_results['overall_accuracy']:.2f}%</span>", unsafe_allow_html=True)
st.markdown(f"ความแม่นยำ Player: {accuracy_results['player_accuracy']:.2f}%")
st.markdown(f"ความแม่นยำ Banker: {accuracy_results['banker_accuracy']:.2f}%")
st.markdown(f"ความแม่นยำ Super6: {accuracy_results['s6_accuracy']:.2f}%")

st.markdown("---")
st.caption(f"Oracle AI v{st.session_state.oracle_engine.__version__} - Powered by Streamlit & Google Gemini API")
