# oracle_engine.py

class OracleBaccaratAI:
    def __init__(self):
        self.memory = set()

    def analyze_patterns(self, data):
        view = []
        pattern = "Unknown"
        next_guess = "P"

        if data[-3:] == ["B", "P", "B"]:
            pattern = "Pingpong"
            next_guess = "P"
        elif data[-4:] == ["B", "B", "P", "P"]:
            pattern = "Two-Cut"
            next_guess = "B"
        elif len(set(data[-5:])) == 1:
            pattern = "Dragon"
            next_guess = data[-1]
        elif data[-5:] == ["B", "P", "P", "B", "P"]:
            pattern = "Broken Pattern"
            next_guess = "B"

        # ทำให้ดูสวย
        view = [data[i:i+3] for i in range(0, len(data)-2)]

        return {
            "view": view,
            "pattern": pattern,
            "next": next_guess
        }

    def track_momentum(self, data):
        last = data[-1]
        count = 0
        for i in reversed(data):
            if i == last:
                count += 1
            else:
                break
        return count >= 3

    def detect_trap_zone(self, data):
        if len(data) < 4:
            return False
        last4 = data[-4:]
        if last4 in [["P", "B", "P", "B"], ["B", "P", "B", "P"]]:
            return True
        if last4[:2] == last4[2:] and last4[0] != last4[1]:
            return True
        return False

    def calculate_confidence(self, pattern, momentum, trap):
        score = 0
        if pattern["pattern"] != "Unknown":
            score += 30
        if momentum:
            score += 30
        if not trap:
            score += 40
        return score

    def use_intuition(self, data):
        if data[-1] == "P":
            return "B"
        elif data[-1] == "B":
            return "P"
        else:
            return "P"

    def backtest(self, data, prediction):
        actual = data[-1]
        hit = 1 if prediction[-1] == actual else 0
        accuracy = round(hit * 100, 1)
        drawdown = 0 if hit == 1 else 1
        return {
            "accuracy": accuracy,
            "drawdown": drawdown
        }

    def predict(self, data):
        base = data[:10]
        test = data[10:]

        pattern = self.analyze_patterns(test)
        momentum = self.track_momentum(test)
        trap = self.detect_trap_zone(test)
        confidence = self.calculate_confidence(pattern, momentum, trap)

        if confidence < 60:
            prediction = self.use_intuition(test)
        else:
            prediction = pattern["next"]

        backtest_result = self.backtest(test, [prediction])

        result = {
            "🧬 Developer View": pattern["view"],
            "🔮 Prediction": prediction,
            "🎯 Accuracy": f"{backtest_result['accuracy']}%",
            "📍 Risk": "Trap" if trap else "Normal",
            "🧾 Recommendation": "Avoid ❌" if trap or backtest_result["accuracy"] < 60 else "Play ✅"
        }

        return result
