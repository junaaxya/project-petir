# Petir 2 — Nelayan Sungailiat

Repository-only deployment preparation for `nelayan-sungailiat.petirlabs.com`.
This directory does not modify Petir 1, Cloudflare, DNS, or Raspberry Pi services.

## Isolation

- Compose project: `petir2_nelayan` (declared by top-level `name`)
- Web host bind: `127.0.0.1:3020:3000`
- API and PostgreSQL: internal Compose network only
- PostgreSQL data: `/mnt/data/apps/petir2-nelayan/postgres`
- Database: `petir2_nelayan`
- Runtime DB role: `petir2_app` (non-superuser, DML only)
- Migration DB role: `petir2_migrator` (non-superuser, schema owner)
- Container/network names: generated from the unique Compose project; no `container_name`
- Images: immutable Git-SHA tag plus OCI revision label

## Static validation (safe in Phase 1)

```bash
cd deploy/petir2-nelayan
docker compose --env-file .env.example -f compose.yml config -q
docker compose --env-file .env.example -f compose.yml config
```

Do not run `up`, `down`, or the migration profile during Phase 1.

## Approved deployment sequence (future phase only)

1. Verify the release SHA and build immutable `petir2-server`/`petir2-web` images.
2. Create the dedicated deployment and HDD directories with approved ownership.
3. Create a mode-0600 runtime `.env` using new, Petir-2-only credentials.
4. Start only Petir 2 PostgreSQL; verify its dedicated bind mount and health.
5. Run the explicit one-shot migration:
   `docker compose --profile migration run --rm --no-deps migrate`.
6. Start Petir 2 server and web; verify `http://127.0.0.1:3020` and its unique marker.
7. Configure an exact Cloudflare hostname route to `http://localhost:3020` only after approval.
8. Prove the hostname no longer returns Petir 1 before registering or syncing the Petir 2 node.

The backend image starts only Uvicorn. It never runs Alembic automatically.

## Authentication gate

Node ingest uses a separate per-node bearer token and validates that the token's node
matches the envelope `node_id`. Dashboard/admin read routes must be protected before
public routing. Prefer Cloudflare Access for browser access, with an explicit policy that
keeps `/api/ingest/sync-batch` available to registered node tokens. The built-in
`X-API-Key` mode is suitable only for controlled API clients; the browser UI does not
persist or embed that secret.

## Rollback boundary

Before the hostname route changes, rollback is simply stopping/removing only the
`petir2_nelayan` stateless services after approval. Never use project `deploy`, never
run commands from `/srv/apps/petirdashboard`, and never remove Petir 1 resources.
