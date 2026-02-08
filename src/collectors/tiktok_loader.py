import time
import json
from playwright.sync_api import sync_playwright
from datetime import datetime
from src.models.base import Session, Trend, TrendMetric, init_db

# URLs Cibles (TikTok Creative Center)
URL_HASHTAGS = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
URL_SONGS = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en"

# Mappage des industries TikTok vers tes Niches
# (On filtre a posteriori pour garder le script flexible)
NICHE_KEYWORDS = {
    'Cinema': ['movie', 'netflix', 'film', 'actor', 'cinema', 'disney'],
    'Sport': ['football', 'nba', 'sport', 'fitness', 'gym', 'ufc'],
    'Music': ['song', 'music', 'concert', 'lyrics', 'rap', 'pop']
}

def intercept_tiktok_data(page_type="hashtag"):
    """
    Lance un navigateur, va sur le Creative Center, et intercepte le JSON de l'API.
    """
    data_captured = []
    
    with sync_playwright() as p:
        # Lancement du navigateur (Headless = sans interface graphique)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Fonction de callback déclenchée à chaque réponse réseau
        def handle_response(response):
            # On cherche les réponses JSON provenant de l'API Creative Radical
            if "api/v1" in response.url and "json" in response.headers.get("content-type", ""):
                try:
                    json_body = response.json()
                    # Structure typique : data -> list ou data -> promotions
                    if "data" in json_body:
                        # On capture tout ce qui ressemble à une liste
                        extracted = json_body.get("data", {}).get("list", [])
                        if extracted:
                            print(f"  ⚡ INTERCEPTION RÉUSSIE : {len(extracted)} items trouvés via {response.url[-40:]}...")
                            data_captured.extend(extracted)
                except:
                    pass # On ignore les erreurs de parsing sur les requêtes non pertinentes

        # On branche l'écouteur
        page.on("response", handle_response)

        # Navigation vers la cible
        target_url = URL_HASHTAGS if page_type == "hashtag" else URL_SONGS
        print(f"🕵️  Infiltration de : {target_url} ...")
        
        try:
            page.goto(target_url, timeout=60000)
            # On scrolle un peu pour déclencher le chargement des données
            page.wait_for_timeout(5000) # Pause pour laisser l'API répondre
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"❌ Timeout ou Erreur Nav: {e}")
        
        browser.close()
    
    return data_captured

def process_tiktok_trends():
    session = Session()
    print("🚀 Démarrage du module TikTok Interceptor...")
    
    # 1. Récupération des Hashtags
    hashtags = intercept_tiktok_data("hashtag")
    
    count_new = 0
    for item in hashtags:
        # Extraction sécurisée des données (la structure change parfois)
        name = item.get("hashtag_name", "")
        if not name: continue
        
        # Le volume est souvent caché dans des clés bizarres ou absent
        # On utilise une valeur par défaut ou une métrique disponible
        # Ici on simule une extraction de volume relatif
        view_count = item.get("view_count", 0) 
        
        # Classification Niche
        assigned_niche = 'General'
        for niche, keywords in NICHE_KEYWORDS.items():
            if any(k in name.lower() for k in keywords):
                assigned_niche = niche
                break
        
        # Logique Upsert
        topic_name = f"#{name}"
        trend_obj = session.query(Trend).filter_by(topic=topic_name).first()
        
        if not trend_obj:
            trend_obj = Trend(topic=topic_name, niche=assigned_niche)
            session.add(trend_obj)
            session.commit()
            count_new += 1
            print(f"  [+] Nouveau Hashtag Viral : {topic_name} ({assigned_niche})")

        # Métrique (On stocke le rang ou le volume)
        metric = TrendMetric(
            trend_id=trend_obj.id,
            platform='TikTok',
            volume=view_count if view_count else 0,
            velocity_score=100.0 # Par définition, si c'est ici, c'est viral
        )
        session.add(metric)

    # 2. Récupération des Sons (Optionnel pour ta niche Musique)
    # songs = intercept_tiktok_data("song")
    # (Même logique de boucle ici si tu veux activer la musique)

    session.commit()
    session.close()
    print(f"✅ Ingestion TikTok terminée. {count_new} nouveaux sujets.")

if __name__ == "__main__":
    init_db()
    process_tiktok_trends()