import os
import json
import math
from datetime import datetime

from sqlalchemy import text
from src.models.base import Session, init_db
from src.analysis.cross_platform_radar import find_cross_platform_opportunities

# ─── CONFIG ──────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Niche emojis for visual scanning
NICHE_EMOJI = {
    'Cinema': '🎬',
    'Sport': '⚽',
    'Music': '🎵',
    'General': '📌',
}

PLATFORM_EMOJI = {
    'Google': '🔍',
    'Reddit': '🟠',
    'TikTok': '🎵',
}


def build_briefing() -> dict:
    """Build the Discord embed payload from current data."""
    session = Session()

    # Top trends by velocity (last 24h)
    top_trends = session.execute(text("""
        SELECT t.topic, t.niche, m.platform, m.velocity_score, m.volume
        FROM trends t
        JOIN trend_metrics m ON t.id = m.trend_id
        WHERE m.timestamp > datetime('now', '-1 day')
        ORDER BY m.velocity_score DESC
        LIMIT 30
    """)).fetchall()

    session.close()

    # Cross-platform gold opportunities
    gold = find_cross_platform_opportunities()

    # ─── BUILD EMBED ─────────────────────────────────────────────────
    now = datetime.now().strftime("%A %d %B %Y — %H:%M")

    embeds = []

    # Main header embed
    header = {
        "title": f"🚀 VIRAL BRIEFING — {datetime.now().strftime('%d/%m/%Y')}",
        "description": f"*Généré le {now}*\nVoici les sujets à plus fort potentiel viral pour aujourd'hui.",
        "color": 0xFF4500,  # Reddit orange
    }
    embeds.append(header)

    # Gold opportunities section
    if gold:
        gold_lines = []
        for i, opp in enumerate(gold[:5], 1):
            niche_e = NICHE_EMOJI.get(opp['niche'], '📌')
            platforms = " + ".join(
                PLATFORM_EMOJI.get(p, p) for p in sorted(opp['platforms'])
            )
            gold_lines.append(
                f"**{i}. {opp['main_topic']}** {niche_e}\n"
                f"   Score: `{opp['score']}` | {platforms}"
            )

        embeds.append({
            "title": "💎 SIGNAUX CROSS-PLATFORM (Or massif)",
            "description": "\n\n".join(gold_lines) if gold_lines else "Aucun signal croisé.",
            "color": 0xFFD700,
        })

    # Top by niche
    for niche in ['Cinema', 'Sport', 'Music']:
        emoji = NICHE_EMOJI.get(niche, '📌')
        niche_trends = [t for t in top_trends if t[1] == niche][:5]

        if not niche_trends:
            continue

        lines = []
        for i, t in enumerate(niche_trends, 1):
            plat_e = PLATFORM_EMOJI.get(t[2], t[2])
            lines.append(
                f"**{i}.** {t[0][:60]}\n"
                f"   {plat_e} Vel: `{int(t[3])}` | Vol: `{t[4]:,}`"
            )

        embeds.append({
            "title": f"{emoji} TOP {niche.upper()}",
            "description": "\n\n".join(lines),
            "color": 0x5865F2,
        })

    return {"embeds": embeds}


def send_briefing():
    """Send the briefing to Discord via webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL not set. Printing to stdout instead.")
        payload = build_briefing()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    import requests

    payload = build_briefing()
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            print(f"✅ Briefing envoyé sur Discord à {datetime.now().strftime('%H:%M')}")
        else:
            print(f"❌ Discord error: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Discord send failed: {e}")


if __name__ == "__main__":
    send_briefing()