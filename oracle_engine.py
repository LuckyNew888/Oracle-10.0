# oracle_engine_v3_2.py
import random
from collections import Counter

class OracleEngine:
    def __init__(self):
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.failed_pattern_instances = {}
        self.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Broken Pattern': 0.3,
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6,
        }
        self.sequence_weights = {3: 0.6, 4: 0.7, 5: 0.8}
        self.tie_prediction_score = 0.1
        self.super6_occurrences = 0

    def reset_history(self):
        self.__init__()

    def _get_recent_results(self, n):
        return [x['main_outcome'] for x in self.history[-n:] if x['main_outcome'] in ['P', 'B']]

    def detect_patterns(self, history, big_road):
        results = self._get_recent_results(10)
        patterns = []

        if len(results) >= 6:
            if all(results[i] != results[i+1] for i in range(len(results)-1)):
                patterns.append("Pingpong")
            if len(set(results[-3:])) == 1:
                patterns.append("Dragon")
            if results[-2:] == results[-4:-2]:
                patterns.append("Two-Cut")

        return patterns

    def detect_momentum(self, history, big_road):
        results = self._get_recent_results(10)
        momentum = []

        if len(results) >= 4:
            streak = 1
            for i in range(len(results)-2, -1, -1):
                if results[i] == results[i+1]:
                    streak += 1
                else:
                    break
            if streak >= 3:
                side = results[-1]
                momentum.append(f"{side}3+ Momentum")
        return momentum

    def _detect_sequences(self, history):
        return Counter([x['main_outcome'] for x in history[-6:]])

    def confidence_score(self, history, big_road):
        patterns = self.detect_patterns(history, big_road)
        momentum = self.detect_momentum(history, big_road)
        sequences = self._detect_sequences(history)

        conf = 0.0
        for p in patterns:
            conf += self.pattern_weights.get(p, 0)
        for m in momentum:
            conf += self.momentum_weights.get(m, 0)
        for k, v in sequences.items():
            conf += self.sequence_weights.get(v, 0) * 0.5

        if self._is_in_trap_zone(history):
            conf -= 1.0

        return max(0, min(100, round(conf * 20, 2)))

    def _is_in_trap_zone(self, history):
        last = self._get_recent_results(4)
        if len(last) < 4: return False
        return (last[-1] != last[-2]) and (last[-2] != last[-3])

    def predict_next(self):
        if len(self.history) < 20:
            return {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Insufficient'}

        patterns = self.detect_patterns(self.history, [])
        momentum = self.detect_momentum(self.history, [])
        sequences = self._detect_sequences(self.history)

        scores = {'P': 0, 'B': 0, 'T': self.tie_prediction_score}

        for p in patterns:
            if 'P' in p:
                scores['P'] += self.pattern_weights.get(p, 0)
            elif 'B' in p:
                scores['B'] += self.pattern_weights.get(p, 0)

        for m in momentum:
            if 'P' in m:
                scores['P'] += self.momentum_weights.get(m, 0)
            elif 'B' in m:
                scores['B'] += self.momentum_weights.get(m, 0)

        max_side = max(scores, key=scores.get)
        confidence = self.confidence_score(self.history, [])

        recommendation = "Avoid ❌"
        if confidence >= 80:
            recommendation = "Play ✅"
        elif confidence >= 60:
            recommendation = "Consider ⚠️"

        return {
            'prediction': max_side,
            'confidence': confidence,
            'recommendation': recommendation,
            'risk': "Normal" if confidence >= 60 else "Trap",
            'developer_view': f"Patterns: {patterns} | Momentum: {momentum} | Sequences: {sequences}"
        }

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        if predicted_outcome != actual_outcome:
            for p in patterns_detected:
                self.failed_pattern_instances[p] = self.failed_pattern_instances.get(p, 0) + 1
        if actual_outcome == 'T':
            self.tie_prediction_score += 0.05
        else:
            self.tie_prediction_score = max(0.1, self.tie_prediction_score * 0.95)

    def reset_learning_states_on_undo(self):
        pass
