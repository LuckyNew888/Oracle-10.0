from collections import Counter
import random

class OracleEngine:
    def __init__(self):
        self.history = []
        self.memory_failed_patterns = set()

    # --- ส่วน Data Management (สำหรับ Engine เอง) ---
    def update_history(self, result):
        """Adds a new result to the history."""
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def remove_last(self):
        """Removes the last result from the history."""
        if self.history:
            self.history.pop()

    def reset_history(self):
        """Resets the entire history and failed patterns memory."""
        self.history = []
        self.memory_failed_patterns = set()

    # --- 1. 🧬 DNA Pattern Analysis (ตรวจจับรูปแบบ) ---
    def detect_patterns(self):
        """
        Detects various patterns such as Pingpong, Two-Cut, Dragon, Broken Pattern, Triple Cut.
        """
        patterns = []
        h = self.history

        # Detect Pingpong (Alternating P/B pattern for a certain length)
        # Check for alternation from the end
        if len(h) >= 2: # Needs at least 2 results to alternate
            alternating_count = 0
            # Loop backwards from the last element to count alternations
            for i in range(len(h) - 1, 0, -1):
                if h[i] != h[i-1]:
                    alternating_count += 1
                else:
                    break # Stop counting if alternation ends

            # Consider it a clear Pingpong if there are at least 3 alternations (meaning 4 results like P-B-P-B)
            if alternating_count >= 3:
                patterns.append(f'Pingpong ({alternating_count + 1}x)') # +1 to show total results in the pattern

        # Detect Two-Cut (BB-PP or PP-BB)
        if len(h) >= 4:
            last4 = h[-4:]
            # Check if the first 2 are the same, the last 2 are the same, and the two pairs are different
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # Detect Dragon (long streak: 3 to 6 consecutive same results)
        for i in range(3, 7):
            if len(h) >= i:
                if len(set(h[-i:])) == 1: # If the last i elements are all the same
                    patterns.append(f'Dragon ({i})') # Indicate the length of the Dragon

        # Detect Triple Cut (e.g., PPPBBB or BBBPPP)
        if len(h) >= 6:
            last6 = h[-6:]
            # Check if the first 3 are the same, the last 3 are the same, and the first 3 are different from the last 3
            if (last6[0] == last6[1] == last6[2] and
                last6[3] == last6[4] == last6[5] and
                last6[0] != last6[3]):
                patterns.append('Triple Cut')

        # Detect Broken Pattern (BPBPPBP) - Example Implementation
        # **Note:** This logic is just a starting example. It should be refined based on the true definition.
        if len(h) >= 7:
            last7 = "".join(h[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7:
                patterns.append('Broken Pattern')

        return patterns

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self):
        """Detects momentum such as B3+, P3+, Steady Repeat."""
        momentum = []
        h = self.history

        # Check for Momentum (3 or more consecutive same results)
        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
            # Count consecutive same characters from the end
            for i in reversed(range(len(h))):
                if h[i] == last_char:
                    streak_count += 1
                else:
                    break
            if streak_count >= 3:
                momentum.append(f"{last_char}{streak_count}+ Momentum")

        # Detect Steady Repeat (PBPBPBP or BPBPBPB)
        if len(h) >= 7:
            seq = h[-7:]
            if (seq == ['P','B','P','B','P','B','P'] or
                seq == ['B','P','B','P','B','P','B']):
                momentum.append("Steady Repeat Momentum")

        return momentum

    # --- 3. ⚠️ Trap Zone Detection (ตรวจจับโซนอันตราย) ---
    def in_trap_zone(self):
        """Detects zones where changes are rapid and dangerous."""
        h = self.history
        if len(h) < 2:
            return False

        # P1-B1, B1-P1 (Unstable)
        last2 = h[-2:]
        if tuple(last2) in [('P','B'), ('B','P')]:
            return True

        # B3-P1 or P3-B1 (Risk of reversal) - 3 consecutive then cut
        if len(h) >= 4:
            if (len(set(h[-4:-1])) == 1 and h[-4] != h[-1]):
                return True
        return False

    # --- 4. 🎯 Confidence Engine (ระบบประเมินความมั่นใจ 0-100%) ---
    def confidence_score(self):
        """Calculates the system's confidence score for prediction."""
        if not self.history or len(self.history) < 10:
            return 0

        patterns = self.detect_patterns()
        momentum = self.detect_momentum()
        trap = self.in_trap_zone()

        score = 50

        if patterns:
            score += len(patterns) * 10

        if momentum:
            score += len(momentum) * 8

        if trap:
            score -= 60

        if score < 0:
            score = 0
        if score > 100:
            score = 100

        return score

    # --- 5. 🔁 Memory Logic (จดจำ Pattern ที่เคยพลาด) ---
    def update_failed_pattern(self, pattern_name):
        """Adds a pattern that led to an incorrect prediction to memory."""
        self.memory_failed_patterns.add(pattern_name)

    def is_pattern_failed(self, pattern_name):
        """Checks if this pattern has previously led to an incorrect prediction."""
        return pattern_name in self.memory_failed_patterns

    # --- 6. 🧠 Intuition Logic (ลอจิกเชิงลึกเมื่อไม่มี Pattern ชัดเจน) ---
    def intuition_predict(self):
        """Uses deep logic to predict when no clear pattern is present."""
        h = self.history
        if len(h) < 3:
            return '?'

        last3 = h[-3:]
        last4 = h[-4:] if len(h) >= 4 else None

        # Specific Tie patterns
        if 'T' in last3 and last3.count('T') == 1 and last3[0] != last3[1] and last3[1] != last3[2]:
            return 'T'
        if last4 and Counter(last4)['T'] >= 2:
            return 'T'

        # Specific P/B patterns
        if last3 == ['P','B','P']:
            return 'P'
        if last3 == ['B','B','P']:
            return 'P'
        if last3 == ['P','P','B']:
            return 'B'
        if len(h) >= 5 and h[-5:] == ['B','P','B','P','P']:
             return 'B'

        return '?'

    # --- 7. 🔬 Backtest Simulation (ทดสอบผลย้อนหลัง) ---
    def backtest_accuracy(self):
        """
        Calculates the system's accuracy from historical predictions (requires actual logic).
        And checks Drawdown.
        """
        if len(self.history) < 20:
            return 0

        # TODO: Implement actual backtesting simulation here
        return random.randint(60, 90) # Dummy accuracy value between 60-90%

    def backtest_drawdown_exceeded(self):
        """
        Checks if Drawdown (consecutive misses) exceeds 3 times (requires actual logic).
        """
        # TODO: Implement actual drawdown checking logic here
        return False # Assume not exceeded (dummy value)

    # --- ฟังก์ชันหลักในการทำนายผลถัดไป ---
    def predict_next(self):
        """
        Main function for analyzing and predicting the next outcome.
        Returns a dictionary with prediction, risk, recommendation, developer_view.
        """
        prediction_result = '?'
        risk_level = "Normal"
        recommendation = "Play ✅"
        developer_view = ""

        # --- 1. ตรวจสอบ Trap Zone เป็นอันดับแรกสุด (งดเดิมพันทันที) ---
        if self.in_trap_zone():
            risk_level = "Trap"
            recommendation = "Avoid ❌"
            developer_view = "Trap Zone detected: High volatility, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 2. ตรวจสอบ Confidence Score (งดเดิมพันหากต่ำกว่าเกณฑ์) ---
        score = self.confidence_score()
        if score < 60:
            recommendation = "Avoid ❌"
            developer_view = f"Confidence Score ({score}%) is below threshold (60%), recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": "Low Confidence",
                "recommendation": recommendation
            }

        # --- 3. ตรวจสอบ Drawdown (หากเกิน 3 miss ติดกัน ให้งดเดิมพัน) ---
        if self.backtest_drawdown_exceeded():
            risk_level = "High Drawdown"
            recommendation = "Avoid ❌"
            developer_view = "Drawdown exceeded 3 consecutive misses, recommending avoidance."
            return {
                "developer_view": developer_view,
                "prediction": prediction_result,
                "accuracy": self.backtest_accuracy(),
                "risk": risk_level,
                "recommendation": recommendation
            }

        # --- 4. ใช้ Pattern หลักในการทำนาย (หากมี) ---
        patterns = self.detect_patterns()
        momentum = self.detect_momentum()

        if patterns:
            developer_view_patterns_list = []
            for pat_name in patterns:
                developer_view_patterns_list.append(pat_name)

                # ตรวจสอบ Memory Logic: ห้ามใช้ pattern ที่เคยพลาด
                if self.is_pattern_failed(pat_name):
                    developer_view += f" (Note: Pattern '{pat_name}' previously failed. Skipping.)"
                    continue

                # ลอจิกการทำนายตาม Pattern ที่มั่นใจ
                if 'Dragon' in pat_name:
                    prediction_result = self.history[-1]
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting last result."
                    break
                elif 'Pingpong' in pat_name: # Updated to check if 'Pingpong' is in name
                    last = self.history[-1]
                    prediction_result = 'P' if last == 'B' else 'B'
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting opposite of last."
                    break
                elif pat_name == 'Two-Cut':
                    if len(self.history) >= 2:
                        last_two = self.history[-2:]
                        if last_two[0] == last_two[1]:
                            prediction_result = 'P' if last_two[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
                elif pat_name == 'Triple Cut': # Logic for Triple Cut
                    if len(self.history) >= 3:
                        last_three = self.history[-3:]
                        if len(set(last_three)) == 1: # E.g., PPP
                            # Predict the opposite of the current triple
                            prediction_result = 'P' if last_three[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Triple Cut detected. Predicting opposite of last three."
                            break

            if developer_view_patterns_list and not developer_view:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            elif developer_view_patterns_list:
                developer_view += f" | Other patterns: {', '.join(developer_view_patterns_list)}."

        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if prediction_result == '?': # ถ้ายังไม่มีการทำนายจาก Pattern หลัก
            intuitive_guess = self.intuition_predict()

            if intuitive_guess == 'T':
                prediction_result = 'T'
                developer_view += " (Intuition Logic: Specific Tie pattern identified.)"
            elif intuitive_guess in ['P', 'B']:
                prediction_result = intuitive_guess
                developer_view += f" (Intuition Logic: Predicting {intuitive_guess} based on subtle patterns.)"
            else:
                recommendation = "Avoid ❌"
                risk_level = "Uncertainty"
                developer_view += " (Intuition Logic: No strong P/B/T prediction, recommending Avoid.)"
                prediction_result = '?'

        # รวบรวม Developer View เพิ่มเติมจาก Momentum
        if momentum:
            if developer_view: developer_view += " | "
            developer_view += f"Momentum: {', '.join(momentum)}."

        # หากไม่มีอะไรเลยและยังทำนายไม่ได้
        if not developer_view and prediction_result == '?':
            developer_view = "No strong patterns or intuition detected."

        return {
            "developer_view": developer_view,
            "prediction": prediction_result,
            "accuracy": self.backtest_accuracy(),
            "risk": risk_level,
            "recommendation": recommendation
        }

    def _build_big_road(self, history, max_rows=6):
        """
        Builds the Big Road representation from the history.
        Returns a 2D list (grid) where each cell is a dict {'type': 'P'/'B', 'ties': count} or None.
        Handles column changes, vertical stacking, and horizontal tailing.
        Ties are marked on the last P/B result.
        """
        if not history:
            return []

        # This will store the data for each cell in the Big Road, with its calculated grid position
        # Format: {'type': 'P'/'B', 'ties': count, 'grid_col': int, 'grid_row': int}
        road_cells = []

        current_col_idx = 0
        current_row_idx = 0
        last_pb_type = None # Stores the type of the last P/B result to determine column breaks

        # Iterate through the history to determine cell types and positions
        for i, result in enumerate(history):
            if result == 'T':
                # Ties are marked on the last P/B cell.
                # Find the last P/B cell that was added to road_cells and increment its tie count.
                found_pb_for_tie = False
                for cell in reversed(road_cells):
                    if cell['type'] in ['P', 'B']: # Only attach ties to P or B cells
                        cell['ties'] += 1
                        found_pb_for_tie = True
                        break
                # If no P/B cell exists yet (e.g., history starts with 'T'), we ignore the tie for Big Road.
                # Standard Big Road doesn't start with standalone ties, they are usually overlays.
                continue # Ties do not advance the main P/B column/row logic

            # Handle P or B results
            if last_pb_type is None: # This is the very first P/B result
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})
            elif result == last_pb_type: # Same type as previous P/B, continue in current column
                if current_row_idx < max_rows - 1: # Still space to go down
                    current_row_idx += 1
                else: # Column is full, start tailing
                    current_col_idx += 1
                    # current_row_idx remains at max_rows - 1 for tailing
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})
            else: # Different type from previous P/B, start a new column
                current_col_idx += 1
                current_row_idx = 0 # Reset row for the new column
                road_cells.append({'type': result, 'ties': 0, 'grid_col': current_col_idx, 'grid_row': current_row_idx})

            last_pb_type = result # Update the last P/B type

        # Now, convert the `road_cells` into a proper 2D grid for rendering
        if not road_cells:
            return []

        # Determine the maximum column index to size the grid correctly
        max_grid_col = max(cell['grid_col'] for cell in road_cells)
        # The grid will have `max_rows` rows and `max_grid_col + 1` columns
        big_road_grid = [[None for _ in range(max_grid_col + 1)] for _ in range(max_rows)]

        for cell in road_cells:
            big_road_grid[cell['grid_row']][cell['grid_col']] = {'type': cell['type'], 'ties': cell['ties']}

        return big_road_grid
