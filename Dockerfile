FROM python:3.13-slim

# Répertoire de travail
WORKDIR /app

# Variables d'environnement pour logs et pip
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système légères
RUN apt-get update && \
    apt-get install -y \
        postgresql-client \
        default-libmysqlclient-dev \
        build-essential \
        pkg-config \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copier uniquement requirements pour profiter du cache Docker
COPY requirements.txt .

# Installer Python packages (upgrade pip + installer en une couche)
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY . .

# Créer un utilisateur non-root pour exécuter l'app
RUN groupadd -r app && useradd -r -g app app

# Donner la propriété des dossiers à l'utilisateur app
RUN chown -R app:app /app

# Basculer sur l'utilisateur non-root
USER app

# Expose (documentational)
EXPOSE 8000

# CMD est géré par docker-compose (gunicorn)
