# app.py
import streamlit as st
import asyncio
import time
import json 
import streamlit.components.v1 as components 

# --- Import OracleEngine from the separate file ---
# Ensure your oracle_engine.py is in the same directory
from oracle_engine import OracleEngine

# --- Function to generate BigRoad HTML for Streamlit component ---
def get_big_road_html(results_history):
    # This history will be processed in JavaScript to form the BigRoad
    js_history_str = json.dumps(results_history)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BigRoad Display</title>
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background-color: transparent; /* Make background transparent to blend with Streamlit */
                margin: 0;
                padding: 0;
                overflow: hidden; /* Prevent extra scrollbars in component body */
            }}
            #bigRoadDisplay {{
                background-color: #1a202c; /* Similar to bg-gray-900 */
                border-radius: 0.75rem; /* rounded-xl */
                box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.6); /* shadow-inner */
                overflow-x: auto; /* Enable horizontal scrolling for BigRoad */
                border: 1px solid #4a5568; /* border-gray-700 */
                padding: 0.5rem 0.25rem; /* Padding for the display area */
                max-height: 250px; /* Limit height for the BigRoad display */
                min-height: 150px; /* Ensure a minimum height even if empty */
                display: flex; /* Use flexbox for the outer container to align grid */
                justify-content: flex-start; /* Align grid to start (left) */
                align-items: flex-start; /* Align grid to top */
            }}
            /* Hide scrollbar for BigRoadDisplay on most browsers, but still allow scrolling */
            #bigRoadDisplay::-webkit-scrollbar {{
                height: 8px; /* Thinner scrollbar */
            }}
            #bigRoadDisplay::-webkit-scrollbar-track {{
                background: #2d3748; /* Darker track */
                border-radius: 4px;
            }}
            #bigRoadDisplay::-webkit-scrollbar-thumb {{
                background: #a0aec0; /* Lighter thumb */
                border-radius: 4px;
            }}
            #bigRoadDisplay::-webkit-scrollbar-thumb:hover {{
                background: #cbd5e0; /* Even lighter on hover */
            }}
            #bigRoadGrid {{
                display: grid;
                grid-auto-flow: column; /* Cells flow horizontally first, then wrap */
                grid-template-rows: repeat(6, minmax(0, 1fr)); /* Fixed 6 rows for BigRoad */
                gap: 1px; /* Gap between cells */
                width: max-content; /* Allow grid to expand horizontally based on content */
                min-width: 100%; /* Ensure it takes at least 100% of parent width initially for smaller content */
                padding: 0;
                margin: 0;
            }}
            .big-road-cell {{
                width: 38px; /* Fixed width for each cell */
                height: 38px; /* Fixed height for each cell */
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(255,255,255,0.08); /* Subtle grid lines */
                border-radius: 9999px; /* Fully rounded (circle) */
                position: relative;
                overflow: visible; /* Allow overflow for ellipse positioning */
                background-color: #111827; /* Background for empty cells, bg-gray-900 */
            }}
            .main-circle {{
                width: 32px; /* Inner circle size */
                height: 32px;
                border-radius: 9999px; /* Fully rounded (circle) */
                border-width: 2px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.3); /* Soft shadow */
            }}
            /* Specific colors for Banker, Player */
            .bg-red-500 {{ background-color: #ef4444; }}
            .border-red-600 {{ border-color: #dc2626; }}
            .bg-blue-500 {{ background-color: #3b82f6; }}
            .border-blue-600 {{ border-color: #2563eb; }}
            /* Tie Ellipse */
            .tie-ellipse {{
                position: absolute;
                top: 0;
                right: 0;
                transform: translate(30%, -30%); /* Position off the main circle */
                background-color: #22c55e; /* Green-500 from Tailwind for ellipse */
                color: white;
                font-size: 0.75rem; /* text-xs */
                font-weight: bold;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 9999px; /* rounded-full to make it look like an ellipse */
                width: 24px; /* w-6 */
                height: 16px; /* h-4 for ellipse shape */
                box-shadow: 0 1px 2px rgba(0,0,0,0.4);
                z-index: 10;
                border: 1px solid rgba(255,255,255,0.2); /* Slight white border */
            }}
        </style>
    </head>
    <body>
        <div id="bigRoadDisplay">
            <div id="bigRoadGrid">
                <!-- Cells will be dynamically generated by JavaScript -->
            </div>
        </div>

        <script>
            const rawBigRoadResults = {js_history_str}; // Raw history from Streamlit
            const MAX_ROWS = 6;
            const MIN_DISPLAY_COLS = 20; // Minimum columns to always display for a wider view

            function renderBigRoad() {
                const bigRoadGrid = document.getElementById('bigRoadGrid');
                bigRoadGrid.innerHTML = ''; // Clear existing cells for a fresh render

                // Calculate virtual grid based on actual BigRoad logic
                const virtualGrid = Array(MAX_ROWS).fill(0).map(() => Array(200).fill(null)); // Max 200 columns for now
                let currentColumn = 0;
                let currentRow = 0;
                let lastNonTieOutcome = null; // Stores the type of the last P or B that defined a column
                let lastNonTieGridPos = {row: -1, col: -1}; // Stores grid position of the last P or B circle
                let consecutiveTieCount = 0; // Accumulates ties until a P or B occurs

                for (let i = 0; i < rawBigRoadResults.length; i++) {
                    const result = rawBigRoadResults[i];
                    const resultType = result.main_outcome;

                    if (resultType === 'T') {
                        consecutiveTieCount++; // Just accumulate the tie count
                        // Ties do NOT create their own circles in the main BigRoad
                        // The tie count will be attached to the LAST non-tie circle
                        continue; // Skip to next iteration
                    }

                    // If we reached a P or B (non-tie outcome)
                    if (lastNonTieOutcome === null) { // First P or B outcome
                        // Initial placement
                        currentRow = 0;
                        currentColumn = 0;
                    } else if (resultType !== lastNonTieOutcome) {
                        // Change of type (P to B or B to P) -> new column
                        currentColumn++;
                        currentRow = 0;
                    } else { // Same type (P to P or B to B)
                        if (currentRow < MAX_ROWS - 1) {
                            // If there's still room in the current column (not yet 6 rows full)
                            currentRow++; // Move down in the same column
                        } else {
                            // If the current column is already full (currentRow is MAX_ROWS - 1),
                            // then move to a new column and start at the top (row 0)
                            currentColumn++;
                            currentRow = 0; // <--- This is the change for "หางมังกร" rule
                        }
                    }

                    // Store the P/B result in the virtual grid
                    // Also attach the accumulated tie count to this P/B result
                    virtualGrid[currentRow][currentColumn] = {
                        type: resultType,
                        tieCount: consecutiveTieCount // This will be 0 if no ties preceded, or N if N ties preceded
                    };
                    
                    // Update tracker for the last non-tie outcome and its position
                    lastNonTieOutcome = resultType;
                    lastNonTieGridPos = {row: currentRow, col: currentColumn};
                    consecutiveTieCount = 0; // Reset tie counter for the next sequence
                }

                // AFTER the loop: If history ends with ties, attach them to the very last P/B circle
                if (consecutiveTieCount > 0 && lastNonTieGridPos.row !== -1) {
                    // Find the last actual P/B circle plotted and update its tieCount
                    const lastPlottedCircle = virtualGrid[lastNonTieGridPos.row][lastNonTieGridPos.col];
                    if (lastPlottedCircle) {
                        lastPlottedCircle.tieCount = consecutiveTieCount;
                    }
                }

                // Determine actual MAX_COLS needed for rendering
                const renderedMaxCol = Math.max(MIN_DISPLAY_COLS, currentColumn + 5); // Add buffer cols for future plays
                bigRoadGrid.style.gridTemplateColumns = `repeat(${renderedMaxCol}, minmax(0, 1fr))`;


                // Render the physical HTML grid based on the populated virtual grid
                for (let r = 0; r < MAX_ROWS; r++) {
                    for (let c = 0; c < renderedMaxCol; c++) {
                        const result = virtualGrid[r][c]; // Get result from our processed grid

                        const cellDiv = document.createElement('div');
                        cellDiv.className = 'big-road-cell'; // Base styling for the grid cell

                        if (result) {
                            let mainCircleClass = ''; // Class for the main circle's color and border
                            switch (result.type) {
                                case 'B':
                                    mainCircleClass = 'bg-red-500 border-red-600';
                                    break;
                                case 'P':
                                    mainCircleClass = 'bg-blue-500 border-blue-600';
                                    break;
                                // No 'T' case here for main circle as 'T's don't create their own circles in this logic
                            }

                            // Create the main colored circle (Banker or Player)
                            const mainCircle = document.createElement('div');
                            mainCircle.className = `main-circle ${mainCircleClass}`;
                            cellDiv.appendChild(mainCircle);

                            // Add the tie ellipse if this P/B result has an associated tie count
                            if (result.tieCount > 0) {
                                const tieEllipse = document.createElement('div');
                                tieEllipse.className = 'tie-ellipse';
                                tieEllipse.textContent = result.tieCount; // Display the consecutive tie count
                                cellDiv.appendChild(tieEllipse); // Add ellipse to the cell
                            }
                        }
                        // Add empty cell background for null grid spots
                        bigRoadGrid.appendChild(cellDiv);
                    }
                }
                
                // Automatically scroll the BigRoad display to the far right to show the most recent results
                const bigRoadDisplay = document.getElementById('bigRoadDisplay');
                // Use a slight delay to ensure the content has rendered before scrolling
                setTimeout(() => {
                    bigRoadDisplay.scrollLeft = bigRoadDisplay.scrollWidth;
                }, 100); 
            }

            // Call renderBigRoad when the component loads in the browser
            renderBigRoad();
        </script>
    </body>
    </html>
    """
    return html_content

# --- Streamlit App Configuration ---
st.set_page_config(page_title=f"ORACLE Predictor", layout="centered") 

# --- State Management for OracleEngine and History ---
if 'oracle_engine' not in st.session_state:
    st.session_state.oracle_engine = OracleEngine()
if 'oracle_history' not in st.session_state:
    st.session_state.oracle_history = []
if 'losing_streak_prediction' not in st.session_state:
    st.session_state.losing_streak_prediction = 0

oracle = st.session_state.oracle_engine

# --- Custom CSS for Streamlit UI ---
st.markdown(f"""
<style>
/* Font import from Google Fonts - Using Inter and Orbitron */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Orbitron:wght@700;900&display=swap');

.stApp {{
    padding-top: 1rem; 
}}

.center-gold-title {{
    text-align: center;
    color: gold; 
    font-size: 3.5em; 
    font-weight: 900; 
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); 
    margin-bottom: 0.2rem; 
    padding-bottom: 0px;
    font-family: 'Orbitron', 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; 
}}
.version-text {{
    font-size: 0.5em; 
    font-weight: normal;
    color: #CCCCCC; 
    vertical-align: super; 
    margin-left: 0.2em; 
    font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; 
}}
h3 {{
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}}
.stMarkdown, .stText, .stInfo, .stWarning, .stSuccess {{
    margin-top: 0.2rem;
    margin-bottom: 0.2rem;
    font-family: 'Inter', sans-serif; 
}}
.stButton>button {{
    margin-top: 0.2rem;
    margin-bottom: 0.2rem;
    line-height: 1.2; 
    font-family: 'Inter', sans-serif; 
}}

.prediction-h1 {{
    text-align: center; 
    font-size: 2.5em; 
    margin-top: 0.2rem;
    margin-bottom: 0.2rem;
    font-family: 'Inter', sans-serif; 
}}

div[data-testid="stColumns"] > div {{
    padding-left: 0.2rem;
    padding-right: 0.2rem;
}}
</style>
""", unsafe_allow_html=True)

# Main title of the app, dynamically displaying the version from OracleEngine
st.markdown(f'<h1 class="center-gold-title">🔮 ORACLE <span class="version-text">{oracle.VERSION}</span></h1>', unsafe_allow_html=True)

# --- Prediction Display Section ---
current_prediction_mode = None
if len(st.session_state.oracle_history) >= OracleEngine.PREDICTION_THRESHOLD: 
    temp_result = oracle.predict_next(st.session_state.oracle_history, is_backtest=False)
    current_prediction_mode = temp_result['prediction_mode']

mode_text = ""
if current_prediction_mode == 'ตาม':
    mode_text = "ผลวิเคราะห์: ⏮️ **ตาม**" 
elif current_prediction_mode == 'สวน':
    mode_text = "ผลวิเคราะห์: ⏭️ **สวน**" 
elif current_prediction_mode == '⚠️':
    mode_text = "ผลวิเคราะห์: ⚠️ **งดเดิมพัน**" 
else:
    mode_text = "ผลวิเคราะห์:" 

st.markdown(f"<h3>{mode_text}</h3>", unsafe_allow_html=True)

if len(st.session_state.oracle_history) >= OracleEngine.PREDICTION_THRESHOLD: 
    result = oracle.predict_next(st.session_state.oracle_history)

    prediction_text = ""
    if result['prediction'] == 'P':
        prediction_text = f"🔵 P" 
    elif result['prediction'] == 'B':
        prediction_text = f"🔴 B" 
    elif result['prediction'] == '⚠️':
        prediction_text = f"⚠️" 
    else:
        prediction_text = result['prediction'] 

    st.markdown(f'<h1 class="prediction-h1">{prediction_text}</h1>', unsafe_allow_html=True)
    
    st.markdown(f"📈 **ตามสูตรชนะ** : {oracle.tam_sutr_wins} ครั้ง")
    st.markdown(f"📉 **สวนสูตรชนะ** : {oracle.suan_sutr_wins} ครั้ง")

    st.markdown(f"**🎯 Accuracy:** {result['accuracy']}")
    
    if st.session_state.losing_streak_prediction > 0:
        st.warning(f"**❌ แพ้ติดกัน:** {st.session_state.losing_streak_prediction} ครั้ง")
    else:
        st.success(f"**✅ แพ้ติดกัน:** 0 ครั้ง")
else:
    st.info(f"🔮 ผลการทำนาย กรุณาใส่ผลย้อนหลังอย่างน้อย {OracleEngine.PREDICTION_THRESHOLD} ตา เพื่อเริ่มต้นการวิเคราะห์ (ปัจจุบันมี {len(st.session_state.oracle_history)} ตา)")

# --- Total Tie Count Display ---
# Calculate the number of 'T' outcomes in the history
tie_count = sum(1 for item in st.session_state.oracle_history if item['main_outcome'] == 'T')
st.markdown(f"🤝 **เสมอทั้งหมด:** {tie_count} ครั้ง")

st.markdown("---") 
st.markdown("<h3>📊 BigRoad ผลลัพธ์</h3>", unsafe_allow_html=True)
# Embed the BigRoad HTML component
components.html(get_big_road_html(st.session_state.oracle_history), height=250, scrolling=True)

st.markdown("---") 

# --- Record Outcome Buttons Section ---
st.markdown("<h3>➕ บันทึกผลลัพธ์</h3>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

def add_new_result(outcome):
    prediction_for_learning = None
    if len(st.session_state.oracle_history) >= OracleEngine.PREDICTION_THRESHOLD: 
        prediction_for_learning = oracle.predict_next(st.session_state.oracle_history, is_backtest=False) 

        if prediction_for_learning and prediction_for_learning['prediction'] in ['P', 'B']: 
            if outcome == 'T': 
                pass 
            elif prediction_for_learning['prediction'] == outcome: 
                st.session_state.losing_streak_prediction = 0 
            else: 
                st.session_state.losing_streak_prediction += 1 
    
    st.session_state.oracle_history.append({'main_outcome': outcome}) 
    
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
            st.session_state.oracle_history.pop()
            
            st.session_state.oracle_engine = OracleEngine() 
            
            current_losing_streak = 0
            temp_oracle_for_streak = OracleEngine() 
            
            for i in range(OracleEngine.PREDICTION_THRESHOLD, len(st.session_state.oracle_history)):
                history_segment_for_pred = st.session_state.oracle_history[:i] 
                actual_outcome_for_streak_calc = st.session_state.oracle_history[i]['main_outcome']

                pred_result_for_streak = temp_oracle_for_streak.predict_next(history_segment_for_pred)
                
                if pred_result_for_streak and pred_result_for_streak['prediction'] in ['P', 'B']:
                    if actual_outcome_for_streak_calc != 'T':
                        if pred_result_for_streak['prediction'] == actual_outcome_for_streak_calc:
                            current_losing_streak = 0 
                        else:
                            current_losing_streak += 1 
            st.session_state.losing_streak_prediction = current_losing_streak

            main_oracle_rebuild = OracleEngine()
            if len(st.session_state.oracle_history) > 0:
                for i in range(len(st.session_state.oracle_history)):
                    history_segment_for_learning = st.session_state.oracle_history[:i+1] 
                    actual_outcome_to_learn = st.session_state.oracle_history[i]['main_outcome']
                    
                    if len(history_segment_for_learning) > OracleEngine.PREDICTION_THRESHOLD -1: 
                        temp_pred_result = main_oracle_rebuild.predict_next(history_segment_for_learning[:-1], is_backtest=False)
                        
                        main_oracle_rebuild.last_prediction_context = {
                            'prediction': temp_pred_result['prediction'],
                            'prediction_mode': temp_pred_result['prediction_mode'],
                            'patterns': temp_pred_result['patterns'] if 'patterns' in temp_pred_result else {},
                            'momentum': temp_pred_result['momentum'] if 'momentum' in temp_pred_result else {},
                            'intuition_applied': temp_pred_result['intuition_applied'] if 'intuition_applied' in temp_pred_result else False,
                            'predicted_by': temp_pred_result['predicted_by'] if 'predicted_by' in temp_pred_result else 'N/A',
                            'dominant_pattern_id_at_prediction': temp_pred_result['dominant_pattern_id_at_prediction'] if 'dominant_pattern_id_at_prediction' in temp_pred_result else 'N/A',
                            'confidence': temp_pred_result['confidence'] if 'confidence' in temp_pred_result else 0.5
                        }
                    else:
                         main_oracle_rebuild.last_prediction_context = None 

                    main_oracle_rebuild.update_learning_state(actual_outcome_to_learn, history_segment_for_learning)
                
                st.session_state.oracle_engine = main_oracle_rebuild 
            else: 
                st.session_state.oracle_engine = OracleEngine() 
                st.session_state.losing_streak_prediction = 0 
        st.rerun() 

# --- Reset All Button ---
if st.button("🔄 Reset ระบบทั้งหมด", use_container_width=True, key="reset_all"):
    st.session_state.oracle_history.clear() 
    st.session_state.oracle_engine = OracleEngine() 
    st.session_state.losing_streak_prediction = 0 
    st.rerun() 

# --- Developer View Expander ---
if len(st.session_state.oracle_history) >= OracleEngine.PREDICTION_THRESHOLD: 
    current_prediction_info = oracle.predict_next(st.session_state.oracle_history)
    with st.expander("🧬 Developer View: คลิกเพื่อดูรายละเอียด"):
        st.code(current_prediction_info['developer_view'], language='text')
