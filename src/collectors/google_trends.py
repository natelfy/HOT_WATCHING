import requests
import json
from src.models.base import Session, Trend, TrendMetric, init_db
from datetime import datetime

# URL de l'API interne (celle utilisée par le navigateur)
# ns=15 est le namespace pour les Daily Trends
API_URL = "https://trends.google.com/trends/api/dailytrends?hl=fr&geo=FR&ns=15"

# Headers pour se faire passer pour un navigateur (Anti-404)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://trends.google.com/trends/trendingsearches/daily?geo=FR&hl=fr"
}

NICHES = {
    'Cinema': ['film', 'movie', 'trailer', 'netflix', 'série', 'cinéma', 'acteur', 'disney', 'marvel', 'star'],
    'Sport': ['match', 'score', 'goal', 'ufc', 'nba', 'football', 'ligue', 'jo', 'athlète', 'vs', 'prix', 'course'],
    'Music': ['lyrics', 'concert', 'album', 'song', 'feat', 'rap', 'musique', 'clip', 'chanteur']
}

def fetch_internal_api():
    """Récupère les données JSON brutes de l'API interne"""
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Erreur HTTP: {response.status_code}")
            return []
            
        # Google ajoute un préfixe de sécurité ")]}'," qu'il faut retirer
        content = response.text
        if content.startswith(")]}',"):
            content = content[5:]
            
        data = json.loads(content)
        
        # Navigation dans le JSON complexe de Google
        # Structure: default -> trendingSearchesDays -> [0] (Aujourd'hui) -> trendingSearches
        daily_data = data.get('default', {}).get('trendingSearchesDays', [])
        
        if not daily_data:
            return []
            
        # On prend le premier jour disponible
        todays_trends = daily_data[0].get('trendingSearches', [])
        
        clean_items = []
        for item in todays_trends:
            title = item.get('title', {}).get('query', 'Inconnu')
            traffic_str = item.get('formattedTraffic', '0')
            
            # Nettoyage "20K+" -> 20000
            traffic = int(traffic_str.replace('K+', '000').replace('M+', '000000').replace(',', '').replace('+', ''))
            
            # Google donne aussi des articles liés (contexte)
            articles = item.get('articles', [])
            context = articles[0].get('title', '') if articles else ''
            
            clean_items.append({
                'topic': title,
                'volume': traffic,
                'context': context
            })
            
        return clean_items

    except Exception as e:
        print(f"❌ Erreur Parsing: {e}")
        return []

def process_trends():
    session = Session()
    trends_data = fetch_internal_api()
    
    if not trends_data:
        print("⚠️ Aucun flux récupéré via l'API interne.")
        return

    print(f"🔍 {len(trends_data)} sujets récupérés via API Interne...")

    count_new = 0
    for item in trends_data:
        topic = item['topic']
        volume = item['volume']
        
        # 1. Classification
        assigned_niche = 'General'
        topic_lower = topic.lower() + " " + item['context'].lower()
        
        for niche, keywords in NICHES.items():
            if any(k in topic_lower for k in keywords):
                assigned_niche = niche
                break
        
        # 2. Upsert Trend
        trend_obj = session.query(Trend).filter_by(topic=topic).first()
        
        if not trend_obj:
            trend_obj = Trend(topic=topic, niche=assigned_niche)
            session.add(trend_obj)
            count_new += 1
            session.commit()
            print(f"  [+] {topic} ({assigned_niche}) - Vol: {item['volume']}")
        
        # 3. Métrique
        metric = TrendMetric(
            trend_id=trend_obj.id,
            platform='Google',
            volume=volume,
            velocity_score=0.0 
        )
        session.add(metric)
    
    session.commit()
    session.close()
    print(f"✅ Ingestion terminée. {count_new} nouveaux sujets.")

if __name__ == "__main__":
    init_db()
    process_trends()