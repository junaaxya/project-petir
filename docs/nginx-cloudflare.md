# Public access: Cloudflare Tunnel → Next.js (web)

The lab server has no public IP. Public access is provided by a **Cloudflare
Tunnel** (`cloudflared`) which terminates TLS at the Cloudflare edge and forwards
to the **Next.js web container on `localhost:3000`**.

```
Browser ── HTTPS ──> Cloudflare edge ── tunnel ──> cloudflared ──> web:3000 (Next.js)
                                                                     ├─ /        → dashboard
                                                                     └─ /api/*   → proxied to server:8000
```

The Cloudflare Tunnel ingress for `petir.lab-ilkom.my.id` points at
**`http://localhost:3000`** (the web service). The dashboard and the API share
that single origin, and **Next.js proxies `/api/*` to the FastAPI server**
internally (over the Docker network) via `rewrites()` in `web/next.config.mjs`.

This means **no nginx is required** for this hostname — the Next.js server is the
single entry point. The API container is not published to the host; the web
container reaches it over the compose network at `http://server:8000`.

## How the /api proxy works

`web/next.config.mjs`:
```js
async rewrites() {
  const target = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
  return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
}
```

- In docker compose, the web container gets `API_PROXY_TARGET=http://server:8000`
  (set in `docker-compose.yml`). `rewrites()` runs on the Next.js **server** and
  reads this at runtime in standalone mode.
- The browser only ever talks to one origin (`https://petir.lab-ilkom.my.id`),
  so `NEXT_PUBLIC_API_BASE` is **empty** (relative `/api` calls). No CORS needed.

## cloudflared ingress

Point the tunnel hostname at the web container's host port (`:3000`):

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: petir.lab-ilkom.my.id
    service: http://localhost:3000
  - service: http_status:404
```

```bash
cloudflared tunnel route dns <TUNNEL_ID> petir.lab-ilkom.my.id
cloudflared tunnel run <TUNNEL_ID>
```

> Additive: only add the `petir.lab-ilkom.my.id` ingress entry. Do not modify
> other hostnames already served by the same tunnel.

## Bring up the stack

```bash
cp .env.example .env   # set credentials; leave NEXT_PUBLIC_API_BASE empty (same-origin)
docker compose up -d --build   # postgres + server + web
```

- `web` publishes `:3000` on the host for the tunnel to reach.
- `server` is `expose`-only (reachable by `web` over the compose network, not the host).
- `postgres` is `expose`-only (reachable by `server` only).

## Optional: nginx in front

If you prefer to route at nginx (e.g. to serve multiple apps on one host port),
point the tunnel at nginx instead and have nginx `proxy_pass` `/` → `web:3000`.
You do NOT need a separate `/api` location — Next.js already proxies `/api`. But
for this single-app deployment, tunnel → `:3000` directly is simplest.
