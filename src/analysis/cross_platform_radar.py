import sqlite3
import pandas as pd
import re
from datetime import datetime
from collections import defaultdict

DB_PATH = 'viral_data.db'

def normalize_text(text):
    """Nettoie le texte pour faciliter la comparaison"""
    # Minuscule, enlève les #, garde que les lettres/chiffres
    text = text.lower()
    text = text.replace('#', '')
    text = re.sub(r'[^\w\s]', '', text)
    return text

def get_tokens(text):
    """Transforme une phrase en ensemble de mots-clés (set)"""
    # On exclut les "stop words" courants (anglais/français) pour réduire le bruit
    STOP_WORDS = {'le', 'la', 'les', 'de', 'du', 'des', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'is', 'and', 'et', 'vs', 'sur'}
    words = normalize_text(text).split()
    return set(w for w in words if w not in STOP_WORDS and len(w) > 2)

def calculate_similarity(text1, text2):
    """Calcule un score de similarité (Jaccard Index) entre deux titres"""
    set1 = get_tokens(text1)
    set2 = get_tokens(text2)
    
    if not set1 or not set2:
        return 0.0
        
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def find_cross_platform_opportunities():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. On récupère tout ce qui a bougé depuis 24h
    query = """
    SELECT t.id, t.topic, t.niche, m.platform, m.velocity_score, m.volume
    FROM trends t
    JOIN trend_metrics m ON t.id = m.trend_id
    WHERE m.timestamp > datetime('now', '-1 day')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("⚠️ Pas assez de données récentes.")
        return

    print(f"🔄 Analyse de {len(df)} signaux bruts pour trouver les corrélations...")
    
    # 2. Clustering (Regroupement des sujets similaires)
    # Structure : clusters = { 'mot_cle_principal': [ {trend_data}, {trend_data} ] }
    clusters = []
    
    # On trie par volume pour traiter les gros sujets en premier (ce seront nos "Ancres")
    df = df.sort_values(by='volume', ascending=False)
    
    processed_ids = set()
    
    for idx, row in df.iterrows():
        if row['id'] in processed_ids:
            continue
            
        # Nouveau cluster
        current_cluster = {
            'main_topic': row['topic'],
            'niche': row['niche'],
            'platforms': {row['platform']},
            'trends': [row],
            'total_score': row['velocity_score']
        }
        processed_ids.add(row['id'])
        
        # On cherche des correspondances dans le reste de la liste
        for comp_idx, comp_row in df.iterrows():
            if comp_row['id'] in processed_ids:
                continue
                
            # Si c'est la même niche, on compare le texte
            if comp_row['niche'] == row['niche']:
                score = calculate_similarity(row['topic'], comp_row['topic'])
                
                # SEUIL DE DÉTECTION : 0.3 (30% de mots communs suffisent souvent pour un match)
                # Ex: "GTA 6 Trailer" (3 mots) vs "#GTA6 Leaks" (2 mots) -> "gta6" commun
                if score >= 0.3 or (normalize_text(row['topic']) in normalize_text(comp_row['topic'])):
                    current_cluster['platforms'].add(comp_row['platform'])
                    current_cluster['trends'].append(comp_row)
                    current_cluster['total_score'] += comp_row['velocity_score']
                    processed_ids.add(comp_row['id'])
        
        clusters.append(current_cluster)

    # 3. Filtrage : On ne garde que les clusters "Multi-Plateformes"
    gold_opportunities = [c for c in clusters if len(c['platforms']) >= 2]
    
    # Affichage Rapport
    print(f"\n💎 CROSS-PLATFORM RADAR | {datetime.now().strftime('%Y-%m-%d')}")
    print("="*60)
    
    if not gold_opportunities:
        print("❌ Aucun signal croisé détecté pour l'instant.")
        print("   Conseil : Attends que les collecteurs tournent un peu plus ou baisse le seuil.")
    
    for opp in sorted(gold_opportunities, key=lambda x: x['total_score'], reverse=True):
        platforms_str = " + ".join(opp['platforms'])
        print(f"\n🔥 SUJET VALIDÉ : {opp['main_topic']}")
        print(f"   📊 Score Global : {int(opp['total_score'])} | Niche : {opp['niche']}")
        print(f"   🌐 Sources : {platforms_str}")
        print("   ------------------------------------------------")
        for t in opp['trends']:
            print(f"    - [{t['platform']}] {t['topic']} (Vol: {t['volume']})")

if __name__ == "__main__":
    find_cross_platform_opportunities()