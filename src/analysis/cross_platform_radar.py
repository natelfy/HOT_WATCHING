import re
import math
from datetime import datetime
from collections import defaultdict

from sqlalchemy import text
from src.models.base import Session, Trend, TrendMetric, init_db

# ─── CONFIG ──────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.25  # Jaccard index minimum for matching
MIN_PLATFORMS = 2            # Minimum platforms for a "gold" opportunity

# Platform weight: cross-platform signals from bigger platforms count more
PLATFORM_WEIGHT = {
    'Google': 1.5,   # Google Trends = mass-market validation
    'TikTok': 1.3,   # TikTok trending = short-form content goldmine
    'Reddit': 1.0,   # Reddit = early signal, niche communities
}

STOP_WORDS = frozenset({
    'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'en', 'au', 'aux',
    'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'is', 'and', 'et',
    'vs', 'sur', 'with', 'from', 'has', 'are', 'was', 'not', 'but',
})


def normalize(text: str) -> str:
    return re.sub(r'[^\w\s]', '', text.lower().replace('#', ''))


def get_tokens(text: str) -> set[str]:
    words = normalize(text).split()
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def jaccard_similarity(a: str, b: str) -> float:
    sa, sb = get_tokens(a), get_tokens(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def substring_match(a: str, b: str) -> bool:
    """Check if one normalized topic contains the other (handles 'GTA 6' vs '#GTA6Leak')."""
    na, nb = normalize(a).replace(' ', ''), normalize(b).replace(' ', '')
    return (len(na) > 3 and na in nb) or (len(nb) > 3 and nb in na)


def compute_opportunity_score(cluster: dict) -> float:
    """
    Final opportunity score combining:
    - Sum of velocity scores (weighted by platform importance)
    - Platform diversity bonus (more platforms = exponentially better)
    - Volume factor
    """
    weighted_velocity = 0.0
    for t in cluster['trends']:
        w = PLATFORM_WEIGHT.get(t['platform'], 1.0)
        weighted_velocity += t['velocity_score'] * w

    platform_bonus = len(cluster['platforms']) ** 1.5  # 2 platforms = 2.8x, 3 = 5.2x
    volume_factor = math.log10(max(cluster['total_volume'], 1))

    return round(weighted_velocity * platform_bonus * (1 + volume_factor * 0.1), 1)


def find_cross_platform_opportunities():
    session = Session()

    # Fetch all metrics from last 24h
    results = session.execute(text("""
        SELECT t.id, t.topic, t.niche, m.platform, m.velocity_score, m.volume
        FROM trends t
        JOIN trend_metrics m ON t.id = m.trend_id
        WHERE m.timestamp > datetime('now', '-1 day')
        ORDER BY m.velocity_score DESC
    """)).fetchall()

    session.close()

    if not results:
        print("⚠️ Pas assez de données récentes pour l'analyse.")
        return []

    print(f"🔄 Analyse de {len(results)} signaux bruts...")

    # Convert to dicts for easier manipulation
    rows = [
        {'id': r[0], 'topic': r[1], 'niche': r[2], 'platform': r[3],
         'velocity_score': r[4] or 0, 'volume': r[5] or 0}
        for r in results
    ]

    # ─── CLUSTERING ──────────────────────────────────────────────────
    clusters = []
    processed = set()

    for row in rows:
        if row['id'] in processed:
            continue

        cluster = {
            'main_topic': row['topic'],
            'niche': row['niche'],
            'platforms': {row['platform']},
            'trends': [row],
            'total_volume': row['volume'],
        }
        processed.add(row['id'])

        for other in rows:
            if other['id'] in processed:
                continue

            # Match within same niche OR if text similarity is very high
            same_niche = other['niche'] == row['niche']
            sim = jaccard_similarity(row['topic'], other['topic'])
            substr = substring_match(row['topic'], other['topic'])

            if same_niche and (sim >= SIMILARITY_THRESHOLD or substr):
                cluster['platforms'].add(other['platform'])
                cluster['trends'].append(other)
                cluster['total_volume'] += other['volume']
                processed.add(other['id'])

        clusters.append(cluster)

    # ─── FILTER & SCORE ──────────────────────────────────────────────
    gold = [c for c in clusters if len(c['platforms']) >= MIN_PLATFORMS]
    for c in gold:
        c['score'] = compute_opportunity_score(c)

    gold.sort(key=lambda x: x['score'], reverse=True)

    # ─── REPORT ──────────────────────────────────────────────────────
    print(f"\n💎 CROSS-PLATFORM RADAR | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    if not gold:
        print("❌ Aucun signal croisé détecté.")
        print("   → Attends que les collecteurs tournent davantage.")
    else:
        for i, opp in enumerate(gold[:15], 1):
            platforms_str = " + ".join(sorted(opp['platforms']))
            print(f"\n🔥 #{i} — {opp['main_topic']}")
            print(f"   📊 Score: {opp['score']} | Niche: {opp['niche']}")
            print(f"   🌐 {platforms_str}")
            for t in opp['trends']:
                print(f"    └─ [{t['platform']}] {t['topic'][:70]} "
                      f"(Vol: {t['volume']:,} | Vel: {t['velocity_score']})")

    return gold


if __name__ == "__main__":
    find_cross_platform_opportunities()