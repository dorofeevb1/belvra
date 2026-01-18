#!/bin/bash

set -e

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
    sleep 0.1
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
    sleep 0.1
done
echo "Redis started"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
