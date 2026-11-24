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

## Runtime networking fix

The release Compose file includes the two settings proven necessary by the
internal Phase 2 deployment:

- `HOSTNAME=0.0.0.0` makes the Next.js standalone server listen on the
  container interfaces instead of only the generated container hostname;
- web joins both `internal` (to reach `server:8000`) and `host_ingress` (to
  publish the loopback-only host port).

PostgreSQL and the backend remain attached only to `internal`, which is marked
`internal: true`. Neither service has a published host port. The only host bind
remains `127.0.0.1:3020:3000`.

The old out-of-repository `compose.runtime.yml` workaround is not needed for a
release containing this fix. Do not combine both definitions after upgrading;
validate the rendered Compose model first.

## Runtime site identity

The frontend reads these public, non-secret variables at request time:

- `PETIR_SITE_NAME`
- `PETIR_STATION_VERSION`
- `PETIR_SITE_ID`
- `PETIR_PUBLIC_DOMAIN` (hostname only, without scheme or path)

The Petir 2 template defaults to `Nelayan Sungailiat`, station `2.0`, site ID
`nelayan-sungailiat`, and `nelayan-sungailiat.petirlabs.com`. When the variables
are absent, the same image keeps the Petir 1-compatible `PetirDashboard`
identity. Do not put credentials in these variables or rename them to
`NEXT_PUBLIC_*`; the server passes only the resolved public identity to the UI.

## Static validation (safe in Phase 1)

```bash
cd deploy/petir2-nelayan
docker compose --env-file .env.example -f compose.yml config -q
docker compose --env-file .env.example -f compose.yml config
python ../../scripts/check_petir2_compose.py
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
matches the envelope `node_id`. Privileged API authentication is separate from public
monitoring and fails closed when `PETIR2_ADMIN_AUTH_MODE=disabled`:

- `api_key` accepts server-only admin/operator keys for controlled API clients;
- `cloudflare_access` verifies the Access JWT signature, issuer, audience, expiry,
  and email allowlist inside the backend;
- `/api/admin/*` and browser siren routes require the admin role;
- `/api/system/*` and `/api/ingest/runs` require operator or admin;
- machine ingest and siren callbacks never use browser authentication.

The dedicated template also disables `/openapi.json`, `/docs`, `/redoc`, and every
siren route. `/healthz` remains available for the internal container healthcheck.
Do not enable siren routes or add operators during the public pilot. The built-in
`X-API-Key` mode is not for browser storage; use verified Cloudflare Access JWTs for
browser-admin traffic after the Access application details are approved.

The complete endpoint classification and Phase 3 recommendation are in
[`../../docs/petir2-public-access-security.md`](../../docs/petir2-public-access-security.md).

## Rollback boundary

Before the hostname route changes, rollback is simply stopping/removing only the
`petir2_nelayan` stateless services after approval. Never use project `deploy`, never
run commands from `/srv/apps/petirdashboard`, and never remove Petir 1 resources.
