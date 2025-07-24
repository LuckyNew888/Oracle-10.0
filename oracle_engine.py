import random

class OracleEngine:
    def __init__(self):
        self.history = []
        # สถิติประสิทธิภาพของแต่ละ Pattern และ Momentum
        self.pattern_stats = {
            'Pingpong': {'success': 0, 'fail': 0},
            'Two-Cut': {'success': 0, 'fail': 0},
            'Dragon': {'success': 0, 'fail': 0},
            'Triple-Cut': {'success': 0, 'fail': 0},
            'One-Two Pattern': {'success': 0, 'fail': 0},
            'Two-One Pattern': {'success': 0, 'fail': 0},
            'Broken Pattern': {'success': 0, 'fail': 0},
        }
        self.momentum_stats = {
            'B3+ Momentum': {'success': 0, 'fail': 0},
            'P3+ Momentum': {'success': 0, 'fail': 0},
            # เพิ่ม Ladder Momentum หากมีการใช้งาน
        }
        # Memory Logic: เก็บ Pattern ที่เคยทำนายผิดซ้ำ 2 ครั้ง
        self.memory_blocked_patterns = {} # {'pattern_name': {'failures': count, 'last_failed_outcome': 'P'/'B'}}
        
        self.trap_zone_active = False # สถานะ Trap Zone
        self.last_prediction_context = { # เก็บข้อมูลการทำนายครั้งล่าสุดสำหรับ Learning
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False
        }
        self.backtest_results = {'hits': 0, 'misses': 0, 'total': 0, 'drawdown': 0, 'accuracy_pct': 0}
        self.developer_view_components = [] # สำหรับสร้าง Developer View

        # Weights สำหรับ Confidence Engine
        self.pattern_weights = {
            'Pingpong': 1.0, 'Two-Cut': 0.9, 'Dragon': 0.95, 'Triple-Cut': 0.85,
            'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7, 'Broken Pattern': 0.6
        }
        self.momentum_weights = {
            'B3+ Momentum': 1.0, 'P3+ Momentum': 1.0, # ให้ weight สูงเพราะเป็นแรงเหวี่ยงที่ชัดเจน
        }

    def reset_history(self):
        """รีเซ็ตประวัติและสถานะการเรียนรู้ทั้งหมด"""
        self.history = []
        for stats in [self.pattern_stats, self.momentum_stats]:
            for key in stats:
                stats[key] = {'success': 0, 'fail': 0}
        self.memory_blocked_patterns.clear()
        self.trap_zone_active = False
        self.last_prediction_context = {
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False
        }
        self.backtest_results = {'hits': 0, 'misses': 0, 'total': 0, 'drawdown': 0, 'accuracy_pct': 0}
        self.developer_view_components = []

    def _group_outcomes(self, history_data):
        """Helper: จัดกลุ่มผลลัพธ์ที่ติดกัน เช่น P, P, B, B, B -> [PP], [BBB]"""
        if not history_data:
            return []
        
        grouped_outcomes = []
        current_group = []
        
        for item in history_data:
            outcome = item['main_outcome']
            if not current_group:
                current_group.append(outcome)
            elif outcome == current_group[-1]:
                current_group.append(outcome)
            else:
                grouped_outcomes.append(''.join(current_group))
                current_group = [outcome]
        
        if current_group: # Add the last group
            grouped_outcomes.append(''.join(current_group))
            
        return grouped_outcomes

    # --- 🧬 DNA Pattern Analysis ---
    def detect_dna_patterns(self, history_segment):
        """
        ตรวจจับรูปแบบ DNA เช่น Dragon, Pingpong, Two-Cut
        """
        patterns = []
        if len(history_segment) < 4: # ต้องการประวัติอย่างน้อย 4 ตาสำหรับรูปแบบเบื้องต้น
            return patterns

        seq_str = ''.join([item['main_outcome'] for item in history_segment])
        
        # Pingpong (B-P-B-P) - ต้องมีอย่างน้อย 4 ตัวขึ้นไป
        if len(seq_str) >= 4:
            if seq_str[-4:] == 'PBPB' or seq_str[-4:] == 'BPBP':
                patterns.append('Pingpong')
            elif len(seq_str) >= 6 and (seq_str[-6:] == 'PBPBPB' or seq_str[-6:] == 'BPBPBP'):
                 patterns.append('Pingpong') # Stronger pingpong

        # Dragon (BBBBB...) - ต้องมีอย่างน้อย 4 ตัวขึ้นไป
        if len(seq_str) >= 4:
            if seq_str.endswith('BBBB') or seq_str.endswith('PPPP'):
                patterns.append('Dragon')

        # Two-Cut (BB-PP-BB-PP)
        if len(seq_str) >= 4:
            if seq_str.endswith('BBPP') or seq_str.endswith('PPBB'):
                patterns.append('Two-Cut')
        
        # Triple-Cut (BBB-PPP)
        if len(seq_str) >= 6:
            if seq_str.endswith('BBBPPP') or seq_str.endswith('PPPBBB'):
                patterns.append('Triple-Cut')
        
        # One-Two Pattern (PBB / BPP)
        if len(seq_str) >= 3:
            if seq_str.endswith('PBB') or seq_str.endswith('BPP'):
                patterns.append('One-Two Pattern')
        
        # Two-One Pattern (PPB / BBP)
        if len(seq_str) >= 3:
            if seq_str.endswith('PPB') or seq_str.endswith('BBP'):
                patterns.append('Two-One Pattern')
        
        # Broken Pattern (BPBPPBP) - การเปลี่ยนแปลงที่รวดเร็วหรือแตกแถว
        # ตรวจสอบรูปแบบสลับที่คาดว่าจะกลับมาเป็นปกติ
        if len(history_segment) >= 5:
            last_5 = [item['main_outcome'] for item in history_segment[-5:]]
            # Ex: PBBPP, PPBBP - indicating a broken streak/pattern
            if (last_5 == ['P','B','B','P','P'] or last_5 == ['B','P','P','B','B'] or
                last_5 == ['P','P','B','B','P'] or last_5 == ['B','B','P','P','B']):
                patterns.append('Broken Pattern')

        return patterns

    # --- 🚀 Momentum Tracker ---
    def detect_momentum(self, history_segment):
        """
        ตรวจสอบแรงเหวี่ยง B3+, P3+
        """
        momentum = []
        if len(history_segment) < 3:
            return momentum

        last_outcome = history_segment[-1]['main_outcome']
        streak_count = 1
        for i in range(len(history_segment) - 2, -1, -1):
            if history_segment[i]['main_outcome'] == last_outcome:
                streak_count += 1
            else:
                break
        
        if streak_count >= 3:
            momentum.append(f"{last_outcome}{streak_count}+ Momentum") # B3+ Momentum, P4+ Momentum etc.
        
        # Ladder Momentum (BB-P-BBB-P-BBBB) - ซับซ้อนมาก, require Big Road visualization
        # สำหรับการตรวจจับแบบ linear จะทำได้ยาก
        # เช่น history = BBB P BBB P BBBB
        # current_groups = self._group_outcomes(history_segment)
        # if len(current_groups) >= 3:
        #     # Simplified check: streaks growing with single interruptions
        #     # Example: ['BB', 'P', 'BBB', 'P', 'BBBB']
        #     # This requires more robust pattern recognition than simple string matching
        #     pass 

        return momentum

    # --- ⚠️ Trap Zone Detection ---
    def detect_trap_zone(self, history_segment):
        """
        ตรวจจับโซนอันตราย (Zone เปลี่ยนเร็ว)
        """
        self.trap_zone_active = False
        if len(history_segment) < 2:
            return

        last_2 = ''.join([item['main_outcome'] for item in history_segment[-2:]])
        last_4 = ''.join([item['main_outcome'] for item in history_segment[-4:]])
        last_5 = ''.join([item['main_outcome'] for item in history_segment[-5:]])

        # P1-B1, B1-P1 (ไม่เสถียร)
        if last_2 == 'PB' or last_2 == 'BP':
            self.trap_zone_active = True
            self.developer_view_components.append("⚠️ Trap: P1-B1/B1-P1 (ไม่เสถียร)")
            return

        # B3-P1 หรือ P3-B1 → เสี่ยงกลับตัว
        if len(history_segment) >= 4:
            if (last_4 == 'BBBP' or last_4 == 'PPPB'):
                self.trap_zone_active = True
                self.developer_view_components.append("⚠️ Trap: B3-P1/P3-B1 (เสี่ยงกลับตัว)")
                return
        
        # Pingpong (PBPB) - หาก Pingpong แตก หรือมีการสลับที่รวดเร็ว
        # ตรวจสอบว่ามี Pingpong pattern แต่แล้วมีแนวโน้มจะกลับด้าน (เช่น PBPB P B)
        # ตรวจจับ PBPBP หรือ BPBPB ที่ยาวแล้วเกิดการสลับอีกครั้งทันที
        if len(history_segment) >= 5:
            if (last_5 == 'PBPBP' or last_5 == 'BPBPB'): # ถ้ามี Pingpong ยาวๆ
                # และเกิดการสลับอีกครั้ง
                if len(history_segment) >= 6 and (history_segment[-6]['main_outcome'] == last_5[0]):
                    self.trap_zone_active = True
                    self.developer_view_components.append("⚠️ Trap: Pingpong Breaking")
                    return


    # --- 🎯 Confidence Engine ---
    def calculate_confidence(self, patterns, momentum):
        """
        ระบบประเมินความมั่นใจจากความถี่รูปแบบซ้ำ, Momentum เสถียรหรือไม่, Trap Zone มีหรือไม่
        """
        total_score = 0
        total_weight_sum = 0

        # จาก DNA Patterns
        for p_name in patterns:
            if p_name in self.pattern_stats:
                stats = self.pattern_stats[p_name]
                if (stats['success'] + stats['fail']) > 0:
                    success_rate = stats['success'] / (stats['success'] + stats['fail'])
                    total_score += success_rate * self.pattern_weights.get(p_name, 0.5)
                else: # ไม่เคยเกิด ให้ค่าเริ่มต้น
                    total_score += self.pattern_weights.get(p_name, 0.5)
                total_weight_sum += self.pattern_weights.get(p_name, 0.5)

        # จาก Momentum
        for m_name in momentum:
            if m_name in self.momentum_stats:
                stats = self.momentum_stats[m_name]
                if (stats['success'] + stats['fail']) > 0:
                    success_rate = stats['success'] / (stats['success'] + stats['fail'])
                    total_score += success_rate * self.momentum_weights.get(m_name, 0.5)
                else:
                    total_score += self.momentum_weights.get(m_name, 0.5)
                total_weight_sum += self.momentum_weights.get(m_name, 0.5)

        # หากไม่มี Pattern หรือ Momentum ที่ตรวจจับได้เลย
        if total_weight_sum == 0:
            confidence = 50 # Default confidence if no patterns/momentum
        else:
            confidence = (total_score / total_weight_sum) * 100
        
        # ลด Confidence หากอยู่ใน Trap Zone
        if self.trap_zone_active:
            confidence *= 0.5 # ลดลง 50%
            self.developer_view_components.append(f"Confidence reduced by Trap Zone.")

        return round(confidence)

    # --- 🔁 Memory Logic ---
    def apply_memory_logic(self, current_prediction_candidate, active_patterns, active_momentum):
        """
        จดจำ Pattern ที่เคยพลาดในห้องเดียวกัน และไม่ใช้ซ้ำ Pattern เดิมที่ทำให้พลาด ≥ 2 ครั้ง
        คืนค่าเป็น None หากถูก Memory Logic บล็อก หรือคืนค่าเดิมหากไม่ถูกบล็อก
        """
        relevant_patterns = active_patterns + active_momentum
        
        for pattern_name in relevant_patterns:
            if pattern_name in self.memory_blocked_patterns:
                failures_count = self.memory_blocked_patterns[pattern_name]['failures']
                # last_failed_outcome = self.memory_blocked_patterns[pattern_name]['last_failed_outcome']
                
                # หาก Pattern นี้เคยทำให้พลาด ≥ 2 ครั้ง และกำลังจะทำนายเหมือนเดิม
                # (สมมติว่า memory logic บล็อก pattern นั้นๆ ไม่ว่าจะทำนายอะไรก็ตามจาก pattern นั้น)
                if failures_count >= 2:
                    self.developer_view_components.append(f"Memory Logic: Pattern '{pattern_name}' blocked (Failures: {failures_count})")
                    return None # บล็อกการทำนายที่มาจาก Pattern นี้

        return current_prediction_candidate

    # --- 🧠 Intuition Logic ---
    def apply_intuition_logic(self, history_segment):
        """
        หากไม่มี Pattern เด่น → ใช้ตรรกะขั้นสูง เช่น PBP → P
        """
        if len(history_segment) < 3:
            return None

        seq_str = ''.join([item['main_outcome'] for item in history_segment[-5:]]) # ดู 5 ตาหลัง

        # PBP → P (Double Confirmed)
        if seq_str.endswith('PBP'):
            self.developer_view_components.append("Intuition: PBP -> P")
            return 'P'
        
        # BBPBB → B (Reverse Trap) - ควรจะเป็น B-B-P-B-B
        if seq_str.endswith('BBPBB'):
            self.developer_view_components.append("Intuition: BBPBB -> B")
            return 'B'

        # 2P1B2P → P (Zone Flow) - ควรจะเป็น P-P-B-P-P
        if seq_str.endswith('PPBPP'):
            self.developer_view_components.append("Intuition: PPBPP -> P")
            return 'P'
        
        # Steady Repeat: (PBPBPBP → จะกลับมาที่ P) - ถ้าเป็น Pingpong ยาวๆ แล้วถึงจุดที่คาดว่า Pingpong จะจบแล้วจะออกอะไร
        # ถ้ามี PBPBPB (6 ตา) และกำลังจะออก B แต่คาดว่าจะเป็น P
        if len(history_segment) >= 6:
            last_6 = ''.join([item['main_outcome'] for item in history_segment[-6:]])
            if last_6 == 'PBPBPB' and history_segment[-1]['main_outcome'] == 'B':
                self.developer_view_components.append("Intuition: Steady Repeat (PBPBPB)")
                return 'P' # คาดว่าจะกลับมาที่ P
            elif last_6 == 'BPBPBP' and history_segment[-1]['main_outcome'] == 'P':
                self.developer_view_components.append("Intuition: Steady Repeat (BPBPBP)")
                return 'B' # คาดว่าจะกลับมาที่ B

        return None # ไม่มี Intuition ที่ชัดเจน

    # --- 🔬 Backtest Simulation ---
    def _run_backtest_simulation(self):
        """
        ทดสอบผลย้อนหลังมือ #11–ปัจจุบัน คำนวณ Hit / Miss % และ Drawdown
        """
        hits = 0
        misses = 0
        current_drawdown = 0
        max_drawdown = 0
        
        # เริ่ม Backtest ตั้งแต่มือที่ 11
        if len(self.history) < 11:
            return {'hits': 0, 'misses': 0, 'total': 0, 'drawdown': 0, 'accuracy_pct': 0}

        # ใช้ slice ของ history สำหรับ backtest
        # จำลองการทำนายบนข้อมูลย้อนหลัง โดยใช้ logic เดียวกับ predict_next
        # แต่ไม่ได้อัปเดต state ของ OracleEngine จริงๆ
        # เนื่องจาก _update_learning จะถูกเรียกจาก add_result ใน live prediction
        
        # สำหรับ Backtest, เราจะใช้ simplified logic ในการทำนายเพื่อประเมิน accuracy
        # ไม่ได้จำลองการเรียนรู้ของ engine ใน backtest loop
        
        for i in range(10, len(self.history)): # เริ่มจาก index 10 (มือที่ 11)
            segment = self.history[:i] # ประวัติที่ใช้ทำนายถึงมือปัจจุบัน
            
            # ต้องจำลองการทำนายแบบเดียวกับ predict_next แต่ไม่มีการอัปเดต _update_learning
            # เพื่อไม่ให้ backtest ไปกระทบสถานะปัจจุบันของ engine
            
            # Simplified prediction for backtest:
            patterns = self.detect_dna_patterns(segment)
            momentum = self.detect_momentum(segment)
            
            simulated_prediction = '?'
            if patterns or momentum:
                last_outcome = segment[-1]['main_outcome']
                if 'Dragon' in patterns:
                    simulated_prediction = last_outcome
                elif 'Pingpong' in patterns:
                    simulated_prediction = 'B' if last_outcome == 'P' else 'P'
                elif 'B3+ Momentum' in momentum and last_outcome == 'B':
                    simulated_prediction = 'B'
                elif 'P3+ Momentum' in momentum and last_outcome == 'P':
                    simulated_prediction = 'P'
                elif 'Two-Cut' in patterns: # Two-Cut typically suggests continuation
                    simulated_prediction = last_outcome
                elif 'Triple-Cut' in patterns: # Triple-Cut typically suggests continuation
                    simulated_prediction = last_outcome
                else:
                    simulated_prediction = random.choice(['P', 'B']) # Fallback if no specific pattern for backtest
            else:
                simulated_prediction = random.choice(['P', 'B']) # Fallback for backtest
            
            actual_outcome = self.history[i]['main_outcome']

            if simulated_prediction != '?' and simulated_prediction == actual_outcome:
                hits += 1
                current_drawdown = 0 # Reset drawdown on hit
            elif simulated_prediction != '?' and actual_outcome != 'T' and simulated_prediction != actual_outcome:
                misses += 1
                current_drawdown += 1
            
            max_drawdown = max(max_drawdown, current_drawdown)

        total_games = hits + misses
        accuracy_pct = (hits / total_games * 100) if total_games > 0 else 0

        self.backtest_results = {
            'hits': hits,
            'misses': misses,
            'total': total_games,
            'drawdown': max_drawdown,
            'accuracy_pct': round(accuracy_pct, 1)
        }
        return self.backtest_results

    # --- การอัปเดตการเรียนรู้ (เมื่อทราบผลลัพธ์จริง) ---
    def _update_learning(self, actual_outcome):
        """
        อัปเดตสถิติและ Memory Logic จากผลการทำนายครั้งล่าสุด
        """
        predicted_outcome = self.last_prediction_context['prediction']
        patterns_detected = self.last_prediction_context['patterns']
        momentum_detected = self.last_prediction_context['momentum']

        if predicted_outcome != '?' and actual_outcome != 'T': # ไม่นับผลเสมอในการเรียนรู้
            if predicted_outcome == actual_outcome:
                # ทำนายถูก: อัปเดต success count
                for p_name in patterns_detected:
                    if p_name in self.pattern_stats:
                        self.pattern_stats[p_name]['success'] += 1
                for m_name in momentum_detected:
                    if m_name in self.momentum_stats:
                        self.momentum_stats[m_name]['success'] += 1
                # หากเคยถูกบล็อกด้วย Memory Logic, อาจจะ reset counter หรือลดค่าลง
                # (สำหรับเวอร์ชั่นนี้ เราจะยังไม่ลดค่า เพื่อให้มัน "จำ" ได้นานขึ้น)
            else:
                # ทำนายผิด: อัปเดต fail count และ Memory Logic
                for p_name in patterns_detected:
                    if p_name in self.pattern_stats:
                        self.pattern_stats[p_name]['fail'] += 1
                        self.memory_blocked_patterns.setdefault(p_name, {'failures': 0, 'last_failed_outcome': predicted_outcome})['failures'] += 1
                        self.memory_blocked_patterns[p_name]['last_failed_outcome'] = predicted_outcome
                for m_name in momentum_detected:
                    if m_name in self.momentum_stats:
                        self.momentum_stats[m_name]['fail'] += 1
                        self.memory_blocked_patterns.setdefault(m_name, {'failures': 0, 'last_failed_outcome': predicted_outcome})['failures'] += 1
                        self.memory_blocked_patterns[m_name]['last_failed_outcome'] = predicted_outcome

    def add_result(self, main_outcome, big_road_column=None):
        """
        เพิ่มผลลัพธ์ใหม่ และเรียกใช้ _update_learning จากการทำนายครั้งก่อน
        """
        # อัปเดตการเรียนรู้ก่อนเพิ่มผลลัพธ์ใหม่
        if self.last_prediction_context['prediction'] != '?':
            self._update_learning(main_outcome)
        
        # เพิ่มผลลัพธ์ใหม่เข้าในประวัติ
        self.history.append({'main_outcome': main_outcome, 'big_road_column': big_road_column})
        # หลังจากเพิ่มผลลัพธ์ ก็ clear last_prediction_context เพื่อให้พร้อมสำหรับ prediction ใหม่
        self.last_prediction_context = { 
            'prediction': '?',
            'patterns': [],
            'momentum': [],
            'intuition_applied': False
        }

    # --- Core Prediction Engine ---
    def predict_next(self):
        """
        ประมวลผลการทำนายผลลัพธ์ถัดไปตามระบบ SYNAPSE VISION Baccarat 7 ขั้นตอน
        """
        self.developer_view_components = [] # Reset developer view for this prediction cycle
        
        # 1. รับ Input จากผู้ใช้ (ต้องมีประวัติอย่างน้อย 20 ตา)
        if len(self.history) < 20:
            return {
                'prediction': '?',
                'recommendation': 'Avoid ❌',
                'risk': 'Not enough data',
                'accuracy': 'N/A',
                'developer_view': 'กรุณาใส่ผลย้อนหลังอย่างน้อย 20 ตา'
            }

        history_segment = self.history[-30:] # วิเคราะห์จาก 30 ตาหลังสุด

        # 2. 🧬 DNA Pattern Analysis
        patterns_detected = self.detect_dna_patterns(history_segment)
        self.developer_view_components.append(f"DNA Patterns: {', '.join(patterns_detected) if patterns_detected else 'None'}")

        # 3. 🚀 Momentum Tracker
        momentum_detected = self.detect_momentum(history_segment)
        self.developer_view_components.append(f"Momentum: {', '.join(momentum_detected) if momentum_detected else 'None'}")

        # 4. ⚠️ Trap Zone Detection
        self.detect_trap_zone(history_segment) # จะตั้งค่า self.trap_zone_active และเพิ่มข้อความลง dev_view_components เอง

        # 5. 🎯 Confidence Engine
        confidence = self.calculate_confidence(patterns_detected, momentum_detected)
        self.developer_view_components.append(f"Confidence: {confidence}%")

        # กำหนดค่าเริ่มต้นการทำนาย
        prediction = '?'
        recommendation = 'Avoid ❌'
        risk = 'Normal'
        intuition_applied = False

        # ตัดสินใจทำนายตาม Confidence
        if confidence >= 60:
            last_outcome = self.history[-1]['main_outcome']
            
            # --- กลยุทธ์การทำนายหลัก (ตามลำดับความสำคัญ) ---
            # Dragon (ลากยาว)
            if 'Dragon' in patterns_detected:
                prediction = last_outcome
                self.developer_view_components.append(f"Predict by: Dragon ({last_outcome} continuation)")
            # Momentum 3+ (แรงเหวี่ยง)
            elif f"{last_outcome}3+ Momentum" in momentum_detected:
                prediction = last_outcome
                self.developer_view_components.append(f"Predict by: Momentum ({last_outcome} continuation)")
            # Pingpong (สลับ)
            elif 'Pingpong' in patterns_detected:
                prediction = 'B' if last_outcome == 'P' else 'P'
                self.developer_view_components.append(f"Predict by: Pingpong (Opposite of {last_outcome})")
            # Two-Cut (สองตัด)
            elif 'Two-Cut' in patterns_detected:
                prediction = last_outcome # คาดว่าจะออกซ้ำชุดที่สอง
                self.developer_view_components.append(f"Predict by: Two-Cut ({last_outcome} continuation)")
            # Triple-Cut (สามตัด)
            elif 'Triple-Cut' in patterns_detected:
                prediction = last_outcome # คาดว่าจะออกซ้ำชุดที่สอง
                self.developer_view_components.append(f"Predict by: Triple-Cut ({last_outcome} continuation)")
            # One-Two Pattern
            elif 'One-Two Pattern' in patterns_detected:
                # PBB -> P, BPP -> B (predicts the single opposite)
                if len(history_segment) >= 3:
                    if history_segment[-3]['main_outcome'] == 'P' and history_segment[-2]['main_outcome'] == 'B' and last_outcome == 'B':
                        prediction = 'P'
                    elif history_segment[-3]['main_outcome'] == 'B' and history_segment[-2]['main_outcome'] == 'P' and last_outcome == 'P':
                        prediction = 'B'
                    else: prediction = random.choice(['P', 'B']) # Fallback if not clear or not this exact pattern
                else: prediction = random.choice(['P', 'B'])
                self.developer_view_components.append(f"Predict by: One-Two Pattern ({prediction})")
            # Two-One Pattern
            elif 'Two-One Pattern' in patterns_detected:
                # PPB -> P, BBP -> B (predicts continuation of the pair)
                if len(history_segment) >= 3:
                    if history_segment[-3]['main_outcome'] == 'P' and history_segment[-2]['main_outcome'] == 'P' and last_outcome == 'B':
                        prediction = 'P'
                    elif history_segment[-3]['main_outcome'] == 'B' and history_segment[-2]['main_outcome'] == 'B' and last_outcome == 'P':
                        prediction = 'B'
                    else: prediction = random.choice(['P', 'B']) # Fallback if not clear or not this exact pattern
                else: prediction = random.choice(['P', 'B'])
                self.developer_view_components.append(f"Predict by: Two-One Pattern ({prediction})")
            # หากไม่มี Pattern ชัดเจน แต่ Confidence สูงพอ ให้ลองใช้ Intuition
            else:
                intuition_pred = self.apply_intuition_logic(history_segment)
                if intuition_pred:
                    prediction = intuition_pred
                    intuition_applied = True
                else:
                    prediction = random.choice(['P', 'B']) # Fallback หากไม่มีอะไรชัดเจน
                    self.developer_view_components.append("Predict by: Random Fallback (No strong pattern/intuition)")
            
            # 6. 🔁 Memory Logic: ตรวจสอบว่าการทำนายนี้ถูกบล็อกหรือไม่
            original_prediction = prediction
            prediction_after_memory = self.apply_memory_logic(prediction, patterns_detected, momentum_detected)
            
            if prediction_after_memory is None: # หากถูก Memory Logic บล็อก
                self.developer_view_components.append(f"Memory Logic Blocked: Original '{original_prediction}' rejected.")
                # ลองใช้ Intuition Logic อีกครั้ง
                intuition_pred = self.apply_intuition_logic(history_segment)
                if intuition_pred and intuition_pred != original_prediction: # ต้องไม่เป็นผลเดิมที่ถูกบล็อก
                    prediction = intuition_pred
                    intuition_applied = True
                    self.developer_view_components.append(f"Memory Logic: Fallback to Intuition ({prediction}).")
                else:
                    # หาก Intuition ก็ไม่ได้ หรือได้ผลเดิมที่ถูกบล็อก, ให้สุ่ม P/B
                    prediction = random.choice(['P', 'B']) 
                    if prediction == original_prediction and original_prediction != '?': # ถ้าสุ่มได้อันที่ถูกบล็อกอีก
                         prediction = 'B' if original_prediction == 'P' else 'P' # สลับไปอีกฝั่งแทน
                    self.developer_view_components.append(f"Memory Logic: Fallback to {prediction} after block.")
                risk = 'Memory Rejection' # เปลี่ยน Risk level
            else:
                prediction = prediction_after_memory # Use the prediction passed through memory logic

            # กำหนด Recommendation หลังจาก Memory Logic
            if prediction in ['P', 'B']:
                recommendation = 'Play ✅'
                if intuition_applied:
                    self.developer_view_components.append("Intuition Logic Applied.")
            else:
                recommendation = 'Avoid ❌'
                risk = 'Low Confidence / Undetermined'

        else: # Confidence < 60%
            prediction = '⚠️' # ใช้ ⚠️ เพื่อบ่งบอกว่าไม่ควรเล่น
            recommendation = 'Avoid ❌'
            risk = 'Low Confidence'
            self.developer_view_components.append("Confidence < 60%. Not playing.")
        
        # 7. 🔬 Backtest Simulation
        backtest_results = self._run_backtest_simulation()
        backtest_accuracy_str = f"{backtest_results['accuracy_pct']}% ({backtest_results['hits']}/{backtest_results['total']})"
        self.developer_view_components.append(f"Backtest Accuracy: {backtest_accuracy_str}")
        
        # ตรวจสอบ Drawdown
        if backtest_results['drawdown'] >= 3:
            risk = 'Drawdown Alert'
            recommendation = 'Avoid ❌'
            self.developer_view_components.append(f"Drawdown Alert! (Max Drawdown: {backtest_results['drawdown']})")

        # ตรวจสอบ Trap Zone สุดท้าย
        if self.trap_zone_active:
            risk = 'Trap Zone'
            recommendation = 'Avoid ❌'
            self.developer_view_components.append("Final Risk: Trap Zone Detected.")


        # จัดรูปแบบ Developer View
        grouped_outcomes_str = ', '.join([f"[{g}]" for g in self._group_outcomes(history_segment)])
        final_dev_view = f"{grouped_outcomes_str}; {'; '.join(self.developer_view_components)}"

        # เก็บ context สำหรับการเรียนรู้ครั้งถัดไป
        self.last_prediction_context = {
            'prediction': prediction,
            'patterns': patterns_detected,
            'momentum': momentum_detected,
            'intuition_applied': intuition_applied
        }

        # ✅ โครงสร้างผลลัพธ์ของระบบ
        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'accuracy': backtest_accuracy_str,
            'developer_view': final_dev_view
        }
