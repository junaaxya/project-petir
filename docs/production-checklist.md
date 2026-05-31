# Production Checklist

Go-live steps for PetirDashboard. Server lab runs the stack via Docker Compose
behind the existing **nginx + Cloudflare Tunnel**; the Raspberry Pi 5 runs the
edge sync worker. Neither machine needs a public IP — see
[deployment-topology.md](./deployment-topology.md).

## 0. Pre-flight (one-time)

- [ ] **One repo, two machines.** Use a single Git repo for both the Pi and the
      lab server (do NOT split into two — it risks wire-contract drift). Each
      machine clones the same repo and runs only its part. Pull options (full
      clone vs sparse checkout) are in
      [deployment-topology.md](./deployment-topology.md#satu-repo-dua-mesin--cara-menarik-kode).
- [ ] `git init` is safe: `.gitignore` excludes `.env`, `.venv/`, `node_modules/`,
      `web/.next/`, and `*.db` / `*.db.backup-*` (edge DB copies). Verify nothing
      sensitive is staged before the first commit.
- [ ] Generate strong secrets:
      `openssl rand -base64 24` (Postgres), `openssl rand -hex 32` (dashboard key).

## 1. Server lab — bring up the stack

```bash
git clone <repo-url> petir && cd petir
cp .env.example .env          # fill POSTGRES_PASSWORD + auth choice (see step 4)
docker compose up -d --build  # postgres + server + web
docker compose ps             # all healthy
docker compose logs server    # confirm "alembic upgrade head" ran to 0004
```

- Postgres is **not** published to the host (`expose` only) — reachable only by
  the server container.
- Server runs `alembic upgrade head` on start (migrations 0001→0004).
- `NEXT_PUBLIC_API_BASE` is empty → the dashboard calls the API with relative
  `/api` paths (same origin via nginx). It is baked at **build** time via a
  Docker build ARG; changing it requires a rebuild (`docker compose build web`).

## 2. nginx + Cloudflare Tunnel (host)

- [ ] nginx proxies `/api/` → `127.0.0.1:8000` and `/` → `127.0.0.1:3000`.
- [ ] `cloudflared` ingress points the public hostname at nginx (`http://localhost:80`).
- [ ] Browse `https://<domain>` → dashboard loads; `https://<domain>/api/health/latest`
      responds. Full config in [nginx-cloudflare.md](./nginx-cloudflare.md).

## 3. Register the edge node → get its token

On the server lab (inside the server container or a venv with DATABASE_URL set):

```bash
cd server
python scripts/register_node.py rpi-lab-01 --name "Lab rooftop" --location "Building A"
# prints NODE_TOKEN once — copy it for the Pi's edge/.env
```

For docker compose:
```bash
docker compose exec server python scripts/register_node.py rpi-lab-01 --name "Lab rooftop"
```

Rotate later without downtime: `... register_node.py rpi-lab-01 --rotate`
(old token keeps working until the next rotation).

## 4. Secure the public dashboard (choose one)

The dashboard is reachable on the public internet via the tunnel. Do NOT leave it open.

- **Option A — built-in API key**: set `DASHBOARD_AUTH_ENABLED=true` and a strong
  `DASHBOARD_API_KEY` in `.env`; the browser must send `X-API-Key`.
- **Option B — Cloudflare Access (recommended)**: keep `DASHBOARD_AUTH_ENABLED=false`
  and put a Cloudflare Access policy (email/SSO) on the hostname. Auth happens at
  the edge; no key to manage in-app.

Ingest write-path is always protected by per-node bearer tokens (step 3) — this
choice only concerns the read-path dashboard.

## 5. Raspberry Pi 5 — deploy the edge worker

Clone the same repo on the Pi; it runs only the edge parts (stays lightweight,
no Node/web toolchain). Use `--sparse` to keep only edge folders on disk
(see [deployment-topology.md](./deployment-topology.md#satu-repo-dua-mesin--cara-menarik-kode)):

```bash
ssh pi@<pi-host>
git clone <repo-url> petir && cd petir
cp edge/.env.example edge/.env   # set SERVER_URL=https://<domain>, NODE_ID, NODE_TOKEN, EDGE_DB_PATH
```

- [ ] Inspect live schema (read-only): `cd edge && python -m migrations.inspect "$EDGE_DB_PATH"`.
- [ ] `bash scripts/bootstrap-edge.sh` (add `--sparse` to trim the checkout to
      edge folders only) — venv + install + **backup-first** additive migration +
      one dry-run cycle. Confirm dry-run exit code (0 ok / 1 partial / 2 failed).
- [ ] `sudo bash scripts/install-edge-systemd.sh` — installs + enables **only**
      `petir-sync.timer`. It does NOT touch the live `weather-ingest` /
      `lightning-ingest` services.
- [ ] Updates later: `git pull` (sparse checkout is preserved) then re-run
      `bash scripts/bootstrap-edge.sh`.

Full procedure + rollback: [edge-deploy.md](./edge-deploy.md) and
[edge-migration.md](./edge-migration.md).

## 6. First real sync — order matters (anti data-loss)

The cursor advances past quarantined rows, so the contract must match the firmware
BEFORE the first sync. The current contract (v2.0.0) is already validated against
real Pi data (110459 rows, 0 rejected) — see [edge-schema-drift.md](./edge-schema-drift.md).

1. Confirm server is on contract **v2** (it is — `CONTRACT_VERSION = 2.0.0`).
2. Edge ships with the v2 normalize layer (`healthy→ok`, `warning→warn`,
   `noisy→noise`, `active→activity`).
3. Enable the timer; cursors start at zero → full history ingests cleanly.
4. Watch the first cycle:
   ```bash
   sudo systemctl start petir-sync.service
   journalctl -u petir-sync.service -n 50 --no-pager
   # confirm ingest services untouched:
   systemctl is-active weather-ingest lightning-ingest
   ```
5. On the server, confirm rows landing and rejected ≈ 0:
   `GET https://<domain>/api/ingest/runs`.

## 7. Post-deploy verification

- [ ] Dashboard shows live data on all pages (Ringkasan, Cuaca, Petir, Kesehatan, Kualitas).
- [ ] `/api/ingest/runs` shows recent accepted runs with `rejected: 0`.
- [ ] Kesehatan page freshness is "fresh" shortly after a sync cycle.
- [ ] Backups: schedule periodic `pg_dump` of the Postgres volume.
- [ ] Retention: the `retention_policies` table is seeded (migration 0003); wire a
      scheduled call to `/api/admin/retention/run` if you want automatic pruning.

## Rollback

- **Server**: `docker compose down` (data persists in the `petir_pg` volume);
  `alembic downgrade` is reversible to any prior revision.
- **Edge**: disable the timer (`sudo systemctl disable --now petir-sync.timer`);
  the additive migration is reversible (drop triggers / `sync_state` / `meta` /
  `change_seq_counter`) and never modified existing data rows. The live ingest
  services were never touched.
