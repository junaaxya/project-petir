#!/usr/bin/env bash
# Install + enable the PetirDashboard edge sync systemd timer.
# The service unit is GENERATED from this machine's actual layout (user, repo
# path, venv) — no /opt or special-user assumptions. Override via env vars below.
#
# SAFETY: enables ONLY petir-sync.timer. It never stops, restarts, disables, or
# modifies the existing weather-ingest / lightning-ingest services.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EDGE_DIR="${REPO_ROOT}/edge"
UNIT_SRC="${EDGE_DIR}/systemd"
SYSTEMD_DIR="/etc/systemd/system"

# venv location must match bootstrap-edge.sh (defaults to <repo>/edge/.venv).
PREFIX="${PETIR_EDGE_PREFIX:-${EDGE_DIR}}"
VENV_PY="${PREFIX}/.venv/bin/python"
ENV_FILE="${EDGE_DIR}/.env"

# Service user/group: default to the invoking (non-root) user so the unit runs
# as the same account that owns the repo and the live DB (e.g. pi), not root.
SERVICE_USER="${PETIR_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVICE_GROUP="${PETIR_SERVICE_GROUP:-$(id -gn "${SERVICE_USER}")}"

log() { printf '[install-edge-systemd] %s\n' "$*"; }
die() { printf '[install-edge-systemd] ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "must run as root (use sudo)"
[ -f "${UNIT_SRC}/petir-sync.service.tmpl" ] || die "missing ${UNIT_SRC}/petir-sync.service.tmpl"
[ -f "${UNIT_SRC}/petir-sync.timer" ] || die "missing ${UNIT_SRC}/petir-sync.timer"
[ -x "${VENV_PY}" ] || die "venv python not found at ${VENV_PY}; run bootstrap-edge.sh first"
[ -f "${ENV_FILE}" ] || die "env file not found at ${ENV_FILE}; copy edge/.env.example to edge/.env"
id "${SERVICE_USER}" >/dev/null 2>&1 || die "service user does not exist: ${SERVICE_USER}"

log "generating unit with: User=${SERVICE_USER} Group=${SERVICE_GROUP} WorkingDirectory=${EDGE_DIR}"

# Render the template into the systemd dir, substituting this machine's values.
sed \
  -e "s#__SERVICE_USER__#${SERVICE_USER}#g" \
  -e "s#__SERVICE_GROUP__#${SERVICE_GROUP}#g" \
  -e "s#__EDGE_DIR__#${EDGE_DIR}#g" \
  -e "s#__VENV_PYTHON__#${VENV_PY}#g" \
  -e "s#__ENV_FILE__#${ENV_FILE}#g" \
  "${UNIT_SRC}/petir-sync.service.tmpl" > "${SYSTEMD_DIR}/petir-sync.service"
chmod 0644 "${SYSTEMD_DIR}/petir-sync.service"

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
