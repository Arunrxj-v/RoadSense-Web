#!/bin/sh
set -eu

if [ "${RUN_DB_INIT:-false}" = "true" ]; then
  flask --app wsgi:app init-db
fi

exec "$@"
