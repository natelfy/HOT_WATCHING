import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'viral_data.db'

def show_dashboard():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT 
        t.niche,
        t.topic,
        m.volume,
        m.velocity_score,
        m.platform
    FROM trends t
    JOIN trend_metrics m ON t.id = m.trend_id
    WHERE m.timestamp > datetime('now', '-1 day') -- Seulement les dernières 24h
    ORDER BY m.velocity_score DESC
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        
        print(f"\n🚀 VIRAL WATCH DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        if df.empty:
            print("⚠️ Aucune donnée récente. Lance les collecteurs !")
            return

        for niche in ['Sport', 'Cinema', 'Music']:
            print(f"\n📱 NICHE: {niche.upper()}")
            subset = df[df['niche'] == niche].head(5)
            
            if subset.empty:
                print("   (Pas de données)")
                continue
                
            for i, row in subset.iterrows():
                print(f" {i+1}. [Score: {int(row['velocity_score'])}] {row['topic'][:60]}...")
                print(f"     Source: {row['platform']} | Vol: {row['volume']}")
                
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    show_dashboard()