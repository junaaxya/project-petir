# Prompt Deploy — Agent Raspberry Pi 5 (Edge)

Prompt siap-pakai untuk Hermes/agent AI yang menjalankan deploy komponen **edge**
PetirDashboard di Raspberry Pi 5. Salin blok di bawah ke agent tersebut.

> Urutan koordinasi: jalankan agent **server lab dulu** sampai menghasilkan
> `NODE_TOKEN` (lihat [agent-deploy-server.md](./agent-deploy-server.md) langkah 8),
> baru serahkan token itu ke agent Pi ini.

---

```
PERAN: Kamu men-deploy komponen EDGE dari project PetirDashboard di Raspberry Pi 5 ini.

KONTEKS SISTEM:
- Pi ini SUDAH menjalankan sistem ingest cuaca/petir LIVE: service `weather-ingest` dan
  `lightning-ingest` menulis ke SQLite di /home/pi/weather-edge/data/db/weather_edge.db.
- Tugasmu HANYA menambahkan sync worker baru yang mem-PUSH data ke server lab. Ini ADITIF.
- Repo: https://github.com/junaaxya/project-petir.git

⛔ ATURAN KESELAMATAN (PALING PENTING — JANGAN DILANGGAR):
1. JANGAN PERNAH stop/restart/disable/ubah service `weather-ingest` atau `lightning-ingest`.
   Verifikasi mereka tetap `active` sebelum DAN sesudah pekerjaanmu.
2. JANGAN menulis langsung ke DB live. Migrasi WAJIB backup-first (script sudah menangani ini).
3. Sebelum migrasi DB, uji dulu di SALINAN: `sqlite3 <db> ".backup '/tmp/weather_copy.db'"`,
   jalankan `python -m migrations.inspect /tmp/weather_copy.db` lalu `python -m migrations.apply /tmp/weather_copy.db`,
   pastikan idempotent (jalankan 2x = no-op kedua). Baru lakukan ke DB live.
4. JANGAN install toolchain Node/web/Docker di Pi. Edge harus ringan: hanya Python + httpx + petir-contracts.
5. Worker adalah SINGLE-RUN yang dipanggil systemd timer — BUKAN daemon. Jangan ubah jadi long-running.

LANGKAH:
1. `git clone https://github.com/junaaxya/project-petir.git ~/project-petir && cd ~/project-petir`
   (opsional minimal: `bash scripts/bootstrap-edge.sh --sparse` agar hanya folder edge ter-checkout)
2. Pastikan Python 3.11+ tersedia.
3. Konfigurasi: `cp edge/.env.example edge/.env` lalu isi:
   - SERVER_URL=https://petir.lab-ilkom.my.id   (TANYA operator domain-nya; ini URL publik, bukan IP)
   - NODE_ID=rpi-lab-01                                      (atau id yang diberikan operator)
   - NODE_TOKEN=<token dari server>                          (operator menjalankan register_node.py di server, lalu memberi token ini SEKALI)
   - EDGE_DB_PATH=/home/pi/weather-edge/data/db/weather_edge.db
4. REKONSILIASI PATH SYSTEMD (PENTING — ada gap yang harus kamu tangani):
   Unit `edge/systemd/petir-sync.service` meng-hardcode:
     WorkingDirectory=/opt/petir/edge, EnvironmentFile=/opt/petir/edge/.env, User=petir,
     ExecStart=/opt/petir/edge/.venv/bin/python -m sync_worker.run
   Sementara bootstrap menaruh venv di /opt/petir/edge/.venv tapi kode+`.env` ada di clone repo.
   Maka SEBELUM enable timer, pastikan KONSISTEN:
     a. Pastikan user `petir` ADA (atau ubah `User=` di unit ke user yang menjalankan, mis. `pi`).
        Jika ubah, lakukan di file unit SEBELUM install, dan catat perubahannya.
     b. Pastikan /opt/petir/edge/.env ADA dan berisi konfigurasi dari langkah 3
        (cara aman: symlink `sudo ln -s ~/project-petir/edge/.env /opt/petir/edge/.env`,
        ATAU copy). EnvironmentFile harus bisa dibaca oleh User di unit.
     c. Pastikan EDGE_DB_PATH bisa dibaca user tersebut.
5. `bash scripts/bootstrap-edge.sh`
   (membuat venv di /opt/petir/edge/.venv, install petir-contracts+edge, validasi .env,
    migrasi DB live BACKUP-FIRST + idempotent, lalu 1x dry-run sync.
    Dry-run exit: 0=ok, 1=partial, 2=failed — laporkan kodenya.)
6. `sudo bash scripts/install-edge-systemd.sh`
   (install + enable HANYA petir-sync.timer; tidak menyentuh service ingest.)

VERIFIKASI (wajib lapor hasilnya):
- `systemctl is-active weather-ingest lightning-ingest`  → harus tetap `active` (TIDAK terganggu)
- `sudo systemctl start petir-sync.service && journalctl -u petir-sync.service -n 50 --no-pager`
- `systemctl list-timers petir-sync.timer --no-pager`    → timer terjadwal
- Konfirmasi data sampai ke server: minta operator cek GET https://petir.lab-ilkom.my.id/api/ingest/runs
  (harus ada run terbaru, rows_accepted > 0, rejected = 0).
- Konfirmasi file backup DB dibuat (weather_edge.db.backup-<timestamp>).

ROLLBACK (jika perlu):
- `sudo systemctl disable --now petir-sync.timer`
- Migrasi bisa di-rollback (drop trigger / sync_state / meta / change_seq_counter) tanpa
  menyentuh baris data. Service ingest tidak pernah disentuh, jadi tidak ada yang perlu dipulihkan di sana.

LAPORKAN: ringkasan langkah yang dilakukan, status verifikasi di atas, perubahan apa pun yang
kamu buat pada file unit (mis. User=), dan masalah yang ditemui. Jangan klaim sukses tanpa bukti journalctl + /api/ingest/runs.
```

---

Referensi pendukung di repo: [edge-deploy.md](./edge-deploy.md),
[edge-migration.md](./edge-migration.md), [deployment-topology.md](./deployment-topology.md).
