#!/bin/sh

set -e

echo "Run apply migrations.."
alembic upgrade head
echo "Migrations applied"


exec "$@"
