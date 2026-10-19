from app.config import settings

def build_slip(tips: list[dict]) -> tuple[list[dict], float]:
    filtered = [t for t in tips
                if t["confidence"] >= settings.TIP_MIN_CONFIDENCE
                and t["value"] >= settings.TIP_MIN_EV]
    filtered.sort(key=lambda t: t["value"], reverse=True)

    seen_matches = set()
    legs = []
    for t in filtered:
        if t["match_id"] in seen_matches:
            continue
        seen_matches.add(t["match_id"])
        legs.append(t)
        if len(legs) >= settings.TIP_MAX_LEGS:
            break

    total = 1.0
    for l in legs:
        total *= l["odd"]
    return legs, round(total, 2)
