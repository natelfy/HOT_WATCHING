# Utilisation d'une image Python officielle légère
FROM python:3.11-slim-bookworm

# 1. Installation des dépendances système (Cron + Outils)
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. Configuration du répertoire de travail
WORKDIR /app

# 3. Copie des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Installation des navigateurs pour Playwright (TikTok Scraper)
# Cette commande installe Chromium et ses dépendances système Linux
RUN playwright install --with-deps chromium

# 5. Copie du code source
COPY . .

# 6. Configuration du Cron
COPY cronjob /etc/cron.d/viral-cron
# Donner les droits d'exécution
RUN chmod 0644 /etc/cron.d/viral-cron
# Appliquer le cron
RUN crontab /etc/cron.d/viral-cron
# Créer le fichier de log
RUN touch /var/log/cron.log

# 7. Initialisation de la BDD au build (pour être sûr qu'elle existe)
# On lance un script Python simple pour initier les tables
RUN python -c "from src.models.base import init_db; init_db()"

# 8. Commande de démarrage
# On lance cron en premier plan (-f) pour que le conteneur ne s'arrête pas
CMD ["cron", "-f"]