# streamlit_app.py
import streamlit as st
# บรรทัดนี้จะ import คลาส OracleEngine จากไฟล์ oracle_engine.py
# ตรวจสอบให้แน่ใจว่าไฟล์ oracle_engine.py อยู่ในไดเรกทอรีเดียวกันกับ streamlit_app.py
from oracle_engine import OracleEngine


def render_big_road(big_road_data):
    """
    สร้างโค้ด HTML/CSS สำหรับการแสดงผล Big Road.

    Args:
        big_road_data (list): ลิสต์ 2 มิติ (grid[row][col]) ของ dictionary เซลล์
                              ที่ได้จาก _build_big_road ใน OracleEngine.

    Returns:
        str: สตริง HTML ที่จะถูกเรนเดอร์โดย st.markdown.
    """
    html_content = """
    <style>
        /* สไตล์สำหรับ Container หลักของ Big Road */
        .big-road-container {
            display: grid;
            grid-template-rows: repeat(6, 30px); /* กำหนด 6 แถว แต่ละแถวสูง 30px */
            grid-auto-columns: 30px; /* สร้างคอลัมน์อัตโนมัติ แต่ละคอลัมน์กว้าง 30px */
            grid-auto-flow: column; /* จัดเรียงเซลล์แบบเติมคอลัมน์ก่อน แล้วค่อยย้ายไปคอลัมน์ถัดไป */
            border: 1px solid #333; /* ขอบตาราง */
            background-color: #0A1C2B; /* พื้นหลังสีเข้ม */
            padding: 5px; /* ระยะห่างภายใน container */
            overflow-x: auto; /* เปิดใช้งานการเลื่อนแนวนอนหากเนื้อหาเกิน */
            width: 100%; /* ใช้ความกว้างเต็มพื้นที่ที่กำหนด */
            max-width: 900px; /* จำกัดความกว้างสูงสุดของตาราง (สามารถปรับได้) */
            box-sizing: border-box; /* รวม padding และ border ในขนาด element */
            font-family: Arial, sans-serif; /* ฟอนต์ */
            margin-top: 20px; /* ระยะห่างด้านบน */
        }
        /* สไตล์สำหรับแต่ละเซลล์ใน Big Road */
        .big-road-cell {
            width: 30px;
            height: 30px;
            display: flex;
            justify-content: center; /* จัดตำแหน่งกึ่งกลางแนวนอน */
            align-items: center; /* จัดตำแหน่งกึ่งกลางแนวตั้ง */
            position: relative; /* สำคัญสำหรับการจัดตำแหน่ง Tie และ Pair ด้วย absolute positioning */
            box-sizing: border-box;
            /* border: 0.5px solid #1a3a5b; /* ใช้สำหรับ debugging เพื่อดูขอบเซลล์ */ */
        }
        /* สไตล์สำหรับวงกลม Player, Banker และ Tie Label */
        .player-circle, .banker-circle, .tie-label-cell {
            width: 25px; /* ขนาดวงกลม */
            height: 25px;
            border-radius: 50%; /* ทำให้เป็นวงกลม */
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            color: white; /* สีข้อความ */
            font-size: 14px;
        }
        .player-circle {
            background-color: #007bff; /* สีน้ำเงินสำหรับ Player */
        }
        .banker-circle {
            background-color: #dc3545; /* สีแดงสำหรับ Banker */
        }
        /* สไตล์สำหรับเส้น Tie ที่พาดผ่านวงกลม P/B */
        .tie-symbol {
            position: absolute;
            width: 100%; /* ความกว้างเต็มเซลล์ */
            height: 2px; /* ความหนาของเส้น */
            background-color: #28a745; /* สีเขียวสำหรับ Tie */
            transform: rotate(-45deg); /* หมุน 45 องศาเพื่อสร้างเส้นทแยงมุม */
            z-index: 10; /* ให้เส้นอยู่ด้านบนของวงกลม */
        }
        /* สไตล์สำหรับเซลล์ Tie เดี่ยวๆ (ถ้าไม่มี P/B อยู่ก่อนหน้า) */
        .tie-label-cell {
            background-color: #28a745; /* พื้นหลังสีเขียว */
            color: white;
            font-size: 12px; /* ขนาดฟอนต์สำหรับ 'T' */
        }
        /* สไตล์สำหรับจุดคู่ (Pair) */
        /* ข้อจำกัด: การจัดตำแหน่งจุดคู่ใน Streamlit ด้วย HTML/CSS อาจไม่ได้สมบูรณ์แบบ
           เหมือนตารางคาสิโนจริง ๆ เนื่องจากข้อจำกัดในการเรนเดอร์กราฟิกที่ซับซ้อนภายในเซลล์ HTML
           แต่จะพยายามใช้สัญลักษณ์ที่สื่อความหมายได้ใกล้เคียงที่สุด */
        .player-pair-dot {
            position: absolute;
            width: 6px;
            height: 6px;
            background-color: #007bff; /* สีน้ำเงินสำหรับ Player Pair */
            border-radius: 50%;
            top: 1px; /* จัดตำแหน่งที่มุมซ้ายบน */
            left: 1px;
            border: 1px solid white; /* ขอบขาวเพื่อให้มองเห็นชัดเจน */
        }
        .banker-pair-dot {
            position: absolute;
            width: 6px;
            height: 6px;
            background-color: #dc3545; /* สีแดงสำหรับ Banker Pair */
            border-radius: 50%;
            bottom: 1px; /* จัดตำแหน่งที่มุมขวาล่าง */
            right: 1px;
            border: 1px solid white; /* ขอบขาวเพื่อให้มองเห็นชัดเจน */
        }
    </style>
    <div class="big-road-container">
    """

    num_rows = len(big_road_data) # จำนวนแถวใน Big Road (ปกติคือ 6)
    num_cols = len(big_road_data[0]) if big_road_data and num_rows > 0 else 0 # จำนวนคอลัมน์

    if num_rows == 0 or num_cols == 0:
        return "ไม่มีข้อมูล Big Road ให้แสดง"

    # วนลูปตามคอลัมน์ก่อน แล้วค่อยวนแถว (c_idx -> r_idx)
    # เพื่อให้ตรงกับพฤติกรรมของ CSS grid-auto-flow: column
    for c_idx in range(num_cols):
        for r_idx in range(num_rows):
            cell = big_road_data[r_idx][c_idx] # เข้าถึงข้อมูลเซลล์จาก normalized_grid [row][col]
            
            html_content += '<div class="big-road-cell">' # เริ่มต้น div สำหรับแต่ละเซลล์
            
            # ตรวจสอบประเภทผู้ชนะและสร้างวงกลมที่เหมาะสม
            if cell['winner'] == 'P':
                html_content += '<div class="player-circle"></div>'
            elif cell['winner'] == 'B':
                html_content += '<div class="banker-circle"></div>'
            elif cell['winner'] == 'dummy_T': # สำหรับเซลล์ Tie ที่ไม่มี P/B อยู่ในตอนต้น
                 html_content += '<div class="tie-label-cell">T</div>'
            
            # เพิ่มเส้น Tie ถ้า is_tie_line เป็น True และไม่ใช่เซลล์ dummy_T เดี่ยวๆ
            if cell['is_tie_line'] and cell['winner'] != 'dummy_T':
                html_content += '<div class="tie-symbol"></div>'

            # เพิ่มจุดคู่ (Pair) - ปัจจุบัน Pair ไม่ได้ถูกตรวจจับจาก input string
            # หากต้องการให้แสดงผลจุดคู่ ต้องปรับแก้ _build_big_road ให้รับข้อมูล Pair ได้
            if cell['is_player_pair']:
                html_content += '<div class="player-pair-dot"></div>'
            if cell['is_banker_pair']:
                html_content += '<div class="banker-pair-dot"></div>'

            html_content += '</div>' # ปิด div สำหรับแต่ละเซลล์
            
    html_content += "</div>" # ปิด container หลักของ Big Road
    return html_content

# --- ส่วนหลักของ Streamlit App ---
st.set_page_config(layout="wide") # ตั้งค่า layout เป็น "wide" เพื่อให้ Big Road มีพื้นที่แสดงผลมากขึ้น
st.title("SYNAPSE VISION Baccarat Big Road Visualizer")

st.write("ระบบนี้จะแสดงผล Big Road จากประวัติเค้าไพ่ที่ป้อนเข้ามา")

# กล่องข้อความสำหรับให้ผู้ใช้ป้อนประวัติ
history_input = st.text_input(
    "ป้อนประวัติผลลัพธ์ (เช่น PPPPBBBBTBBPPBPPBBPBTBPBP):",
    value="PPPPBBBBTBBPPBPPBBPBTBPBP" # ตัวอย่างประวัติเริ่มต้น
)

if history_input:
    # สร้าง instance ของ OracleEngine
    engine = OracleEngine()
    
    # เรียกใช้ฟังก์ชัน _build_big_road เพื่อรับข้อมูล Big Road
    big_road_data = engine._build_big_road(history_input)
    
    # แสดงผล Big Road ด้วย HTML/CSS
    st.markdown(render_big_road(big_road_data), unsafe_allow_html=True)
else:
    st.info("โปรดป้อนประวัติผลลัพธ์เพื่อแสดง Big Road")

st.markdown("""
<br>
<hr>
<h4>ข้อจำกัดที่สำคัญ:</h4>
<ul>
    <li>การแสดงผลจะเป็นรูปแบบตารางที่สร้างด้วย HTML/CSS ซึ่งอาจจะ <b>ไม่สามารถโต้ตอบได้</b> เหมือนตารางในเว็บคาสิโนจริง</li>
    <li>การแสดงผล "จุดคู่ (Pair)" อาจจะไม่ได้สมบูรณ์แบบเหมือนในตารางจริง เพราะ Streamlit มีข้อจำกัดในการแสดงผลกราฟิกที่ซับซ้อนภายในเซลล์ HTML. 
        และจากรูปแบบประวัติที่ป้อนเข้ามาในปัจจุบัน (เช่น "P", "B", "T") <b>ไม่สามารถระบุข้อมูล Pair ได้</b>. หากต้องการให้แสดง Pair 
        จะต้องมีการปรับปรุงรูปแบบ input string (เช่น "P_P" สำหรับ Player Pair หรือ "B_B" สำหรับ Banker Pair) และปรับ logic ใน 
        <code>_build_big_road</code> เพื่อแยกแยะข้อมูลนี้.</li>
</ul>
""", unsafe_allow_html=True)
