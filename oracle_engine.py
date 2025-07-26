import random
from collections import Counter
import math # Import math for more advanced weighting

# --- Configuration for Prediction Logic (Includes V1.14 improvements) ---
MIN_HISTORY_FOR_PREDICTION = 15
MAX_HISTORY_FOR_ANALYSIS = 30
PREDICTION_THRESHOLD = 0.55
COUNTER_PREDICTION_THRESHOLD = 0.65 
DNA_PATTERN_LENGTH = 5
MOMENTUM_THRESHOLD = 0.70 # Not strictly a threshold for prediction, more for confidence scaling
COUNTER_BIAS_STREAK_THRESHOLD = 3

# --- Helper Functions (from V1.13, retained) ---

def get_outcome_emoji(outcome):
    return "🟦" if outcome == 'P' else "🟥" if outcome == 'B' else "⚪️"

def get_latest_history_string(history_list, num_results=MAX_HISTORY_FOR_ANALYSIS):
    return "".join([h['main_outcome'] for h in history_list[-num_results:]])

# --- Prediction Logic (Updated to V1.14 intelligence) ---

# 1. DNA Pattern Analysis (Improved: Adaptive Weighting for Recent Matches)
def analyze_dna_pattern(history_str):
    if len(history_str) < DNA_PATTERN_LENGTH:
        return None, 0

    target_pattern = history_str[-DNA_PATTERN_LENGTH:]
    
    followers = Counter()
    weighted_total = 0
    
    # Iterate from the earliest possible match to the latest to apply weights
    # We iterate backwards to easily calculate distance from the current end
    for i in range(len(history_str) - DNA_PATTERN_LENGTH - 1, -1, -1):
        if history_str[i : i + DNA_PATTERN_LENGTH] == target_pattern:
            if (i + DNA_PATTERN_LENGTH) < len(history_str):
                follower_outcome = history_str[i + DNA_PATTERN_LENGTH]
                
                # Calculate inverse distance (more recent matches get higher weight)
                # distance_from_end = (len(history_str) - 1) - (i + DNA_PATTERN_LENGTH) 
                # weight = 1.0 / (distance_from_end + 1) # Add 1 to avoid division by zero for closest match
                
                # Using exponential decay for weights (more significant difference for closer matches)
                # Closer matches have a higher exponent base, thus higher weight
                relative_distance = (len(history_str) - (i + DNA_PATTERN_LENGTH)) # How many steps away from the current end
                weight = math.exp(-relative_distance * 0.1) # Exponential decay factor, adjust 0.1 for sensitivity
                
                followers[follower_outcome] += weight
                weighted_total += weight
    
    if weighted_total == 0:
        return None, 0
    
    most_common_follower = followers.most_common(1)
    
    if most_common_follower:
        predicted_outcome = most_common_follower[0][0]
        confidence = most_common_follower[0][1] / weighted_total
        return predicted_outcome, confidence
    return None, 0

# 2. Momentum Tracker (Improved: More nuanced streak confidence)
def analyze_momentum(history_str):
    if len(history_str) < 5:
        return None, 0

    last_outcome = history_str[-1]
    last_streak_length = 0
    for i in reversed(range(len(history_str))):
        if history_str[i] == last_outcome:
            last_streak_length += 1
        else:
            break
            
    # Increased confidence scaling for longer streaks
    if last_streak_length >= 3:
        # Confidence increases more rapidly with streak length
        # Using a non-linear scale like log or a steeper linear scale
        confidence = min(1.0, 0.60 + (last_streak_length - 3) * 0.15) # Adjusted for steeper increase
        return last_outcome, confidence
    
    # Ping-pong pattern - kept as is, but could also be dynamically confident
    if len(history_str) >= 4 and history_str[-4:] in ["PBPB", "BPBP"]:
        predicted_outcome = 'P' if history_str[-1] == 'B' else 'B'
        return predicted_outcome, 0.65 
    
    return None, 0

# 3. Intuition (V1.14 with Dynamic Confidence for Counter Bias - retained from last update)
def analyze_intuition(history_str):
    if len(history_str) < 3:
        return None, 0, False

    last_3 = history_str[-3:]
    last_2 = history_str[-2:]
    
    # Counter Bias Logic (Improved in V1.14 with dynamic confidence)
    if len(history_str) >= COUNTER_BIAS_STREAK_THRESHOLD:
        last_outcome = history_str[-1]
        streak_count = 0
        for i in reversed(range(len(history_str))):
            if history_str[i] == last_outcome:
                streak_count += 1
            else:
                break
            
        if streak_count >= COUNTER_BIAS_STREAK_THRESHOLD:
            streak_pattern = history_str[len(history_str) - streak_count:]
            
            continue_count = 0
            break_count = 0
            
            for i in range(len(history_str) - streak_count):
                if (i + streak_count) < len(history_str) and history_str[i : i + streak_count] == streak_pattern:
                    if i == (len(history_str) - streak_count):
                        continue # Exclude the current streak itself
                            
                    if history_str[i + streak_count] == last_outcome:
                        continue_count += 1
                    else:
                        break_count += 1
            
            total_instances = continue_count + break_count
            if total_instances > 0:
                if break_count > continue_count:
                    dynamic_counter_conf = min(0.85, COUNTER_PREDICTION_THRESHOLD + (break_count / total_instances) * (0.85 - COUNTER_PREDICTION_THRESHOLD))
                    return ('P' if last_outcome == 'B' else 'B'), dynamic_counter_conf, True
                elif continue_count == 0 and total_instances >= 2:
                    return ('P' if last_outcome == 'B' else 'B'), COUNTER_PREDICTION_THRESHOLD, True
    
    # Simple Intuition Patterns (from V1.13, retained)
    if last_3 == "BBP" or last_3 == "PBB":
        return ('P' if last_3[-1] == 'B' else 'B'), 0.6, False
    if last_3 == "PPB" or last_3 == "BPP":
        return ('B' if last_3[-1] == 'P' else 'P'), 0.6, False
    
    if last_2 == "BP" or last_2 == "PB":
        return ('B' if last_2[-1] == 'P' else 'P'), 0.55, False
        
    return None, 0, False

# Main prediction function (Updated to use V1.14 intelligent logic from sub-functions)
def predict_outcome(history_list):
    history_str = get_latest_history_string(history_list)
    
    if len(history_str) < MIN_HISTORY_FOR_PREDICTION:
        return {"prediction": "ไม่เพียงพอ", "confidence": 0, "predicted_by": [], "is_counter": False}

    predictions = []
    
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

    # Prioritize Counter prediction if it's highly confident (V1.14 logic for this check)
    for p in predictions:
        if p.get('is_counter', False) and p['confidence'] >= COUNTER_PREDICTION_THRESHOLD:
            return {"prediction": p['outcome'], 
                    "confidence": p['confidence'], 
                    "predicted_by": [p['source']], 
                    "is_counter": True}

    outcome_scores = Counter()
    outcome_sources = {}
    is_any_counter_in_other_preds = False

    for p in predictions:
        if not p.get('is_counter', False) or p['confidence'] < COUNTER_PREDICTION_THRESHOLD:
            outcome_scores[p['outcome']] += p['confidence']
            if p['outcome'] not in outcome_sources:
                outcome_sources[p['outcome']] = []
            outcome_sources[p['outcome']].append(p['source'])
            if p.get('is_counter', False):
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
