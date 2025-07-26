import random
from collections import Counter

# --- Configuration for Prediction Logic (from V1.13) ---
MIN_HISTORY_FOR_PREDICTION = 15
MAX_HISTORY_FOR_ANALYSIS = 30 # Max history for analysis, remains 30 from V1.13 logic
PREDICTION_THRESHOLD = 0.55
COUNTER_PREDICTION_THRESHOLD = 0.65
DNA_PATTERN_LENGTH = 5
MOMENTUM_THRESHOLD = 0.70 # Not explicitly used as threshold in V1.13 momentum, but good to keep
COUNTER_BIAS_STREAK_THRESHOLD = 3

# --- Helper Functions (from V1.13) ---

def get_outcome_emoji(outcome):
    # This function is used for displaying outcomes, good to be in common module
    return "🟦" if outcome == 'P' else "🟥" if outcome == 'B' else "⚪️"

def get_latest_history_string(history_list, num_results=MAX_HISTORY_FOR_ANALYSIS):
    # Extracts the string of outcomes for analysis
    return "".join([h['main_outcome'] for h in history_list[-num_results:]])

# --- Prediction Logic (from V1.13) ---

def analyze_dna_pattern(history_str):
    if len(history_str) < DNA_PATTERN_LENGTH:
        return None, 0

    target_pattern = history_str[-DNA_PATTERN_LENGTH:]
    
    followers = Counter()
    total_matches = 0 # In V1.13, it was a simple count, not weighted
    
    for i in range(len(history_str) - DNA_PATTERN_LENGTH):
        if history_str[i : i + DNA_PATTERN_LENGTH] == target_pattern:
            if (i + DNA_PATTERN_LENGTH) < len(history_str):
                follower_outcome = history_str[i + DNA_PATTERN_LENGTH]
                followers[follower_outcome] += 1
                total_matches += 1
    
    if total_matches == 0:
        return None, 0
    
    most_common_follower = followers.most_common(1)
    
    if most_common_follower:
        predicted_outcome = most_common_follower[0][0]
        confidence = most_common_follower[0][1] / total_matches # Simple confidence based on count
        return predicted_outcome, confidence
    return None, 0

def analyze_momentum(history_str):
    if len(history_str) < 5: # V1.13 had a minimum length for momentum
        return None, 0

    last_outcome = history_str[-1]
    last_streak_length = 0
    for i in reversed(range(len(history_str))):
        if history_str[i] == last_outcome:
            last_streak_length += 1
        else:
            break
            
    if last_streak_length >= 3: # Predict to continue streak if >= 3
        return last_outcome, 0.70 # Fixed confidence for momentum in V1.13
    
    if len(history_str) >= 4 and history_str[-4:] in ["PBPB", "BPBP"]: # Ping-pong pattern
        predicted_outcome = 'P' if history_str[-1] == 'B' else 'B'
        return predicted_outcome, 0.65 # Fixed confidence for ping-pong
    
    return None, 0

def analyze_intuition(history_str):
    if len(history_str) < 3:
        return None, 0, False

    last_3 = history_str[-3:]
    last_2 = history_str[-2:]
    
    # Counter Bias Logic (as present in V1.13)
    if len(history_str) >= COUNTER_BIAS_STREAK_THRESHOLD:
        last_outcome = history_str[-1]
        streak_count = 0
        for i in reversed(range(len(history_str))):
            if history_str[i] == last_outcome:
                streak_count += 1
            else:
                break
        
        if streak_count >= COUNTER_BIAS_STREAK_THRESHOLD:
            # Check for instances where the streak broke in the past
            break_count = 0
            total_instances_checked = 0
            for i in range(len(history_str) - streak_count):
                if history_str[i : i + streak_count] == history_str[len(history_str) - streak_count:]: # Match the exact streak
                    if (i + streak_count) < len(history_str):
                        if history_str[i + streak_count] != last_outcome: # If it broke the streak
                            break_count += 1
                        total_instances_checked += 1
            
            if total_instances_checked > 0 and break_count > (total_instances_checked / 2): # If it broke more than half the time
                return ('P' if last_outcome == 'B' else 'B'), COUNTER_PREDICTION_THRESHOLD, True # Predict counter with fixed threshold

    # Simple Intuition (Two-cut, etc. from V1.13)
    if last_3 == "BBP" or last_3 == "PBB":
        return ('P' if last_3[-1] == 'B' else 'B'), 0.6, False
    if last_3 == "PPB" or last_3 == "BPP":
        return ('B' if last_3[-1] == 'P' else 'P'), 0.6, False
    
    if last_2 == "BP" or last_2 == "PB":
        return ('B' if last_2[-1] == 'P' else 'P'), 0.55, False
        
    return None, 0, False

def predict_outcome(history_list):
    history_str = get_latest_history_string(history_list)
    
    if len(history_str) < MIN_HISTORY_FOR_PREDICTION:
        return {"prediction": "ไม่เพียงพอ", "confidence": 0, "predicted_by": [], "is_counter": False}

    predictions = []
    
    # Run all analysis modules
    dna_pred, dna_conf = analyze_dna_pattern(history_str)
    if dna_pred:
        predictions.append({"outcome": dna_pred, "confidence": dna_conf, "source": "DNA"})

    momentum_pred, momentum_conf = analyze_momentum(history_str)
    if momentum_pred:
        predictions.append({"outcome": momentum_pred, "confidence": momentum_conf, "source": "Momentum"})

    intuition_pred, intuition_conf, is_counter_intuition = analyze_intuition(history_str)
    if intuition_pred:
        predictions.append({"outcome": intuition_pred, "confidence": intuition_conf, "source": "Intuition", "is_counter": is_counter_intuition})
    
    if not predictions:
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    # Prioritize Counter prediction if it's confident (V1.13 logic)
    for p in predictions:
        if p.get('is_counter', False) and p['confidence'] >= COUNTER_PREDICTION_THRESHOLD:
            return {"prediction": p['outcome'], 
                    "confidence": p['confidence'], 
                    "predicted_by": [p['source']], 
                    "is_counter": True}

    # Combine other predictions (V1.13 logic)
    outcome_scores = Counter()
    outcome_sources = {}
    is_any_counter_in_other_preds = False

    for p in predictions:
        # Only include non-counter or weak-counter predictions here
        if not p.get('is_counter', False) or p['confidence'] < COUNTER_PREDICTION_THRESHOLD:
            outcome_scores[p['outcome']] += p['confidence']
            if p['outcome'] not in outcome_sources:
                outcome_sources[p['outcome']] = []
            outcome_sources[p['outcome']].append(p['source'])
            if p.get('is_counter', False): # Track if any source was counter even if not primary
                is_any_counter_in_other_preds = True

    if not outcome_scores:
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    sorted_outcomes = sorted(outcome_scores.items(), key=lambda item: item[1], reverse=True)
    
    best_outcome = sorted_outcomes[0][0]
    best_confidence = sorted_outcomes[0][1] / len(outcome_sources[best_outcome])
    
    if best_confidence >= PREDICTION_THRESHOLD:
        return {"prediction": best_outcome, 
                "confidence": best_confidence, 
                "predicted_by": outcome_sources[best_outcome],
                "is_counter": is_any_counter_in_other_preds}
    else:
        return {"prediction": "ไม่ชัดเจน", "confidence": best_confidence, "predicted_by": outcome_sources[best_outcome], "is_counter": is_any_counter_in_other_preds}
