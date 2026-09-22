#!/bin/sh
# Wait for PostgreSQL and Redis to be ready before starting the application

set -e

echo "Starting AttendAI backend..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-attendai}" -q; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete!"

# Start the application
echo "Starting application..."
exec "$@"
