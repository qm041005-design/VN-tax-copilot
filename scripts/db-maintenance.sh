#!/bin/sh
# Run INSIDE the PostgreSQL container after stopping application writers.
set -eu
umask 077
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

case "${1:-}" in
  inspect)
    psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1 -c \
      "SELECT row_to_json(counts) FROM (SELECT
        (SELECT count(*) FROM legal_documents) AS legal_documents,
        (SELECT count(*) FROM legal_chunks) AS legal_chunks,
        (SELECT count(*) FROM matters) AS matters,
        (SELECT count(*) FROM research_history) AS research_history) counts"
    ;;
  backup)
    target=${2:?Usage: backup /tmp/demo.dump}
    if [ -e "$target" ]; then
      echo "Backup exists. Choose a new filename: $target" >&2
      exit 1
    fi
    temporary="${target}.partial.$$"
    trap 'rm -f "$temporary"' EXIT HUP INT TERM
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file="$temporary"
    pg_restore --list "$temporary" > /dev/null
    mv "$temporary" "$target"
    trap - EXIT HUP INT TERM
    echo "Backup ready: $target"
    ;;
  migrate)
    directory=${2:?Usage: migrate /tmp/migrations}
    tables=$(psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1 \
      -c "SELECT to_regclass('public.legal_documents') IS NOT NULL AND to_regclass('public.legal_chunks') IS NOT NULL")
    if [ "$tables" != "t" ]; then
      echo "Legal tables are missing. Follow the fresh-install runbook for an empty database." >&2
      exit 1
    fi
    for migration in "$directory"/*.sql; do
      test -f "$migration" || { echo "No SQL migrations found: $directory" >&2; exit 1; }
      echo "Applying $(basename "$migration") to $POSTGRES_DB"
      psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f "$migration"
    done
    ;;
  restore)
    archive=${2:?Usage: restore /tmp/demo.dump new_database_name}
    restored=${3:?Choose a NEW database name}
    case "$restored" in
      ''|[!a-z]*|*[!a-z0-9_]*) echo "Use a lowercase database name with letters, digits and underscores." >&2; exit 1 ;;
    esac
    if [ "$restored" = "$POSTGRES_DB" ] || [ "${#restored}" -gt 63 ]; then
      echo "Choose a different database name, at most 63 characters." >&2
      exit 1
    fi
    pg_restore --list "$archive" > /dev/null
    # createdb fails if the destination exists. Never overwrite the live database.
    createdb -U "$POSTGRES_USER" --maintenance-db=postgres "$restored"
    pg_restore -U "$POSTGRES_USER" --dbname="$restored" --exit-on-error \
      --single-transaction --no-owner --no-privileges "$archive"
    echo "Restored to $restored. The original database $POSTGRES_DB is unchanged."
    ;;
  *)
    echo "Usage: sh db-maintenance.sh inspect | backup FILE | migrate DIRECTORY | restore FILE NEW_DB" >&2
    exit 2
    ;;
esac
