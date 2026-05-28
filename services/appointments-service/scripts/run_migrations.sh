#!/bin/bash
set -e

MIGRATIONS_DIR="/app/migrations"

if [ -d "$MIGRATIONS_DIR" ]; then
    for f in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$f" ]; then
            echo "Running migration: $(basename $f)"
            if command -v psql &> /dev/null; then
                psql "$DATABASE_URL" -f "$f" || echo "Warning: migration failed or no DATABASE_URL"
            else
                echo "psql not available, skipping migration"
            fi
        fi
    done
else
    echo "No migrations directory found at $MIGRATIONS_DIR"
fi