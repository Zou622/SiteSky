# Mise en production

## Avant le premier lancement

1. Créez un serveur Linux à jour, installez Docker Engine et le plugin Compose.
2. Pointez les enregistrements DNS `skyconnect-sa.com` et `www.skyconnect-sa.com` vers son IP publique.
3. Copiez `.env.example` vers `.env`, puis remplacez chaque valeur d'exemple par un secret unique. Ne versionnez jamais ce fichier.
4. Ouvrez uniquement les ports TCP 80 et 443. PostgreSQL et Gunicorn restent internes à Docker.
5. Créez les certificats TLS avant le démarrage de Nginx :

```sh
mkdir -p certbot/www certbot/conf
docker compose run --rm --publish 80:80 certbot certonly --standalone \
  --email admin@skyconnect-sa.com --agree-tos --no-eff-email \
  -d skyconnect-sa.com -d www.skyconnect-sa.com
```

## Lancement

```sh
docker compose build
docker compose up -d
docker compose exec web python manage.py check --deploy
docker compose ps
```

La première exécution crée automatiquement les tables Django et les fichiers statiques.

## Exploitation

- Sauvegardez PostgreSQL quotidiennement : `./scripts/backup-postgres.sh`. Copiez ensuite les archives chiffrées hors du serveur.
- Renouvelez le certificat au moins quotidiennement avec une tâche système :

```sh
docker compose run --rm certbot renew --webroot -w /var/www/certbot && docker compose exec nginx nginx -s reload
```

- Surveillez `docker compose ps`, `docker compose logs --tail=200 web` et les sauvegardes.
- Testez régulièrement une restauration PostgreSQL sur un environnement séparé.
