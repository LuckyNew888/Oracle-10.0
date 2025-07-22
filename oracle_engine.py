# oracle_engine.py v1.1

def analyze_patterns(history):
    if len(history) < 20:
        return {"patterns": [], "momentum": [], "recommendation": "รอข้อมูลครบ 20 ตา"}

    patterns = []
    momentum = []

    def last_n(n):
        return history[-n:] if len(history) >= n else []

    seq = ''.join(history)

    # เค้าไพ่: Pingpong (สลับ)
    if any(seq.endswith(p) for p in ["BPBP", "PBPB", "BPBPBP", "PBPBPB"]):
        patterns.append("Pingpong")

    # เค้าไพ่: Dragon
    if len(set(last_n(4))) == 1:
        patterns.append("Dragon")

    # เค้าไพ่: Two-Cut
    if any(seq.endswith(p) for p in ["BBPP", "PPBB", "BBPPBB", "PPBBPP"]):
        patterns.append("Two-Cut")

    # เค้าไพ่: Triple-Cut
    if any(seq.endswith(p) for p in ["BBBPPP", "PPPBBB"]):
        patterns.append("Triple-Cut")

    # One-Two Pattern
    if seq.endswith("BPPBPP") or seq.endswith("PBBPBB"):
        patterns.append("One-Two Pattern")

    # Two-One Pattern
    if seq.endswith("BBPBBP") or seq.endswith("PPBPPB"):
        patterns.append("Two-One Pattern")

    # Broken Pattern
    if any(seq.endswith(p) for p in ["BPBPPBP", "PBPBBBP", "BBPBPP"]):
        patterns.append("Broken Pattern")

    # FollowStreak
    streak_char = history[-1]
    streak_count = 0
    for h in reversed(history):
        if h == streak_char:
            streak_count += 1
        else:
            break
    if streak_count >= 3:
        patterns.append("FollowStreak")

    # Momentum: B3+, P3+
    if history[-1] == "B" and history[-3:] == ["B"] * 3:
        momentum.append("B3+ Momentum")
    if history[-1] == "P" and history[-3:] == ["P"] * 3:
        momentum.append("P3+ Momentum")

    # Momentum: Steady Pingpong
    if any(seq.endswith(p) for p in ["BPBPBPB", "PBPBPBP"]):
        momentum.append("Steady Pingpong")

    # Momentum: Ladder
    if any(seq.endswith(p) for p in ["BPBBPBBB", "PBPPPBBB"]):
        momentum.append("Ladder Momentum")

    recommendation = "วิเคราะห์เสร็จสิ้น" if patterns or momentum else "ยังไม่พบเค้าไพ่ชัดเจน"

    return {
        "patterns": patterns,
        "momentum": momentum,
        "recommendation": recommendation
    }
