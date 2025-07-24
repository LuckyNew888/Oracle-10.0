
import random

class OracleEngine:
    def __init__(self):
        self.history = []
        self.pattern_stats = {}
        self.momentum_stats = {}
        self.sequence_memory_stats = {}
        self.failed_pattern_instances = {}
        self.last_failed_patterns = set()
        self.pattern_weights = {
            'Dragon': 1.0, 'FollowStreak': 0.95, 'Pingpong': 0.9, 'Two-Cut': 0.8,
            'Triple-Cut': 0.8, 'One-Two Pattern': 0.7, 'Two-One Pattern': 0.7,
            'Broken Pattern': 0.6
        }
        self.momentum_weights = {
            'B3+ Momentum': 0.9, 'P3+ Momentum': 0.9, 'Steady Repeat Momentum': 0.85,
            'Ladder Momentum (1-2-3)': 0.7, 'Ladder Momentum (X-Y-XX-Y)': 0.6
        }
        self.sequence_weights = {3: 0.6, 4: 0.7, 5: 0.8}
        self.last_prediction = '?'

    def reset_history(self):
        self.history = []
        self.pattern_stats.clear()
        self.momentum_stats.clear()
        self.sequence_memory_stats.clear()
        self.failed_pattern_instances.clear()
        self.last_failed_patterns.clear()
        self.last_prediction = '?'

    def detect_patterns(self, history, big_road=None):
        patterns = []
        if len(history) < 6:
            return patterns
        seq = ''.join([item['main_outcome'] for item in history[-10:]])
        if seq.endswith('PBPB'):
            patterns.append('Pingpong')
        if seq.endswith('PPP') or seq.endswith('BBB'):
            patterns.append('Dragon')
        if seq.endswith('BBPP') or seq.endswith('PPBB'):
            patterns.append('Two-Cut')
        if 'PPPB' in seq or 'BBBP' in seq:
            patterns.append('Broken Pattern')
        return patterns

    def detect_momentum(self, history, big_road=None):
        momentum = []
        if len(history) < 6:
            return momentum
        streak = 1
        for i in range(len(history)-1, 0, -1):
            if history[i]['main_outcome'] == history[i-1]['main_outcome']:
                streak += 1
            else:
                break
        if streak >= 3:
            outcome = history[-1]['main_outcome']
            momentum.append(f"{outcome}3+ Momentum")
        return momentum

    def _detect_sequences(self, history):
        sequences = []
        seq = ''.join([item['main_outcome'] for item in history])
        for length in [3, 4, 5]:
            if seq.endswith(seq[-length:] * 2):
                sequences.append(f"Repeat-{length}")
        return sequences

    def confidence_score(self, history, big_road=None):
        patterns = self.detect_patterns(history, big_road)
        momentum = self.detect_momentum(history, big_road)
        sequences = self._detect_sequences(history)
        score = 0
        total_weight = 0
        for p in patterns:
            score += self.pattern_weights.get(p, 0.5)
            total_weight += 1
        for m in momentum:
            score += self.momentum_weights.get(m, 0.5)
            total_weight += 1
        for s in sequences:
            score += self.sequence_weights.get(len(s.split('-')[-1]), 0.6)
            total_weight += 1
        if total_weight == 0:
            return 0
        return round((score / total_weight) * 100)

    def _fallback_to_gemini(self, history):
        return random.choice(['P', 'B', 'T'])

    def predict_next(self):
        if len(self.history) < 20:
            return {'prediction': '?', 'recommendation': 'Avoid ❌', 'risk': 'Not enough data', 'developer_view': '—'}
        patterns = self.detect_patterns(self.history)
        momentum = self.detect_momentum(self.history)
        sequences = self._detect_sequences(self.history)
        developer_view = f"{patterns} + {momentum} + {sequences}"
        confidence = self.confidence_score(self.history)
        prediction = '?'
        risk = 'Normal'
        recommendation = 'Avoid ❌'
        if confidence >= 60:
            if 'Dragon' in patterns or 'FollowStreak' in momentum:
                prediction = self.history[-1]['main_outcome']
            elif 'Pingpong' in patterns:
                prediction = 'B' if self.history[-1]['main_outcome'] == 'P' else 'P'
            elif 'Two-Cut' in patterns:
                prediction = self.history[-1]['main_outcome']
            else:
                prediction = self._fallback_to_gemini(self.history)
            if prediction in self.last_failed_patterns:
                prediction = '?'
                risk = 'Memory Rejection'
        else:
            risk = 'Low Confidence'
        if prediction in ['P', 'B', 'T']:
            recommendation = 'Play ✅'
        else:
            recommendation = 'Avoid ❌'
        self.last_prediction = prediction
        return {
            'prediction': prediction,
            'recommendation': recommendation,
            'risk': risk,
            'developer_view': developer_view
        }

    def _update_learning(self, predicted_outcome, actual_outcome, patterns_detected, momentum_detected, sequences_detected):
        if predicted_outcome != actual_outcome:
            self.last_failed_patterns.update(patterns_detected + momentum_detected + sequences_detected)
        else:
            for p in patterns_detected + momentum_detected + sequences_detected:
                self.pattern_stats[p] = self.pattern_stats.get(p, 0) + 1
