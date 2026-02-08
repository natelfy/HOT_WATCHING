import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'viral_data.db'

def generate_viral_brief():
    conn = sqlite3.connect(DB_PATH)
    
    # On récupère le Top 1 de chaque niche pour l'exemple
    query = """
    SELECT t.niche, t.topic, m.volume, m.velocity_score, m.platform
    FROM trends t
    JOIN trend_metrics m ON t.id = m.trend_id
    WHERE m.timestamp > datetime('now', '-1 day')
    ORDER BY m.velocity_score DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("⚠️ Pas assez de données. Lance les collecteurs d'abord !")
        return

    # On prépare le buffer de texte
    prompt_buffer = []
    
    # Header du Prompt (Le Cerveau)
    prompt_buffer.append("--- COPY PASTE THIS INTO CHATGPT / CLAUDE ---")
    prompt_buffer.append("\n# ROLE")
    prompt_buffer.append("Tu es un expert en scénarisation de contenu viral pour TikTok/Reels.")
    prompt_buffer.append("Ta mission : Transformer des sujets d'actualité en scripts vidéo à haute rétention.")
    prompt_buffer.append("\n# OBJECTIF")
    prompt_buffer.append("Pour chaque sujet ci-dessous, génère 3 HOOKS (Accroches visuelles et verbales) différents :")
    prompt_buffer.append("1. Le Hook 'Polémique' (Diviser pour régner).")
    prompt_buffer.append("2. Le Hook 'Storytelling' (Une histoire incroyable).")
    prompt_buffer.append("3. Le Hook 'Éducatif' (Le Saviez-vous ?).")
    
    prompt_buffer.append("\n# CONTEXTE & DONNÉES (TOP TRENDS DU JOUR)")
    
    # Injection des données réelles
    processed_topics = set()
    
    for niche in ['Sport', 'Cinema', 'Music']:
        subset = df[df['niche'] == niche].head(2) # Top 2 par niche
        
        for _, row in subset.iterrows():
            if row['topic'] in processed_topics: continue
            processed_topics.add(row['topic'])
            
            prompt_buffer.append(f"\n## SUJET ({niche.upper()}) : {row['topic']}")
            prompt_buffer.append(f"- Intensité virale : {int(row['velocity_score'])} points")
            prompt_buffer.append(f"- Source : {row['platform']} (Preuve sociale forte)")
            prompt_buffer.append(f"- Instruction Spécifique : Trouve un angle inattendu, ne raconte pas juste les faits.")

    prompt_buffer.append("\n# FORMAT DE SORTIE ATTENDU")
    prompt_buffer.append("Pour chaque Hook :")
    prompt_buffer.append("- Visuel : [Décris ce qu'on voit à l'écran en 5 mots]")
    prompt_buffer.append("- Audio : [La première phrase exacte à dire, < 15 mots]")
    prompt_buffer.append("- Pourquoi ça marche : [Explication technique en 1 phrase]")
    
    # Affichage du résultat
    print("\n".join(prompt_buffer))

if __name__ == "__main__":
    generate_viral_brief()