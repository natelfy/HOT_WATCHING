import requests
import time
from datetime import datetime
from src.models.base import Session, Trend, TrendMetric, init_db

# Configuration des Sources (Subreddits clés pour tes niches)
SOURCES = {
    'Cinema': ['movies', 'boxoffice', 'netflix', 'cine'],
    'Sport': ['soccer', 'nba', 'formula1', 'ligue1'],
    'Music': ['popheads', 'hiphopheads', 'music', 'kpop']
}

# User-Agent personnalisé OBLIGATOIRE pour ne pas être bloqué par Reddit
HEADERS = {
    "User-Agent": "ViralWatchBot/1.0 (by /u/TesBesoinsDeData)"
}

def fetch_subreddit_hot(subreddit):
    """Récupère les posts 'Hot' d'un subreddit via l'API JSON publique"""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=20"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 429:
            print(f"⚠️ Trop de requêtes pour r/{subreddit}. Pause...")
            time.sleep(2)
            return []
            
        if response.status_code != 200:
            print(f"❌ Erreur r/{subreddit}: {response.status_code}")
            return []

        data = response.json()
        posts = []
        
        # Navigation dans le JSON Reddit: data -> children -> data
        for item in data.get('data', {}).get('children', []):
            post = item['data']
            
            # On ignore les posts épinglés (souvent des règles, pas des trends)
            if post.get('stickied'):
                continue
                
            posts.append({
                'title': post['title'],
                'score': post['score'],       # Net Upvotes
                'comments': post['num_comments'], # Volume de discussion
                'url': post['url'],
                'created_utc': post['created_utc']
            })
            
        return posts

    except Exception as e:
        print(f"❌ Erreur Exception r/{subreddit}: {e}")
        return []

def process_reddit_trends():
    session = Session()
    print("🚀 Démarrage du scan Reddit...")

    total_new = 0
    
    for niche, subreddits in SOURCES.items():
        print(f"\n--- Analyse Niche: {niche} ---")
        
        for sub in subreddits:
            posts = fetch_subreddit_hot(sub)
            print(f"  r/{sub}: {len(posts)} posts récupérés")
            
            for post in posts:
                topic = post['title'][:250] # On tronque pour la DB
                
                # Le score de vélocité brut ici est simple : Score + Commentaires
                # (Dans la V2 on divisera par le temps écoulé depuis le post)
                virality_score = post['score'] + post['comments']
                
                # Filtre : On ne garde que ce qui a un minimum d'impact
                if virality_score < 100:
                    continue

                # 1. Upsert Trend
                trend_obj = session.query(Trend).filter_by(topic=topic).first()
                
                if not trend_obj:
                    trend_obj = Trend(topic=topic, niche=niche)
                    session.add(trend_obj)
                    total_new += 1
                    session.commit() # Commit pour avoir l'ID
                
                # 2. Ajout Métrique
                metric = TrendMetric(
                    trend_id=trend_obj.id,
                    platform='Reddit',
                    volume=post['score'], # On utilise le score comme proxy du volume
                    velocity_score=float(virality_score)
                )
                session.add(metric)
            
            # Pause éthique pour respecter l'API
            time.sleep(1)
    
    session.commit()
    session.close()
    print(f"\n✅ Ingestion terminée. {total_new} nouveaux sujets détectés.")

if __name__ == "__main__":
    init_db()
    process_reddit_trends()