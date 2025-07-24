class OracleEngine:
    def __init__(self):
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.failed_pattern_instances = []
        self.last_failed_patterns = set()  # NEW: Track last failed pattern names

        self.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Broken Pattern': 0.3
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6
        }
        self.sequence_weights = {3: 0.6, 4: 0.7, 5: 0.8}

    def reset_history(self):
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.failed_pattern_instances = []
        self.last_failed_patterns = set()

    def reset_learning_states_on_undo(self):
        self.failed_pattern_instances = []
        self.last_failed_patterns = set()

    def detect_patterns(self, history, big_road_data):
        patterns = []

        def last_n(n):
            return [r['main_outcome'] for r in history[-n:]]

        # Pingpong
        seq = last_n(6)
        if len(seq) >= 4 and all(seq[i] != seq[i+1] for i in range(len(seq)-1)):
            patterns.append('Pingpong')

        # Dragon
        if len(seq) >= 3 and all(x == seq[0] for x in seq):
            patterns.append('Dragon')

        # Two-Cut
        if len(seq) >= 4 and seq == ['B', 'B', 'P', 'P']:
            patterns.append('Two-Cut')

        # Triple-Cut
        if len(seq) >= 6 and seq == ['B', 'B', 'B', 'P', 'P', 'P']:
            patterns.append('Triple-Cut')

        # One-Two Pattern
        if len(seq) >= 5 and seq[-5:] == ['B', 'P', 'P', 'B', 'P']:
            patterns.append('One-Two Pattern')

        # Two-One Pattern
        if len(seq) >= 5 and seq[-5:] == ['B', 'B', 'P', 'B', 'B']:
            patterns.append('Two-One Pattern')

        # Broken Pattern
        if len(seq) >= 6 and seq[:3] == ['B', 'P', 'B'] and seq[-3:] == ['P', 'B', 'P']:
            patterns.append('Broken Pattern')

        # FollowStreak
        if len(seq) >= 3 and seq[-1] == seq[-2] == seq[-3]:
            patterns.append('FollowStreak')

        return patterns

    def detect_momentum(self, history, big_road_data):
        momentum = []

        last_results = [r['main_outcome'] for r in history[-10:]]

        def count_streak(side):
            count = 0
            for result in reversed(last_results):
                if result == side:
                    count += 1
                else:
                    break
            return count

        if count_streak('B') >= 3:
            momentum.append('B3+ Momentum')
        if count_streak('P') >= 3:
            momentum.append('P3+ Momentum')

        # Steady Repeat
        if last_results[-7:] == ['P', 'B', 'P', 'B', 'P', 'B', 'P']:
            momentum.append('Steady Repeat Momentum')

        # Ladder
        if last_results[-6:] == ['B', 'P', 'B', 'B', 'P', 'B', 'B', 'B']:
            momentum.append('Ladder Momentum (1-2-3)')

        return momentum

    def _detect_sequences(self, history):
        results = [r['main_outcome'] for r in history]
        sequences = {}
        current = None
        count = 0
        for r in results:
            if r == current:
                count += 1
            else:
                if current is not None and count >= 2:
                    sequences[count] = sequences.get(count, 0) + 1
                current = r
                count = 1
        return sequences

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        success = predicted_outcome == actual_outcome

        for p in patterns_detected:
            if p not in self.pattern_stats:
                self.pattern_stats[p] = {"hit": 0, "miss": 0}
            if success:
                self.pattern_stats[p]["hit"] += 1
            else:
                self.pattern_stats[p]["miss"] += 1
                self.failed_pattern_instances.append(p)
                self.last_failed_patterns.add(p)  # Track pattern that failed last time

        for m in momentum_detected:
            if m not in self.momentum_stats:
                self.momentum_stats[m] = {"hit": 0, "miss": 0}
            if success:
                self.momentum_stats[m]["hit"] += 1
            else:
                self.momentum_stats[m]["miss"] += 1

        for seq_len, count in sequences_detected.items():
            if seq_len not in self.sequence_memory_stats:
                self.sequence_memory_stats[seq_len] = {"hit": 0, "miss": 0}
            if success:
                self.sequence_memory_stats[seq_len]["hit"] += count
            else:
                self.sequence_memory_stats[seq_len]["miss"] += count

    def confidence_score(self, history, big_road_data):
        patterns = self.detect_patterns(history, big_road_data)
        momentum = self.detect_momentum(history, big_road_data)
        sequences = self._detect_sequences(history)

        score = 0
        count = 0

        for p in patterns:
            if p in self.pattern_weights and p not in self.last_failed_patterns:
                score += self.pattern_weights[p]
                count += 1

        for m in momentum:
            if m in self.momentum_weights:
                score += self.momentum_weights[m]
                count += 1

        for s, weight in self.sequence_weights.items():
            if s in sequences:
                score += weight
                count += 1

        return int((score / count) * 100) if count > 0 else 0

    def predict_next(self):
        big_road_data = []  # Placeholder
        patterns = self.detect_patterns(self.history, big_road_data)
        momentum = self.detect_momentum(self.history, big_road_data)
        sequences = self._detect_sequences(self.history)

        confidence = self.confidence_score(self.history, big_road_data)
        if confidence < 60:
            return {
                "prediction": "?",
                "developer_view": str(patterns),
                "recommendation": "Avoid ❌",
                "risk": "Low Confidence"
            }

        # Simple rule: follow last if momentum is high
        if momentum:
            last_result = self.history[-1]["main_outcome"] if self.history else "?"
            return {
                "prediction": last_result,
                "developer_view": str(patterns),
                "recommendation": "Play ✅",
                "risk": "Normal"
            }

        return {
            "prediction": "?",
            "developer_view": str(patterns),
            "recommendation": "Avoid ❌",
            "risk": "Uncertainty"
        }
