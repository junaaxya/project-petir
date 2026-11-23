#!/bin/sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${PETIR2_MIGRATOR_DB_PASSWORD:?PETIR2_MIGRATOR_DB_PASSWORD is required}"
: "${PETIR2_APP_DB_PASSWORD:?PETIR2_APP_DB_PASSWORD is required}"

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=migrator_password="$PETIR2_MIGRATOR_DB_PASSWORD" \
  --set=app_password="$PETIR2_APP_DB_PASSWORD" <<'EOSQL'
SELECT format('CREATE ROLE petir2_migrator LOGIN PASSWORD %L', :'migrator_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'petir2_migrator')
\gexec
SELECT format('ALTER ROLE petir2_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'migrator_password')
\gexec

SELECT format('CREATE ROLE petir2_app LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'petir2_app')
\gexec
SELECT format('ALTER ROLE petir2_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'app_password')
\gexec

ALTER DATABASE petir2_nelayan OWNER TO petir2_migrator;
REVOKE ALL ON DATABASE petir2_nelayan FROM PUBLIC;
GRANT CONNECT ON DATABASE petir2_nelayan TO petir2_migrator, petir2_app;

ALTER SCHEMA public OWNER TO petir2_migrator;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO petir2_migrator;
GRANT USAGE ON SCHEMA public TO petir2_app;

ALTER DEFAULT PRIVILEGES FOR ROLE petir2_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO petir2_app;
ALTER DEFAULT PRIVILEGES FOR ROLE petir2_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO petir2_app;
EOSQL
