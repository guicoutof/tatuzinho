#!/usr/bin/env bash
set -euo pipefail

# Push data from local PostgreSQL to Supabase
# Usage: ENV=production ./scripts/db_push.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load Supabase connection string from .env.prod
if [ ! -f ".env.prod" ]; then
  echo "❌ .env.prod not found. Create it first."
  exit 1
fi

source .env.prod

LOCAL_DB="postgresql://postgres:postgres@localhost:5432/tatuzinho_dev"
REMOTE_DB="$DATABASE_URL"

echo "📦 Dumping local database..."
pg_dump "$LOCAL_DB" \
  --no-owner \
  --no-acl \
  --data-only \
  -f /tmp/tatuzinho_dump.sql

echo "📤 Uploading to Supabase..."
psql "$REMOTE_DB" < /tmp/tatuzinho_dump.sql

echo "✅ Done! Data pushed to Supabase."
