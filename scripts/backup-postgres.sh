#!/bin/sh
set -eu

if [ ! -f .env ]; then
    echo "Erreur : créez .env à partir de .env.example avant de lancer une sauvegarde." >&2
    exit 1
fi

set -a
. ./.env
set +a

backup_dir=${BACKUP_DIR:-./backups}
umask 077
mkdir -p "$backup_dir"
backup_file="$backup_dir/skyconnect-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$backup_file"
echo "Sauvegarde créée : $backup_file"
