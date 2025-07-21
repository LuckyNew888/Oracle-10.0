# oracle_engine.py

class OracleBaccarat:
    def __init__(self):
        self.history = []  # เก็บประวัติผล เช่น ['P', 'B', 'T']

    def update_history(self, result):
        if result in ['P', 'B', 'T']:
            self.history.append(result)

    def reset_history(self):
        self.history = []

    def remove_last(self):
        if self.history:
            self.history.pop()

    def get_prediction(self):
        if len(self.history) < 3:
            return "❓"
        
        last3 = self.history[-3:]

        if last3[-1] == last3[-2] == last3[-3]:
            return last3[-1]  # เดินมังกรต่อ
        elif last3[-1] != last3[-2] and last3[-2] != last3[-3]:
            return last3[-1]  # ปิงปอง
        elif last3[-1] != last3[-2] == last3[-3]:
            return last3[-1]  # เค้า 2 ตัด
        else:
            return "❓"

    def get_history_emojis(self):
        emoji_map = {'P': '🔵', 'B': '🔴', 'T': '🟢'}
        return [emoji_map.get(r, '?') for r in self.history]
