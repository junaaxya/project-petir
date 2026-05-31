# Reverse proxy: nginx + Cloudflare Tunnel

The lab server has no public IP. Public access is provided by a **Cloudflare Tunnel**
(`cloudflared`) terminating TLS at the Cloudflare edge and forwarding to a local
**nginx**, which reverse-proxies to the dashboard containers.

```
Browser ── HTTPS ──> Cloudflare edge ── tunnel ──> cloudflared ──> nginx ──> {server:8000, web:3000}
```

Caddy is intentionally **not** used here; TLS is handled by Cloudflare and routing
by the existing nginx. `docker compose` only exposes the app ports on the host:

- `server` → `${SERVER_PORT:-8000}`
- `web` → `${WEB_PORT:-3000}`

## nginx site

Path-based split: everything under `/api` goes to the FastAPI server, everything
else to the Next.js app. Adjust `server_name` and ports to match your `.env`.

```nginx
server {
    listen 80;
    server_name petir.lab-ilkom.my.id;

    client_max_body_size 16m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Cloudflare already terminates TLS, so `listen 80` on the loopback side is fine.
Do not add a separate `listen 443 ssl` block for this service unless you also
want direct LAN TLS.

## cloudflared

Point the tunnel ingress at nginx (default `:80`):

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: petir.lab-ilkom.my.id
    service: http://localhost:80
  - service: http_status:404
```

```bash
cloudflared tunnel route dns <TUNNEL_ID> petir.lab-ilkom.my.id
cloudflared tunnel run <TUNNEL_ID>
```

## Frontend API base

The dashboard and API share ONE origin (both behind this nginx), so the browser
uses **relative** `/api/...` paths. Leave the build-time base EMPTY:

```
NEXT_PUBLIC_API_BASE=
```

With an empty base the dashboard calls `/api/...` relative to its own origin,
which nginx proxies to the server container. No CORS config is needed.

> `NEXT_PUBLIC_*` is inlined at BUILD time (passed as a Docker build ARG, see
> web/Dockerfile + docker-compose.yml). Only set a full URL here if you ever
> serve the API on a different origin than the dashboard.

## Bring up the stack

```bash
cp .env.example .env   # set credentials; leave NEXT_PUBLIC_API_BASE empty (same-origin)
docker compose up -d --build   # postgres + server + web (no proxy container)
```

nginx and `cloudflared` run on the host and are managed outside compose.
