#!/bin/sh
set -e

echo "Initializing database tables..."
python -m app.scripts.create_tables

echo "Running database migrations..."
alembic upgrade head

echo "Seeding initial data if needed..."
python -m app.scripts.seed_auto

echo "Seeding questionnaire catalogue if needed..."
python -m app.scripts.seed_questionnaire

echo "Starting application..."
exec "$@"
