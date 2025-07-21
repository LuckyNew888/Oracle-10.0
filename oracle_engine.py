# oracle_engine.py

class OracleEngine:
    def __init__(self):
        # คุณสามารถเพิ่มการเริ่มต้นตัวแปรอื่นๆ ของ OracleEngine ได้ที่นี่
        pass

    def _build_big_road(self, history, max_rows=6):
        """
        สร้างโครงสร้างข้อมูล Big Road จากสตริงประวัติผลลัพธ์ (P, B, T).

        Args:
            history (str): สตริงของผลลัพธ์ (เช่น "PPPPBBBBTBBPPBPPBBPBTBPBP").
                           ณ ตอนนี้รองรับเฉพาะ 'P', 'B', 'T'.
                           ข้อมูล Pair (Player Pair / Banker Pair) ไม่ได้ถูกแยกออกมาจากรูปแบบสตริงนี้โดยตรง
                           ดังนั้น 'is_player_pair' และ 'is_banker_pair' จะเป็น False เสมอ.
                           หากต้องการให้รองรับ Pair จะต้องมีการปรับปรุงรูปแบบ input history (เช่น "P_PP", "B_BP").
            max_rows (int): จำนวนแถวสูงสุดก่อนที่จะเกิดการ 'ตวัดหาง' (tailing) (มาตรฐานคือ 6).

        Returns:
            list: ลิสต์ 2 มิติ (grid[row][col]) ที่แสดงถึง Big Road,
                  โดยแต่ละเซลล์เป็น dictionary ที่มี 'winner', 'is_tie_line',
                  'is_player_pair', 'is_banker_pair'.
                  เซลล์ว่างจะถูกแทนด้วย {'winner': '', 'is_tie_line': False, ...}.
        """
        grid = [[]]  # ลิสต์ของคอลัมน์ โดยแต่ละคอลัมน์เป็นลิสต์ของ dictionary เซลล์
        current_col_idx = 0
        current_row_idx = 0
        last_main_winner = None  # 'P' หรือ 'B' ใช้สำหรับตรวจจับการเปลี่ยนฝั่ง

        # ลิสต์เก็บ reference ไปยังเซลล์ P/B เพื่อใช้สำหรับเพิ่มเส้น Tie ในภายหลัง
        # นี่เป็นสิ่งสำคัญเพราะ Tie จะแสดงผลทับบนเซลล์ P/B ก่อนหน้า
        pb_cells_history_refs = []

        # ตรวจสอบและเริ่มต้นคอลัมน์แรกหากยังว่างอยู่
        # เพื่อรองรับกรณีที่ Big Road เริ่มต้นด้วย Tie (ซึ่งควรจะแสดงผลในเซลล์ (0,0) ได้)
        if not grid[current_col_idx]:
            grid[current_col_idx] = []

        for result_char in history:
            if result_char == 'T':
                # จัดการ Tie: หากมีเซลล์ P/B ก่อนหน้า ให้เพิ่มเส้น Tie ไปยังเซลล์นั้น
                if pb_cells_history_refs:
                    pb_cells_history_refs[-1]['is_tie_line'] = True
                else:
                    # หากผลลัพธ์แรกสุดคือ 'T' และไม่มี P/B เลย
                    # เราจะสร้างเซลล์ 'dummy_T' เพื่อให้ Tie สามารถปรากฏที่จุดเริ่มต้นของ Big Road ได้
                    # (นี่เป็นการประนีประนอมเพื่อการแสดงผล visual ใน Big Road ที่ปกติ Tie จะไม่เริ่มคอลัมน์ใหม่)
                    if not grid[0] or (grid[0][0].get('winner') != 'dummy_T' and not grid[0][0].get('is_tie_line')):
                        dummy_tie_cell = {'winner': 'dummy_T', 'is_tie_line': True, 'is_player_pair': False, 'is_banker_pair': False}
                        grid[0].insert(0, dummy_tie_cell)
                        # หลังจากใส่ dummy T ที่ (0,0) หากมี P/B ถัดมา จะเริ่มที่แถว 1 ในคอลัมน์เดิม
                        if len(grid[0]) > 0 and grid[0][0]['winner'] == 'dummy_T':
                            current_row_idx = 1
                continue  # 'T' ไม่ได้ทำให้คอลัมน์หรือแถวสำหรับผลลัพธ์ P/B ถัดไปเปลี่ยนแปลง

            # หากผลลัพธ์เป็น 'P' หรือ 'B'
            cell = {
                'winner': result_char,
                'is_tie_line': False,
                'is_player_pair': False,  # ปัจจุบันไม่รองรับการตรวจจับ Pair จาก input string
                'is_banker_pair': False   # ปัจจุบันไม่รองรับการตรวจจับ Pair จาก input string
            }

            if last_main_winner is None:
                # นี่คือผลลัพธ์ P หรือ B แรกสุดใน Big Road
                grid[current_col_idx].append(cell)
                current_row_idx = 0  # แถวเริ่มต้นสำหรับผลลัพธ์แรกสุด
                last_main_winner = result_char
            elif result_char == last_main_winner:
                # ผลลัพธ์เหมือนเดิม ('P' ต่อ 'P' หรือ 'B' ต่อ 'B'): ลงไปด้านล่างในคอลัมน์ปัจจุบัน
                if current_row_idx < max_rows - 1:
                    current_row_idx += 1
                    grid[current_col_idx].append(cell)
                else:
                    # ตวัดหาง (Tailing): จำนวนแถวสูงสุด (max_rows) ถูกเติมเต็มแล้ว
                    # ให้ย้ายไปคอลัมน์ถัดไปในแถวเดิม (แถวสุดท้ายของคอลัมน์ที่แล้ว)
                    current_col_idx += 1
                    # ตรวจสอบให้แน่ใจว่าคอลัมน์ใหม่มีอยู่และถูกเตรียมพร้อมไว้
                    while len(grid) <= current_col_idx:
                        grid.append([]) # เพิ่มคอลัมน์ว่างใหม่

                    # เติมเซลล์ว่างในคอลัมน์ก่อนหน้า (ถ้ามี) เพื่อให้การจัดตำแหน่งแนวนอนถูกต้องสำหรับการตวัดหาง
                    # ทำให้แน่ใจว่าทุกคอลัมน์ก่อนหน้าคอลัมน์ปัจจุบัน มีความสูงอย่างน้อยเท่ากับแถวที่เกิดการตวัดหาง
                    for col_to_fill in range(current_col_idx):
                        while len(grid[col_to_fill]) <= current_row_idx:
                            grid[col_to_fill].append({'winner': '', 'is_tie_line': False, 'is_player_pair': False, 'is_banker_pair': False})
                    
                    grid[current_col_idx].append(cell)
                    # current_row_idx ยังคงอยู่ที่ max_rows - 1 สำหรับการตวัดหาง (คือแถวสุดท้าย)
            else:
                # ผลลัพธ์เปลี่ยนฝั่ง ('P' เป็น 'B' หรือ 'B' เป็น 'P'): เริ่มคอลัมน์ใหม่
                current_col_idx += 1
                current_row_idx = 0 # กลับไปเริ่มที่แถวแรกของคอลัมน์ใหม่
                while len(grid) <= current_col_idx:
                    grid.append([]) # เพิ่มคอลัมน์ว่างใหม่
                grid[current_col_idx].append(cell)
                last_main_winner = result_char
            
            pb_cells_history_refs.append(cell) # เก็บ reference ของเซลล์ P/B นี้ไว้สำหรับ Tie ในอนาคต

        # ปรับ Grid ให้เป็นโครงสร้างสี่เหลี่ยมผืนผ้าเพื่อการแสดงผลที่สอดคล้องกันใน HTML Grid
        # กำหนดจำนวนคอลัมน์ทั้งหมดที่ถูกใช้
        max_cols_final = len(grid)
        
        # สร้าง Grid ใหม่ที่เต็มทุกช่องด้วยเซลล์ว่างเริ่มต้น
        # ขนาดจะอยู่ที่ max_rows x max_cols_final
        normalized_grid = [[{'winner': '', 'is_tie_line': False, 'is_player_pair': False, 'is_banker_pair': False} for _ in range(max_cols_final)] for _ in range(max_rows)]

        # คัดลอกข้อมูลเซลล์จาก Grid ที่สร้างไว้ (ซึ่งอาจจะไม่ใช่สี่เหลี่ยมผืนผ้าในตอนแรก)
        # ไปยัง normalized_grid เพื่อให้แน่ใจว่าทุกช่องมีการระบุข้อมูล (ว่างหรือไม่ว่าง)
        for c_idx, column_data in enumerate(grid):
            for r_idx, cell_data in enumerate(column_data):
                if r_idx < max_rows: # ตรวจสอบไม่ให้เกินจำนวนแถวสูงสุดที่เราต้องการแสดงผล
                    normalized_grid[r_idx][c_idx] = cell_data

        return normalized_grid
