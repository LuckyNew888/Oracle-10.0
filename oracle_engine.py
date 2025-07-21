from collections import Counter
import random

class OracleEngine:
    def __init__(self):
        # History will now store richer objects:
        # {'main_outcome': 'P'/'B'/'T', 'ties': int, 'is_any_natural': bool}
        self.history = []
        self.memory_failed_patterns = set()

    # --- Data Management (for the Engine itself) ---
    # update_history is now primarily handled by record_bet_result in Streamlit app
    # This method is kept for internal engine logic if needed, but not directly used for adding results from UI
    def update_history(self, result_obj):
        """Adds a new result object to the history (for internal engine use)."""
        # Assuming result_obj is a dict like {'main_outcome': 'P'/'B'/'T', 'ties': int, 'is_any_natural': bool}
        if isinstance(result_obj, dict) and 'main_outcome' in result_obj:
            self.history.append(result_obj)

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
        Uses main_outcome from history objects.
        """
        # Extract only main outcomes for pattern detection
        h = [item['main_outcome'] for item in self.history if item['main_outcome'] in ['P', 'B']]

        patterns = []

        # Detect Pingpong (Alternating P/B pattern for a certain length)
        if len(h) >= 2:
            alternating_count = 0
            for i in range(len(h) - 1, 0, -1):
                if h[i] != h[i-1]:
                    alternating_count += 1
                else:
                    break
            if alternating_count >= 3:
                patterns.append(f'Pingpong ({alternating_count + 1}x)')

        # Detect Two-Cut (BB-PP or PP-BB)
        if len(h) >= 4:
            last4 = h[-4:]
            if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
                patterns.append('Two-Cut')

        # Detect Dragon (long streak: 3 to 6 consecutive same results)
        for i in range(3, 7):
            if len(h) >= i:
                if len(set(h[-i:])) == 1:
                    patterns.append(f'Dragon ({i})')

        # Detect Triple Cut (e.g., PPPBBB or BBBPPP)
        if len(h) >= 6:
            last6 = h[-6:]
            if (last6[0] == last6[1] == last6[2] and
                last6[3] == last6[4] == last6[5] and
                last6[0] != last6[3]):
                patterns.append('Triple Cut')

        # Detect Broken Pattern (BPBPPBP) - Example Implementation
        if len(h) >= 7:
            last7 = "".join(h[-7:])
            if "BPBPPBP" in last7 or "PBPBBBP" in last7:
                patterns.append('Broken Pattern')

        return patterns

    # --- 2. 🚀 Momentum Tracker (ตรวจจับแรงเหวี่ยง) ---
    def detect_momentum(self):
        """Detects momentum such as B3+, P3+, Steady Repeat. Uses main_outcome."""
        h = [item['main_outcome'] for item in self.history if item['main_outcome'] in ['P', 'B']]
        momentum = []

        # Check for Momentum (3 or more consecutive same results)
        if len(h) >= 3:
            last_char = h[-1]
            streak_count = 0
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
        """Detects zones where changes are rapid and dangerous. Uses main_outcome."""
        h = [item['main_outcome'] for item in self.history if item['main_outcome'] in ['P', 'B']]
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
        """Uses deep logic to predict when no clear pattern is present. Uses main_outcome."""
        h = [item['main_outcome'] for item in self.history] # Use all outcomes for intuition
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
                    # Use main_outcome from the last history item
                    prediction_result = self.history[-1]['main_outcome']
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting last result."
                    break
                elif 'Pingpong' in pat_name:
                    last = self.history[-1]['main_outcome']
                    prediction_result = 'P' if last == 'B' else 'B'
                    developer_view = f"DNA Pattern: {pat_name} detected. Predicting opposite of last."
                    break
                elif pat_name == 'Two-Cut':
                    if len(self.history) >= 2:
                        last_two = [item['main_outcome'] for item in self.history[-2:]]
                        if last_two[0] == last_two[1]:
                            prediction_result = 'P' if last_two[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Two-Cut detected. Predicting opposite of current pair."
                            break
                elif pat_name == 'Triple Cut':
                    if len(self.history) >= 3:
                        last_three = [item['main_outcome'] for item in self.history[-3:]]
                        if len(set(last_three)) == 1:
                            prediction_result = 'P' if last_three[0] == 'B' else 'B'
                            developer_view = f"DNA Pattern: Triple Cut detected. Predicting opposite of last three."
                            break

            if developer_view_patterns_list and not developer_view:
                developer_view += f"Detected patterns: {', '.join(developer_view_patterns_list)}."
            elif developer_view_patterns_list:
                developer_view += f" | Other patterns: {', '.join(developer_view_patterns_list)}."

        # --- 5. Intuition Logic (ใช้เมื่อไม่มี Pattern หลัก หรือ Pattern ที่เจอเคยพลาด) ---
        if prediction_result == '?':
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
