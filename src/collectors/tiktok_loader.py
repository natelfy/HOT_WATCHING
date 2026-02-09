import math
from playwright.sync_api import sync_playwright
from src.models.base import Session, init_db, upsert_trend, add_metric

# ─── CONFIG ──────────────────────────────────────────────────────────
URL_HASHTAGS = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
URL_SONGS = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en"

NICHE_KEYWORDS = {
    'Cinema': ['movie', 'netflix', 'film', 'actor', 'cinema', 'disney', 'series', 'show',
               'marvel', 'trailer', 'premiere', 'oscar', 'hbo', 'anime'],
    'Sport':  ['football', 'nba', 'sport', 'fitness', 'gym', 'ufc', 'soccer', 'basketball',
               'f1', 'tennis', 'running', 'workout', 'match', 'goal'],
    'Music':  ['song', 'music', 'concert', 'lyrics', 'rap', 'pop', 'singer', 'album',
               'dj', 'beat', 'dance', 'kpop', 'hiphop', 'remix'],
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def intercept_tiktok_data(page_type: str = "hashtag") -> list[dict]:
    """Launch headless browser, navigate to Creative Center, intercept API JSON."""
    data_captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "api" in response.url and "json" in ct:
                    body = response.json()
                    items = body.get("data", {}).get("list", [])
                    if items:
                        print(f"  ⚡ Intercepté: {len(items)} items")
                        data_captured.extend(items)
            except Exception:
                pass

        page.on("response", handle_response)

        target = URL_HASHTAGS if page_type == "hashtag" else URL_SONGS
        print(f"🕵️ TikTok: loading {page_type}...")

        try:
            page.goto(target, timeout=60000)
            page.wait_for_timeout(5000)
            # Scroll to trigger lazy-loaded API calls
            for _ in range(3):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  ❌ TikTok navigation error: {e}")

        browser.close()

    return data_captured


def classify_niche(name: str) -> str:
    name_lower = name.lower()
    for niche, keywords in NICHE_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return niche
    return 'General'


def compute_velocity(view_count: int, rank: int, total: int) -> float:
    """
    TikTok velocity: if it's on Creative Center trending, it's already viral.
    Score = log-volume base + rank position bonus.
    """
    base = math.log10(max(view_count, 1)) * 15
    rank_bonus = max(0, (total - rank) / max(total, 1)) * 40
    # Minimum floor: being on trending page = at least 50
    return round(max(base + rank_bonus, 50.0), 1)


def process_tiktok_trends():
    session = Session()
    print("🚀 TikTok: démarrage de l'interception...")

    hashtags = intercept_tiktok_data("hashtag")

    if not hashtags:
        print("  ⚠️ Aucun hashtag intercepté (le DOM a peut-être changé).")
        session.close()
        return

    count_new = 0
    total = len(hashtags)

    for rank, item in enumerate(hashtags):
        name = item.get("hashtag_name", "") or item.get("name", "")
        if not name:
            continue

        view_count = item.get("view_count", 0) or item.get("video_views", 0) or 0
        # Sometimes view_count is a string
        if isinstance(view_count, str):
            view_count = int(view_count.replace(',', '').replace('+', '') or 0)

        niche = classify_niche(name)
        velocity = compute_velocity(view_count, rank, total)
        topic_name = f"#{name}"

        trend = upsert_trend(session, topic_name, niche, 'TikTok')
        was_new = trend.first_detected == trend.last_updated
        add_metric(session, trend, 'TikTok', view_count, velocity)

        if was_new:
            count_new += 1
            print(f"  [+] {topic_name} ({niche}) — Views: {view_count:,} — Vel: {velocity}")

    session.commit()
    session.close()
    print(f"✅ TikTok: terminé. {count_new} nouveaux sujets.")


if __name__ == "__main__":
    init_db()
    process_tiktok_trends()