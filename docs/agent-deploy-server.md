# Prompt Deploy — Agent Server Lab (Server + Web)

Prompt siap-pakai untuk Hermes/agent AI yang menjalankan deploy komponen
**server + web** PetirDashboard di server lab. Salin blok di bawah ke agent tersebut.

> Urutan koordinasi: jalankan agent **server ini DULU**. Di langkah 8 ia
> menghasilkan `NODE_TOKEN` — serahkan token itu ke agent Pi
> ([agent-deploy-pi.md](./agent-deploy-pi.md)) sebelum Pi mulai sync.

---

```
PERAN: Kamu men-deploy komponen SERVER + WEB dari project PetirDashboard di server lab ini.

KONTEKS SISTEM:
- Server lab TIDAK punya IP publik. Akses publik lewat Cloudflare Tunnel (cloudflared) + nginx
  yang SUDAH ADA dan berjalan di host ini.
- Tugasmu: jalankan stack (PostgreSQL + FastAPI + Next.js) via Docker Compose, lalu sambungkan
  ke nginx + tunnel yang sudah ada (ADITIF — jangan rusak konfigurasi nginx/tunnel lain).
- Repo: https://github.com/junaaxya/project-petir.git
- Baca docs/production-checklist.md dan docs/nginx-cloudflare.md di repo — ikuti itu.

⛔ ATURAN KESELAMATAN:
1. JANGAN commit/expose secret. File .env JANGAN di-commit (sudah di .gitignore).
2. JANGAN publish PostgreSQL ke internet. Compose memakai `expose` (hanya antar-container) — biarkan begitu.
3. Konfigurasi nginx + cloudflared bersifat ADITIF: tambahkan server block / ingress untuk
   hostname PetirDashboard saja. JANGAN ubah/hapus site atau tunnel lain yang sudah ada.
4. Dashboard akan PUBLIK lewat tunnel — WAJIB diamankan (lihat langkah 5). Jangan biarkan terbuka.

LANGKAH:
1. Pastikan Docker + Docker Compose v2 terpasang.
2. `git clone https://github.com/junaaxya/project-petir.git ~/project-petir && cd ~/project-petir`
3. `cp .env.example .env` lalu isi dengan secret KUAT:
   - POSTGRES_PASSWORD=$(openssl rand -base64 24)
   - NEXT_PUBLIC_API_BASE=   (KOSONGKAN — dashboard pakai path relatif /api lewat nginx, same-origin)
   - CORS_ALLOW_ORIGINS=     (kosong — same-origin, CORS tidak diperlukan)
   - Pilih mode auth dashboard di langkah 5.
4. `docker compose up -d --build`
   - Verifikasi: `docker compose ps` semua healthy; `docker compose logs server` menunjukkan
     "alembic upgrade head" sampai revision 0004 dan uvicorn listen di 8000.
   - Catatan: NEXT_PUBLIC_API_BASE adalah BUILD-time (build ARG di web/Dockerfile). Jika diubah,
     wajib rebuild: `docker compose build web`.
5. AMANKAN DASHBOARD (pilih satu):
   - Opsi A (bawaan): set DASHBOARD_AUTH_ENABLED=true + DASHBOARD_API_KEY=$(openssl rand -hex 32)
     di .env, lalu `docker compose up -d`. Browser harus kirim header X-API-Key.
   - Opsi B (DIREKOMENDASIKAN): biarkan DASHBOARD_AUTH_ENABLED=false, lalu pasang Cloudflare Access
     (kebijakan email/SSO) pada hostname di Cloudflare. Auth di edge, tanpa kelola key.
   (Write-path ingest selalu dilindungi token per-node — ini hanya soal read-path dashboard.)
6. nginx (host) — TAMBAHKAN server block (lihat docs/nginx-cloudflare.md) untuk hostname kalian:
     location /api/ → proxy_pass http://127.0.0.1:8000;
     location /     → proxy_pass http://127.0.0.1:3000;  (dengan header Upgrade/Connection untuk websocket)
   Cloudflare sudah terminasi TLS, jadi `listen 80` di sisi loopback cukup.
   `sudo nginx -t && sudo systemctl reload nginx`  (reload, JANGAN restart kalau bisa).
7. cloudflared — TAMBAHKAN ingress untuk hostname PetirDashboard mengarah ke nginx
   (service: http://localhost:80), lalu route DNS-nya. JANGAN ubah ingress hostname lain.
8. DAFTARKAN NODE EDGE (untuk Pi):
   `docker compose exec server python scripts/register_node.py rpi-lab-01 --name "Lab rooftop"`
   → cetak NODE_TOKEN SEKALI. Berikan token ini ke operator/agent Pi dengan aman (jangan kirim via channel tidak aman).

VERIFIKASI (wajib lapor):
- `curl -s https://<domain>/api/health/latest` → balas JSON (lewat tunnel+nginx).
- Buka https://<domain> di browser → dashboard tampil (jika Opsi A, sertakan header X-API-Key).
- `docker compose ps` semua Up/healthy.
- PostgreSQL TIDAK dapat diakses dari luar host (cek `docker compose port postgres 5432` → tidak ter-publish).
- Setelah Pi mulai sync: `curl https://<domain>/api/ingest/runs` menunjukkan run dengan rejected=0.

ROLLBACK:
- `docker compose down` (data tetap di volume petir_pg). Migrasi Alembic reversible.
- Hapus server block nginx + ingress cloudflared yang kamu tambahkan jika perlu.

LAPORKAN: status tiap verifikasi di atas, mode auth yang dipilih, NODE_TOKEN sudah diserahkan ke
pihak Pi (ya/tidak), dan masalah yang ditemui. Jangan klaim sukses tanpa output curl /api/health/latest.
```

---

Referensi pendukung di repo: [production-checklist.md](./production-checklist.md),
[nginx-cloudflare.md](./nginx-cloudflare.md), [deployment-topology.md](./deployment-topology.md).
