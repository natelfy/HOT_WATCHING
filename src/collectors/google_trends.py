import requests
import json
from datetime import datetime
from src.models.base import Session, Trend, TrendMetric, init_db, upsert_trend, add_metric

# ─── CONFIG ──────────────────────────────────────────────────────────
API_URL = "https://trends.google.com/trends/api/dailytrends?hl=fr&geo=FR&ns=15"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://trends.google.com/trends/trendingsearches/daily?geo=FR&hl=fr",
}

NICHES = {
    'Cinema': ['film', 'movie', 'trailer', 'netflix', 'série', 'cinéma', 'acteur', 'actrice',
               'disney', 'marvel', 'hbo', 'prime video', 'star wars', 'dc', 'oscar', 'cannes'],
    'Sport':  ['match', 'score', 'goal', 'ufc', 'nba', 'football', 'ligue', 'jo', 'athlète',
               'vs', 'prix', 'course', 'tennis', 'f1', 'psg', 'real madrid', 'champions league',
               'olympique', 'transfert', 'blessure'],
    'Music':  ['lyrics', 'concert', 'album', 'song', 'feat', 'rap', 'musique', 'clip',
               'chanteur', 'chanteuse', 'grammy', 'spotify', 'tournée', 'tour', 'single'],
}


def parse_volume(traffic_str: str) -> int:
    """Convert '200K+' -> 200000, '1M+' -> 1000000."""
    s = traffic_str.replace(',', '').replace('+', '').strip()
    if s.upper().endswith('K'):
        return int(float(s[:-1]) * 1_000)
    if s.upper().endswith('M'):
        return int(float(s[:-1]) * 1_000_000)
    try:
        return int(s)
    except ValueError:
        return 0


def fetch_daily_trends() -> list[dict]:
    """Fetch raw trending searches from Google's internal JSON API."""
    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Google HTTP {resp.status_code}")
            return []

        content = resp.text
        if content.startswith(")]}',"): 
            content = content[5:]

        data = json.loads(content)
        days = data.get('default', {}).get('trendingSearchesDays', [])
        if not days:
            return []

        results = []
        for day in days[:2]:  # Today + yesterday for velocity comparison
            for item in day.get('trendingSearches', []):
                title = item.get('title', {}).get('query', '')
                traffic = parse_volume(item.get('formattedTraffic', '0'))
                articles = item.get('articles', [])
                context = articles[0].get('title', '') if articles else ''

                results.append({
                    'topic': title,
                    'volume': traffic,
                    'context': context,
                })
        return results

    except Exception as e:
        print(f"❌ Google Parsing Error: {e}")
        return []


def classify_niche(topic: str, context: str) -> str:
    """Match topic+context against niche keywords."""
    combined = (topic + " " + context).lower()
    for niche, keywords in NICHES.items():
        if any(kw in combined for kw in keywords):
            return niche
    return 'General'


def compute_velocity(volume: int, rank: int, total: int) -> float:
    """
    Velocity Score for Google Trends.
    
    Formula:  base_volume_score + rank_boost + freshness_bonus
    
    - base: log-scale of raw search volume (prevents 1M+ from dominating everything)
    - rank_boost: higher rank in Google's own trending = stronger signal
    - freshness: top-of-list items get a recency bonus
    """
    import math
    base = math.log10(max(volume, 1)) * 20          # 200K -> ~106, 10K -> ~80
    rank_boost = max(0, (total - rank) / total) * 30  # #1 gets +30, last gets ~0
    return round(base + rank_boost, 1)


def process_trends():
    session = Session()
    items = fetch_daily_trends()

    if not items:
        print("⚠️ Google: aucun flux récupéré.")
        return

    print(f"🔍 Google: {len(items)} sujets récupérés")
    count_new = 0
    total = len(items)

    for rank, item in enumerate(items):
        topic = item['topic']
        volume = item['volume']
        niche = classify_niche(topic, item['context'])
        velocity = compute_velocity(volume, rank, total)

        trend = upsert_trend(session, topic, niche, 'Google')
        if trend.id is None:
            session.flush()
        was_new = trend.first_detected == trend.last_updated
        add_metric(session, trend, 'Google', volume, velocity)

        if was_new:
            count_new += 1
            print(f"  [+] {topic} ({niche}) — Vol: {volume:,} — Vel: {velocity}")

    session.commit()
    session.close()
    print(f"✅ Google: terminé. {count_new} nouveaux sujets.")


if __name__ == "__main__":
    init_db()
    process_trends()