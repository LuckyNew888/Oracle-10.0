import random
from collections import Counter

# --- Configuration for Prediction Logic ---
# These constants are now defined here, and app.py will import them.
MIN_HISTORY_FOR_PREDICTION = 15
MAX_HISTORY_FOR_ANALYSIS = 30
PREDICTION_THRESHOLD = 0.55
COUNTER_PREDICTION_THRESHOLD = 0.65
DNA_PATTERN_LENGTH = 5
MOMENTUM_THRESHOLD = 0.70
COUNTER_BIAS_STREAK_THRESHOLD = 3

# --- Helper Functions ---

# Function to get outcome emoji (moved here as it's used by prediction logic for internal representation)
def get_outcome_emoji(outcome):
    return "🟦" if outcome == 'P' else "🟥" if outcome == 'B' else "⚪️"

# Function to get latest history string (moved here as it's used by prediction logic)
# This function now needs to accept history_list as an argument from app.py
def get_latest_history_string(history_list, num_results=MAX_HISTORY_FOR_ANALYSIS):
    return "".join([h['main_outcome'] for h in history_list[-num_results:]])

# --- Prediction Logic ---

# 1. DNA Pattern Analysis (Improved: Weighted Recent Matches)
def analyze_dna_pattern(history_str):
    if len(history_str) < DNA_PATTERN_LENGTH:
        return None, 0

    target_pattern = history_str[-DNA_PATTERN_LENGTH:]
    
    followers = Counter()
    weighted_total = 0
    
    for i in range(len(history_str) - DNA_PATTERN_LENGTH):
        if history_str[i : i + DNA_PATTERN_LENGTH] == target_pattern:
            if (i + DNA_PATTERN_LENGTH) < len(history_str):
                follower_outcome = history_str[i + DNA_PATTERN_LENGTH]
                
                # Assign a weight based on recency: more recent matches get higher weight
                # Example: If pattern matches in the last 10 possible positions, give it double weight.
                weight = 1
                if i >= (len(history_str) - DNA_PATTERN_LENGTH - 10): 
                    weight = 2 
                
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

# 2. Momentum Tracker
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
            
    if last_streak_length >= 3:
        return last_outcome, min(1.0, 0.5 + (last_streak_length - 3) * 0.1)
    
    if len(history_str) >= 4 and history_str[-4:] in ["PBPB", "BPBP"]:
        predicted_outcome = 'P' if history_str[-1] == 'B' else 'B'
        return predicted_outcome, 0.65
    
    return None, 0

# 3. Intuition (Simple Pattern Matching & Counter Bias - Improved: Dynamic Confidence)
def analyze_intuition(history_str):
    if len(history_str) < 3:
        return None, 0, False

    last_3 = history_str[-3:]
    last_2 = history_str[-2:]
    
    # Counter Bias Logic
    if len(history_str) >= COUNTER_BIAS_STREAK_THRESHOLD:
        last_outcome = history_str[-1]
        streak_count = 0
        for i in reversed(range(len(history_str))):
            if history_str[i] == last_outcome:
                streak_count += 1
            else:
                break
            
            # This break condition is crucial for correctly counting streak_count
            # If the current character is not the same as last_outcome, the streak is broken
            # so we should stop counting and exit the loop.
            # Example: BBBP, if last_outcome is P, streak_count is 1.
            # If last_outcome is B, then B is 1, B is 2, B is 3. Then it encounters P and breaks.
            
            # The current loop correctly breaks when the character doesn't match last_outcome.
            # So, the streak_count should be correct.
            
        if streak_count >= COUNTER_BIAS_STREAK_THRESHOLD:
            # Reconstruct the exact streak pattern that just occurred
            streak_pattern = history_str[len(history_str) - streak_count:]
            
            continue_count = 0 # How many times this exact streak pattern continued with the same outcome
            break_count = 0    # How many times this exact streak pattern broke (changed outcome)
            
            # Iterate through history to find all occurrences of this exact streak pattern
            # and check what happened next.
            # We need to ensure we don't count the current streak itself in the stats.
            # So, range goes up to len(history_str) - streak_count - 1
            # Or, we can exclude the very last instance later.
            
            # Let's adjust loop to prevent self-counting and avoid IndexError
            for i in range(len(history_str) - streak_count):
                # Ensure there's a character after the pattern to check continuation/break
                if (i + streak_count) < len(history_str): 
                    if history_str[i : i + streak_count] == streak_pattern:
                        # Check if this is not the current streak itself.
                        # The current streak starts at len(history_str) - streak_count
                        if i == (len(history_str) - streak_count):
                            # This is the current streak, do not count for break/continue stats.
                            continue 
                            
                        # If it's an older instance of the same pattern
                        if history_str[i + streak_count] == last_outcome:
                            continue_count += 1
                        else:
                            break_count += 1
            
            total_instances = continue_count + break_count
            if total_instances > 0:
                if break_count > continue_count: # If it breaks more often than it continues
                    # Scale confidence from COUNTER_PREDICTION_THRESHOLD up to 0.85 based on break rate
                    # Formula: min(Max_Conf, Base_Conf + (Break_Rate * (Max_Conf - Base_Conf)))
                    dynamic_counter_conf = min(0.85, COUNTER_PREDICTION_THRESHOLD + (break_count / total_instances) * (0.85 - COUNTER_PREDICTION_THRESHOLD))
                    return ('P' if last_outcome == 'B' else 'B'), dynamic_counter_conf, True
                elif continue_count == 0 and total_instances >= 2: # If it never continued in at least 2 instances (strong indication to counter)
                    return ('P' if last_outcome == 'B' else 'B'), COUNTER_PREDICTION_THRESHOLD, True # Use default strong threshold
    
    # Simple Intuition Patterns (e.g., Two-cut, Ping-pong)
    # These are general patterns, not strictly 'counter' but 'follow the established reversal'
    if last_3 == "BBP" or last_3 == "PBB": # Two B's then P, or two P's then B
        return ('P' if last_3[-1] == 'B' else 'B'), 0.6, False # Predict the opposite of the last
    if last_3 == "PPB" or last_3 == "BPP":
        return ('B' if last_3[-1] == 'P' else 'P'), 0.6, False # Predict the opposite of the last
    
    # Simple Ping-Pong
    if last_2 == "BP" or last_2 == "PB":
        return ('B' if last_2[-1] == 'P' else 'P'), 0.55, False # Predict opposite
        
    return None, 0, False # No strong intuition pattern found

# Main prediction function (now accepts history_list from app.py)
def predict_outcome(history_list):
    # Get history string from the list of dicts
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
    
    # If no modules made a prediction, return 'no pattern'
    if not predictions:
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    # Prioritize Counter prediction if it's highly confident from Intuition
    # This loop now correctly iterates over predictions and prioritizes a strong 'counter' prediction
    for p in predictions:
        if p.get('is_counter', False) and p['confidence'] >= COUNTER_PREDICTION_THRESHOLD:
            return {"prediction": p['outcome'], 
                    "confidence": p['confidence'], 
                    "predicted_by": [p['source']], # Only list the source that made this strong counter
                    "is_counter": True}

    # If no strong counter, combine other predictions
    outcome_scores = Counter()
    outcome_sources = {} # To keep track of which module predicted which outcome
    is_any_counter_in_other_preds = False # To check if any of the non-strong-counter preds were still 'counter'

    for p in predictions:
        # Only include non-counter or weak-counter predictions here for general combination
        if not p.get('is_counter', False) or p['confidence'] < COUNTER_PREDICTION_THRESHOLD:
            outcome_scores[p['outcome']] += p['confidence']
            if p['outcome'] not in outcome_sources:
                outcome_sources[p['outcome']] = []
            outcome_sources[p['outcome']].append(p['source'])
            if p.get('is_counter', False): # Mark if any of these were still 'counter' (but not strong enough to prioritize)
                is_any_counter_in_other_preds = True

    if not outcome_scores: # If all predictions were strong counters and that's already returned, or no general preds.
        return {"prediction": "ไม่พบรูปแบบ", "confidence": 0, "predicted_by": [], "is_counter": False}

    # Sort outcomes by combined confidence score
    sorted_outcomes = sorted(outcome_scores.items(), key=lambda item: item[1], reverse=True)
    
    best_outcome = sorted_outcomes[0][0]
    # Average confidence is total score divided by number of contributing sources
    best_confidence = sorted_outcomes[0][1] / len(outcome_sources[best_outcome])
    
    # Final check against general prediction threshold
    if best_confidence >= PREDICTION_THRESHOLD:
        return {"prediction": best_outcome, 
                "confidence": best_confidence, 
                "predicted_by": outcome_sources[best_outcome],
                "is_counter": is_any_counter_in_other_preds} # Indicate if *any* source suggested counter, even if not the primary one
    else:
        return {"prediction": "ไม่ชัดเจน", "confidence": best_confidence, "predicted_by": outcome_sources[best_outcome], "is_counter": is_any_counter_in_other_preds}
