#!/usr/bin/env bash
# Install + enable the PetirDashboard edge sync systemd timer on a Raspberry Pi.
# SAFETY: enables ONLY petir-sync.timer. It never stops, restarts, disables, or
# modifies the existing weather-ingest / lightning-ingest services.
set -euo pipefail

PREFIX="${PETIR_EDGE_PREFIX:-/opt/petir/edge}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="${REPO_ROOT}/edge/systemd"
SYSTEMD_DIR="/etc/systemd/system"

log() { printf '[install-edge-systemd] %s\n' "$*"; }
die() { printf '[install-edge-systemd] ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "must run as root (use sudo)"
[ -f "${UNIT_SRC}/petir-sync.service" ] || die "missing ${UNIT_SRC}/petir-sync.service"
[ -f "${UNIT_SRC}/petir-sync.timer" ] || die "missing ${UNIT_SRC}/petir-sync.timer"
[ -x "${PREFIX}/.venv/bin/python" ] || die "venv not found at ${PREFIX}/.venv; run bootstrap-edge.sh first"

install -m 0644 "${UNIT_SRC}/petir-sync.service" "${SYSTEMD_DIR}/petir-sync.service"
install -m 0644 "${UNIT_SRC}/petir-sync.timer" "${SYSTEMD_DIR}/petir-sync.timer"
log "installed petir-sync.service and petir-sync.timer"

systemctl daemon-reload

# Enable + start ONLY the timer. Do not touch any other unit.
systemctl enable --now petir-sync.timer
log "petir-sync.timer enabled and started"

log "current timer status:"
systemctl status petir-sync.timer --no-pager --lines=0 || true

log "done. The existing ingest services were not modified."
log "Verify a run with: systemctl start petir-sync.service && journalctl -u petir-sync.service -n 50 --no-pager"
