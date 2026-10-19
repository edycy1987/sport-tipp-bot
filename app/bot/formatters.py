from datetime import datetime

def format_pick(pick: str) -> str:
    return {"H": "Hazai", "D": "Döntetlen", "A": "Vendég",
            "OVER": "Over 2.5", "UNDER": "Under 2.5"}.get(pick, pick)

def format_slip(legs: list[dict], total_odd: float) -> str:
    if not legs:
        return "📭 Ma nincs értékelhető tipp a szűrők alapján."
        
    lines = ["<b>🎯 Profi Szelvény Elemzés</b>\n"]
    
    for i, l in enumerate(legs, 1):
        ko = l["kickoff"].strftime("%m-%d %H:%M") if isinstance(l["kickoff"], datetime) else "?"
        
        lines.append(f"{i}. <b>{l['home']} – {l['away']}</b> ({ko})")
        lines.append(f"👉 Tipp: <b>{format_pick(l['pick'])}</b> @ {l['odd']:.2f} | Modell: {l['confidence']*100:.1f}%")
        
        # Itt jön a részletes indoklás
        if "analysis" in l and l["analysis"]:
            lines.append(f"{l['analysis']}")
        lines.append("---") 

    lines.append(f"💰 <b>Összesített odds: {total_odd:.2f}</b>")
    lines.append("⚠️ <i>Statisztikai tipp, nem garancia. Felelős játék 18+!</i>")
    
    return "\n".join(lines)
