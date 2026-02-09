"""
Hook Generator — Produces a copy-paste prompt for ChatGPT/Claude
to generate viral video hooks from today's top trends.
"""
from datetime import datetime
from sqlalchemy import text
from src.models.base import Session, init_db


def generate_viral_brief():
    session = Session()

    results = session.execute(text("""
        SELECT t.niche, t.topic, m.volume, m.velocity_score, m.platform
        FROM trends t
        JOIN trend_metrics m ON t.id = m.trend_id
        WHERE m.timestamp > datetime('now', '-1 day')
        ORDER BY m.velocity_score DESC
    """)).fetchall()

    session.close()

    if not results:
        print("⚠️ Pas assez de données. Lance les collecteurs d'abord !")
        return

    lines = []

    lines.append("--- COPY PASTE THIS INTO CHATGPT / CLAUDE ---")
    lines.append("\n# ROLE")
    lines.append("Tu es un expert en scénarisation de contenu viral pour TikTok/Reels.")
    lines.append("Ta mission : Transformer des sujets d'actualité en scripts vidéo à haute rétention.")
    lines.append("\n# OBJECTIF")
    lines.append("Pour chaque sujet ci-dessous, génère 3 HOOKS (Accroches) différents :")
    lines.append("1. Le Hook 'Polémique' (Diviser pour régner).")
    lines.append("2. Le Hook 'Storytelling' (Une histoire incroyable).")
    lines.append("3. Le Hook 'Éducatif' (Le Saviez-vous ?).")
    lines.append(f"\n# DONNÉES DU {datetime.now().strftime('%d/%m/%Y')}")

    seen = set()
    for niche in ['Sport', 'Cinema', 'Music']:
        subset = [r for r in results if r[0] == niche][:2]
        for row in subset:
            topic = row[1]
            if topic in seen:
                continue
            seen.add(topic)
            lines.append(f"\n## SUJET ({niche.upper()}) : {topic}")
            lines.append(f"- Intensité virale : {int(row[3])} points")
            lines.append(f"- Source : {row[4]}")
            lines.append(f"- Instruction : Trouve un angle inattendu.")

    lines.append("\n# FORMAT DE SORTIE")
    lines.append("Pour chaque Hook :")
    lines.append("- Visuel : [Ce qu'on voit à l'écran en 5 mots]")
    lines.append("- Audio : [Première phrase exacte, < 15 mots]")
    lines.append("- Pourquoi ça marche : [1 phrase technique]")

    print("\n".join(lines))


if __name__ == "__main__":
    generate_viral_brief()