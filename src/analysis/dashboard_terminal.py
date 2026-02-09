from datetime import datetime
from sqlalchemy import text
from src.models.base import Session, init_db


def show_dashboard():
    session = Session()

    results = session.execute(text("""
        SELECT t.niche, t.topic, m.volume, m.velocity_score, m.platform
        FROM trends t
        JOIN trend_metrics m ON t.id = m.trend_id
        WHERE m.timestamp > datetime('now', '-1 day')
        ORDER BY m.velocity_score DESC
    """)).fetchall()

    session.close()

    print(f"\n🚀 VIRAL WATCH DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    if not results:
        print("⚠️ Aucune donnée récente. Lance les collecteurs !")
        return

    for niche in ['Sport', 'Cinema', 'Music']:
        print(f"\n📱 NICHE: {niche.upper()}")
        subset = [r for r in results if r[0] == niche][:5]

        if not subset:
            print("   (Pas de données)")
            continue

        for i, row in enumerate(subset, 1):
            print(f"  {i}. [Vel: {int(row[3])}] {row[1][:60]}")
            print(f"     {row[4]} | Vol: {row[2]:,}")


if __name__ == "__main__":
    show_dashboard()