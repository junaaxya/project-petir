# Petir 2 Phase 3 — Access, Routing, and Rollback Plan

Status saat dokumen dibuat: **NO-GO**. Hostname `nelayan-sungailiat.petirlabs.com` masih cocok dengan final Cloudflare Tunnel rule `http_status:404`.

Dokumen ini adalah rencana perubahan, bukan otorisasi eksekusi. Tidak ada DNS, Tunnel, Access, firewall, Nginx, atau deployment produksi yang diubah pada Phase 2.8.

## Prasyarat GO

1. PR Phase 2.8 direview dan merged ke SHA release yang immutable.
2. Image `server` dan `web` dibangun dari SHA yang sama dan memiliki OCI revision yang sesuai.
3. Backup PostgreSQL terverifikasi dengan `sha256sum -c` dan `pg_restore -l`.
4. Candidate dideploy internal melalui targeted recreate hanya untuk `server`, `web`, dan bila dipakai `jwks-egress-proxy`; PostgreSQL tidak direcreate.
5. Internal smoke test pada `http://127.0.0.1:3020` lulus untuk loading, genuine empty, `401`, `403`, `503`, network failure, stale data, dan mobile safe-area.
6. Nilai aktual berikut tersedia melalui secret/runtime config, tidak ditulis ke repository:
   - Cloudflare Access team domain: `[REDACTED]`
   - Cloudflare Access audience: `[REDACTED]`
   - allowlist operator/admin: `[REDACTED]`
7. Tuan memberi otorisasi eksplisit terpisah untuk perubahan Cloudflare Access dan Tunnel.

## Target Access Policy

### Aplikasi manusia

- Hostname: `nelayan-sungailiat.petirlabs.com`
- Path: seluruh aplikasi kecuali exception mesin di bawah.
- Policy: hanya identitas manusia yang disetujui.
- Backend tetap memverifikasi JWT Cloudflare Access (`iss`, `aud`, `exp`, `iat`, `sub`, `email`, signature RS256) dan menerapkan role operator/admin.
- Tidak ada API key atau Access credential di frontend.

### Exception mesin yang sempit

- Exact path: `/api/ingest/sync-batch`
- Exact method yang diterima backend: `POST`
- Buat Access application/path policy terpisah hanya untuk exact path tersebut bila node tidak menggunakan Access service token.
- Jangan membuat bypass `/api/*`.
- Backend node authentication, token rotation, rate limiting, contract validation, dan node registry tetap wajib; request selain `POST` tetap ditolak oleh route backend.

Pilihan yang lebih kuat bila node mendukungnya: gunakan Access service token pada exact path dan jangan memakai bypass publik.

## Restricted JWKS Egress

1. Set hostname proxy allowlist ke exact Access team hostname `[REDACTED].cloudflareaccess.com`; wildcard dan arbitrary forwarding dilarang.
2. Backend memakai `CLOUDFLARE_JWKS_PROXY_URL=http://jwks-egress-proxy:3128` khusus untuk JWKS client, bukan global `HTTP_PROXY`/`HTTPS_PROXY`.
3. Backend hanya berada pada network `internal` dan `jwks_client` yang `internal: true`.
4. Proxy berada pada `jwks_client` dan network egress khusus; PostgreSQL hanya pada `internal`.
5. Tidak ada published port untuk backend, PostgreSQL, atau proxy.
6. TLS ke Cloudflare tetap diverifikasi. Kegagalan DNS/proxy/JWKS harus fail-closed sebagai `503 ACCESS_JWKS_UNAVAILABLE`; token/claim/signature invalid tetap `401`.

## Urutan Perubahan Routing

1. Catat dan simpan salinan konfigurasi efektif Tunnel saat itu.
2. Validasi konfigurasi sebelum edit:
   ```bash
   cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
   cloudflared tunnel --config /etc/cloudflared/config.yml ingress rule https://nelayan-sungailiat.petirlabs.com
   ```
3. Tambahkan rule hostname **sebelum** final catch-all `http_status:404`:
   ```yaml
   - hostname: nelayan-sungailiat.petirlabs.com
     service: http://127.0.0.1:3020
   ```
4. Validasi kembali; exact hostname harus cocok dengan rule baru, hostname acak harus tetap cocok dengan final `404`.
5. Terapkan Cloudflare Access applications/policies sebelum membuka routing atau dalam maintenance window atomik yang sama.
6. Reload/restart `cloudflared` hanya setelah diff ditampilkan dan Tuan memberi izin eksplisit.
7. Verifikasi eksternal:
   - browser anonim mengikuti policy Access;
   - operator valid dapat membuka protected diagnostics;
   - identitas tanpa role mendapat `403`;
   - JWT invalid/expired/wrong audience/wrong issuer mendapat `401`;
   - JWKS unavailable mendapat `503` tanpa fallback anonim;
   - exact machine sync tetap berfungsi dengan node authentication;
   - `/api/*` selain exact exception tidak ter-bypass;
   - docs/OpenAPI/Redoc tetap `404`;
   - hostname acak tetap `404`.

## Rollback

Trigger rollback: login loop, valid operator gagal, data publik salah, disclosure diagnostics, backend direct egress, sync node gagal, error rate persisten, atau regressi Petir 1/Rimbarest.

1. Kembalikan Tunnel hostname ke kondisi sebelumnya dengan menghapus hanya rule `nelayan-sungailiat.petirlabs.com`, sehingga kembali ke final `http_status:404`.
2. Validasi ingress dan konfirmasi hostname kembali cocok dengan final `404`.
3. Rollback targeted hanya `server`/`web` ke image immutable sebelumnya; jangan recreate PostgreSQL.
4. Bila diperlukan, nonaktifkan hanya Access applications/policies baru untuk hostname/path Petir 2; jangan mengubah policy aplikasi lain.
5. Verifikasi internal URL, database continuity, image revision, node sync, dan service lain.
6. Simpan log waktu kejadian, SHA release/candidate, hasil probe, dan keputusan rollback tanpa menyimpan secret.

## Keputusan

Phase 3/public routing tetap **NO-GO** sampai seluruh prasyarat di atas terpenuhi dan ada otorisasi Cloudflare eksplisit dari Tuan.
