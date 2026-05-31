# Deployment Topology — Pi 5 ↔ Server Lab (tanpa IP publik)

Dokumen ini menjelaskan **bagian repo mana yang di-deploy ke Raspberry Pi 5** dan
**mana yang ke server lab**, serta **bagaimana keduanya terhubung** padahal
kedua mesin tidak punya IP publik.

## Inti: hanya server lab yang perlu "bisa dijangkau"

Arsitektur ini **PUSH-only** (AGENTS.md non-negotiable #2):

- **Pi yang memulai semua koneksi** → `POST https://<domain>/api/ingest/sync-batch`.
- **Server tidak pernah menghubungi Pi.**

Maka hanya server lab yang butuh endpoint publik. Pi berperan sebagai *client*
biasa — cukup punya **akses internet keluar (outbound)**, persis seperti laptop
yang browsing tanpa IP publik.

Server lab juga tidak punya IP publik, tetapi sudah memakai **Cloudflare Tunnel**.
`cloudflared` membuat koneksi **keluar** ke Cloudflare; Cloudflare (yang memegang
domain publik) meneruskan request masuk melalui tunnel itu. Jadi:

```
 Raspberry Pi 5 (NO public IP)            Cloudflare                Server Lab (NO public IP)
 ─────────────────────────────           ───────────               ──────────────────────────────
 Arduino → weather_edge.db (SQLite)                                 cloudflared  (outbound tunnel)
 sync worker (systemd, single-run)                                       │
        │  HTTPS POST (outbound)                                          ▼
        │  https://petir.<domain>/api/ingest/sync-batch            nginx (host)
        └───────────────────────────►  [ petir.<domain> ] ──tunnel──►  ├─ /api/*  → server:8000  (FastAPI)
                                            domain publik                └─ /*      → web:3000     (Next.js)
                                                                        docker compose:
                                                                          postgres + server + web
```

Kedua mesin **hanya membuat koneksi keluar**. Cloudflare adalah titik temu publik.
**Tidak perlu** IP publik, port forwarding, atau VPN. Pi cukup tahu URL
`https://petir.<domain>`.

### Tiga syarat yang harus benar
1. Cloudflare Tunnel meng-expose path `/api/` ke nginx → `server:8000` (bukan hanya
   dashboard). Lihat [nginx-cloudflare.md](./nginx-cloudflare.md).
2. Pi punya akses internet keluar (HTTPS 443 ke Cloudflare). Biasanya sudah ada.
3. `SERVER_URL` di `edge/.env` = `https://petir.<domain>` (domain tunnel, bukan IP).

---

## Pembagian monorepo: mana ke Pi, mana ke server lab

Repo ini satu monorepo, tapi **tiap mesin hanya menjalankan sebagian**. Pemisah
adalah `packages/contracts` (satu-satunya kebenaran bersama; `edge/` dan `server/`
tidak pernah saling impor).

| Folder | Raspberry Pi 5 | Server Lab | Catatan |
| --- | :---: | :---: | --- |
| `packages/contracts/` | ✅ (Python) | ✅ (Python + TS) | Kontrak bersama. Pi pakai versi Python; server pakai Python; web pakai TS. |
| `edge/` | ✅ | ❌ | Sync worker + migrasi SQLite + unit systemd. **Hanya Pi.** |
| `scripts/bootstrap-edge.sh` | ✅ | ❌ | Bootstrap venv + migrasi + dry-run di Pi. |
| `scripts/install-edge-systemd.sh` | ✅ | ❌ | Pasang timer systemd di Pi. |
| `server/` | ❌ | ✅ | FastAPI (ingest + query) + Alembic. **Hanya server.** |
| `web/` | ❌ | ✅ | Dashboard Next.js. **Hanya server.** |
| `docker-compose.yml` | ❌ | ✅ | postgres + server + web. **Hanya server.** |
| `docs/` | (referensi) | (referensi) | Dokumentasi, tidak di-runtime. |

## Satu repo, dua mesin — cara menarik kode

Gunakan **satu repo Git** untuk kedua mesin. JANGAN pecah jadi dua repo: itu
memaksa `packages/contracts` diduplikasi dan membuka risiko **drift kontrak**
(Pi pakai versi berbeda dari server) — persis bencana yang sistem ini didesain
untuk dicegah (lihat drift v1→v2 di [edge-schema-drift.md](./edge-schema-drift.md)).
Kontrak adalah satu-satunya kebenaran bersama (AGENTS.md #1); ia harus berasal
dari sumber yang sama untuk Pi dan server.

Tiap mesin meng-clone repo yang sama lalu hanya menjalankan bagiannya. `git clone`
tidak berarti "jalankan semua" — folder yang tidak dipakai cukup diam di disk.
Karena keduanya hanya butuh koneksi keluar (HTTPS ke GitHub), tidak ada masalah
dengan "no public IP".

### Opsi A — Full clone, jalankan sebagian (paling sederhana)
```bash
# Server lab:
git clone <repo-url> petir && cd petir
docker compose up -d            # hanya menjalankan server + web + postgres

# Raspberry Pi 5:
git clone <repo-url> petir && cd petir
bash scripts/bootstrap-edge.sh  # hanya meng-install edge/ + contracts
```
Pi tetap punya folder `web/`/`server/` di disk tapi tak tersentuh (tidak di-install,
tidak di-build, tidak di-run). Overhead hanya beberapa MB file sumber. `git pull`
memperbarui semuanya sekaligus dan menjaga kontrak tetap sinkron. **Mulai dari sini.**

### Opsi B — Sparse checkout (Pi benar-benar minimal)
Tetap satu repo, tapi Pi hanya meng-checkout folder edge ke disk:
```bash
# Raspberry Pi 5:
git clone --no-checkout <repo-url> petir && cd petir
git sparse-checkout init --cone
git sparse-checkout set edge packages/contracts scripts
git checkout
bash scripts/bootstrap-edge.sh
```
Atau otomatis lewat flag bootstrap (mengonfigurasi sparse-checkout untukmu, idempotent):
```bash
git clone <repo-url> petir && cd petir
bash scripts/bootstrap-edge.sh --sparse     # atau: PETIR_SPARSE=1 bash scripts/bootstrap-edge.sh
```
`web/` dan `server/` tidak ikut ke disk Pi, tetapi `git pull` tetap jalan dan
kontrak tetap satu sumber. Aman: jika bukan git work tree, flag `--sparse`
menjadi no-op.

### Opsi C — Artifact CI (paling matang, nanti)
Pi tidak meng-clone repo. GitHub Actions mem-build paket edge (wheel/tarball atau
image) dan Pi menariknya. Lebih kompleks; pertimbangkan setelah alur dasar stabil.

**Rekomendasi:** Opsi A untuk mulai, naik ke Opsi B kalau ingin Pi seminimal mungkin.

### Yang dikirim ke Raspberry Pi 5
Hanya bagian edge — Pi tetap ringan (AGENTS.md #9: **tanpa Node/web toolchain**).

```
edge/
packages/contracts/        # dependency edge (versi Python)
scripts/bootstrap-edge.sh
scripts/install-edge-systemd.sh
```

Dependency runtime Pi cuma: `httpx` + `petir-contracts` (lihat `edge/pyproject.toml`).
Worker hidup sebagai **single-run** yang dipanggil **systemd timer** — bukan daemon
(AGENTS.md #5). Targetnya DB live `/home/pi/weather-edge/data/db/weather_edge.db`,
dan rollout-nya **additive** (tidak menyentuh service ingest yang sudah jalan).

### Yang dijalankan di server lab
Seluruh stack pusat via Docker Compose:

```
server/            # FastAPI image (alembic upgrade head + uvicorn)
web/               # Next.js image (standalone)
packages/contracts/# di-COPY ke dalam image saat build
docker-compose.yml # postgres + server + web
```

Di depan compose: **nginx (host)** + **cloudflared (host)** — keduanya di luar
compose, mengikuti [nginx-cloudflare.md](./nginx-cloudflare.md).

---

## Alur integrasi end-to-end

1. Arduino → service ingest yang sudah ada di Pi menulis ke `weather_edge.db`
   (tidak diubah oleh kita).
2. `petir-sync.timer` memicu `python -m sync_worker.run` (single-run) tiap ~15 dtk.
3. Worker membaca baris baru (cursor: `edge_id` untuk event, `change_seq` untuk
   summary), menormalkan kosakata sensor (`healthy→ok`, dst — lihat
   [edge-schema-drift.md](./edge-schema-drift.md)), lalu `POST` batch ke
   `https://petir.<domain>/api/ingest/sync-batch` dengan header `Authorization:
   Bearer <NODE_TOKEN>`.
4. Cloudflare → tunnel → nginx → `server:8000`. Server memvalidasi tiap baris
   terhadap kontrak, upsert idempotent ke Postgres, balas `accepted_cursor`.
5. Worker menyimpan `accepted_cursor` verbatim; cursor maju hanya setelah ACK 2xx.
6. Dashboard (`web`) membaca Postgres lewat `/api/...` (same-origin via nginx) dan
   menampilkan data.

---

## Urutan deploy yang aman (anti data-loss)

Detail lengkap di [edge-schema-drift.md](./edge-schema-drift.md). Ringkas:

1. **Server lab dulu**: `cp .env.example .env` (isi secret kuat), `docker compose up -d`.
2. **nginx + cloudflared**: arahkan `/api/`→8000, `/`→3000; tunnel ke nginx.
3. **Daftarkan node** di tabel `edge_nodes` → dapat `NODE_TOKEN`.
4. **Pi**: kirim `edge/` + `packages/contracts/` + `scripts/`, jalankan
   `bootstrap-edge.sh` (backup DB dulu → migrasi additive → dry-run).
5. `install-edge-systemd.sh` → enable `petir-sync.timer`.
6. Pantau siklus pertama: cursor mulai dari 0, seluruh histori masuk bersih.

## Mengapa tidak ada VPN / port forwarding
- PUSH-only → server tak perlu menjangkau Pi.
- Cloudflare Tunnel → server publik tanpa IP publik (outbound saja).
- Pi → client outbound biasa.

Tiga fakta itu menghapus kebutuhan akan IP publik di kedua mesin.
