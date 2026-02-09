import requests
import time
import math
from datetime import datetime
from src.models.base import Session, init_db, upsert_trend, add_metric

# ─── CONFIG ──────────────────────────────────────────────────────────
SOURCES = {
    'Cinema': ['movies', 'boxoffice', 'netflix', 'television'],
    'Sport':  ['soccer', 'nba', 'formula1', 'sports'],
    'Music':  ['popheads', 'hiphopheads', 'music', 'kpop'],
}

HEADERS = {
    "User-Agent": "ViralWatchBot/2.0 (trend-monitoring-research)"
}

MIN_ENGAGEMENT = 100   # Minimum (score + comments) to consider


def fetch_subreddit_hot(subreddit: str) -> list[dict]:
    """Fetch 'Hot' posts from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)

        if resp.status_code == 429:
            print(f"  ⚠️ Rate-limited on r/{subreddit}, sleeping 5s...")
            time.sleep(5)
            return []
        if resp.status_code != 200:
            print(f"  ❌ r/{subreddit}: HTTP {resp.status_code}")
            return []

        posts = []
        for item in resp.json().get('data', {}).get('children', []):
            post = item['data']
            if post.get('stickied'):
                continue
            posts.append({
                'title': post['title'][:250],
                'score': post['score'],
                'comments': post['num_comments'],
                'upvote_ratio': post.get('upvote_ratio', 0.5),
                'created_utc': post['created_utc'],
                'url': post.get('permalink', ''),
            })
        return posts

    except Exception as e:
        print(f"  ❌ r/{subreddit} exception: {e}")
        return []


def compute_velocity(score: int, comments: int, upvote_ratio: float, created_utc: float) -> float:
    """
    Time-aware velocity score for Reddit.
    
    Formula: engagement_density × controversy_boost
    
    - engagement_density = (score + comments) / hours_alive
      → A post with 500 upvotes in 2h is WAY more viral than 500 in 24h
    - controversy_boost = if ratio < 0.7, it's polarizing → +20% boost
      (Controversial content = higher engagement potential for short-form)
    """
    now = datetime.utcnow().timestamp()
    hours_alive = max((now - created_utc) / 3600, 0.5)  # floor at 30min

    raw_engagement = score + comments
    density = raw_engagement / hours_alive

    # Controversy multiplier: polarizing posts (ratio 0.5-0.7) drive more comments
    controversy = 1.2 if upvote_ratio < 0.7 else 1.0

    # Log-scale to prevent a single mega-post from dominating
    velocity = math.log10(max(density, 1)) * 40 * controversy

    return round(velocity, 1)


def process_reddit_trends():
    session = Session()
    print("🚀 Reddit: démarrage du scan...")
    total_new = 0

    for niche, subreddits in SOURCES.items():
        print(f"\n  --- {niche} ---")

        for sub in subreddits:
            posts = fetch_subreddit_hot(sub)
            kept = 0

            for post in posts:
                engagement = post['score'] + post['comments']
                if engagement < MIN_ENGAGEMENT:
                    continue

                velocity = compute_velocity(
                    post['score'], post['comments'],
                    post['upvote_ratio'], post['created_utc']
                )

                trend = upsert_trend(session, post['title'], niche, 'Reddit')
                was_new = trend.first_detected == trend.last_updated
                add_metric(session, trend, 'Reddit', post['score'], velocity)

                if was_new:
                    total_new += 1
                kept += 1

            print(f"  r/{sub}: {len(posts)} posts → {kept} retenus")
            time.sleep(1.5)  # Rate-limit politeness

    session.commit()
    session.close()
    print(f"\n✅ Reddit: terminé. {total_new} nouveaux sujets.")


if __name__ == "__main__":
    init_db()
    process_reddit_trends()