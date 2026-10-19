import math

def implied_prob(odd: float) -> float:
    return 1/odd if odd and odd > 1 else 0.0

def expected_value(p_model: float, odd: float) -> float:
    return p_model * odd - 1 if odd and odd > 1 else -1

def poisson_prob(k, lam):
    if lam <= 0: return 0.0
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def calc_poisson_matrix(lam_home, lam_away, max_goals=5):
    p_home_win = p_draw = p_away_win = p_over_25 = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_prob(h, lam_home) * poisson_prob(a, lam_away)
            if h > a: p_home_win += p
            elif h == a: p_draw += p
            else: p_away_win += p
            if h + a > 2.5: p_over_25 += p
    return p_home_win, p_draw, p_away_win, p_over_25

def _generate_analysis(match, pick, market, p_model, odd, ev, lam_h=None, lam_a=None):
    ip = implied_prob(odd)
    diff = p_model - ip
    lines = []
    
    # 1. Value Bet logika szövegesen
    if diff > 0.05:
        lines.append(f"🔥 <b>Value Bet:</b> A modellünk {diff*100:.1f}%-kal magasabbra értékeli ezt az esélyt, mint a fogadóirodák.")
    elif diff > 0:
        lines.append(f"📈 <b>Kis előny:</b> A piaci ár korrekt, de a modell minimális ({diff*100:.1f}%) pluszt lát.")
    else:
        lines.append(f"📊 <b>Piaci alapon:</b> A fogadóiroda kicsit magasabbra árazza ezt az esélyt, de a magas odds miatt mégis megérheti.")

    # 2. Csapat erőviszonyok (Poisson alapján)
    if lam_h is not None and lam_a is not None:
        if market == "1X2":
            if pick == "H":
                if lam_h > lam_a + 0.5: lines.append(f"⚽ A hazai csapat támadóereje dominál (Várható gólok: {lam_h:.2f} vs {lam_a:.2f}).")
                elif lam_h > lam_a: lines.append(f"⚽ Enyhe hazai pálya előny (Várható gólok: {lam_h:.2f} vs {lam_a:.2f}).")
                else: lines.append(f"⚽ Meglepetés tipp: A vendégek a papírforma szerint erősebbek, de itt értéket látunk.")
            elif pick == "A":
                if lam_a > lam_h + 0.5: lines.append(f"⚽ A vendégcsapat jóval erősebb a modell szerint (Várható gólok: {lam_a:.2f} vs {lam_h:.2f}).")
                elif lam_a > lam_h: lines.append(f"⚽ Enyhe vendég fölény (Várható gólok: {lam_a:.2f} vs {lam_h:.2f}).")
                else: lines.append(f"⚽ Meglepetés tipp: A hazaiak a papírforma szerint erősebbek, de itt értéket látunk.")
        elif market == "OU2.5":
            total_lam = lam_h + lam_a
            if pick == "OVER":
                lines.append(f"🥅 A modell {total_lam:.2f} gólt vár összesen, ami magasabb, mint a 2.5-ös határ.")
            else:
                lines.append(f"🛡️ A modell csak {total_lam:.2f} gólt vár összesen, ami alacsonyabb, mint a 2.5-ös határ.")

    # 3. Scraper infók
    if match.scraped_notes:
        clean_notes = match.scraped_notes.replace("[thesportsdb]", "").replace("[fbref]", "").replace("[openligadb]", "").strip()
        if clean_notes:
            lines.append(f"📰 <i>Háttérinfó: {clean_notes[:70]}...</i>")
            
    return "\n".join(lines)

def score_1x2(match) -> list[dict]:
    if not (match.odds_home and match.odds_draw and match.odds_away): return []
    iph, ipd, ipa = implied_prob(match.odds_home), implied_prob(match.odds_draw), implied_prob(match.odds_away)
    tot = iph + ipd + ipa or 1.0
    
    total_goals = 2.6
    if match.odds_over25 and match.odds_under25:
        ipo = implied_prob(match.odds_over25)
        total_goals = 2.6 + (ipo - 0.5) * 2.0

    strength_diff = (iph/tot) - (ipa/tot)
    lam_home = max(0.1, (total_goals / 2) + (strength_diff * 1.5) + 0.1) 
    lam_away = max(0.1, (total_goals / 2) - (strength_diff * 1.5) - 0.1)

    p_h, p_d, p_a, _ = calc_poisson_matrix(lam_home, lam_away)
    s = p_h + p_d + p_a
    p_h, p_d, p_a = p_h/s, p_d/s, p_a/s

    cand = {"H": (p_h, match.odds_home), "D": (p_d, match.odds_draw), "A": (p_a, match.odds_away)}
    out = []
    for pick, (p, odd) in cand.items():
        ev = expected_value(p, odd)
        analysis = _generate_analysis(match, pick, "1X2", p, odd, ev, lam_home, lam_away)
        out.append(dict(market="1X2", pick=pick, odd=odd, confidence=p, value=ev, analysis=analysis))
    return out

def score_ou25(match) -> list[dict]:
    if not (match.odds_over25 and match.odds_under25): return []
    iph, ipd, ipa = implied_prob(match.odds_home or 3.0), implied_prob(match.odds_draw or 3.0), implied_prob(match.odds_away or 3.0)
    tot = iph + ipd + ipa or 1.0
    
    ipo = implied_prob(match.odds_over25)
    total_goals = 2.6 + (ipo - 0.5) * 2.0
    strength_diff = (iph/tot) - (ipa/tot)
    
    lam_home = max(0.1, (total_goals / 2) + (strength_diff * 1.5) + 0.1)
    lam_away = max(0.1, (total_goals / 2) - (strength_diff * 1.5) - 0.1)
    
    _, _, _, p_over = calc_poisson_matrix(lam_home, lam_away)
    p_under = 1.0 - p_over

    out = []
    for pick, p, odd in [("OVER", p_over, match.odds_over25), ("UNDER", p_under, match.odds_under25)]:
        ev = expected_value(p, odd)
        analysis = _generate_analysis(match, pick, "OU2.5", p, odd, ev, lam_home, lam_away)
        out.append(dict(market="OU2.5", pick=pick, odd=odd, confidence=p, value=ev, analysis=analysis))
    return out

def evaluate_match(match) -> list[dict]:
    return score_1x2(match) + score_ou25(match)
