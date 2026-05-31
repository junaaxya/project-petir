#!/usr/bin/env bash
# Bootstrap the PetirDashboard edge sync worker on a Raspberry Pi.
# Additive and idempotent: it does NOT touch the running weather-ingest /
# lightning-ingest services. Safe to re-run.
#
# Optional: pass --sparse (or set PETIR_SPARSE=1) to trim this git checkout to
# only the edge-relevant folders (edge/, packages/contracts/, scripts/). The
# repo stays ONE repo so the wire contract never drifts between Pi and server.
set -euo pipefail

PREFIX="${PETIR_EDGE_PREFIX:-/opt/petir/edge}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EDGE_DIR="${REPO_ROOT}/edge"
CONTRACTS_DIR="${REPO_ROOT}/packages/contracts"
ENV_FILE="${EDGE_DIR}/.env"

SPARSE="${PETIR_SPARSE:-0}"
for arg in "$@"; do
  [ "${arg}" = "--sparse" ] && SPARSE=1
done

log() { printf '[bootstrap-edge] %s\n' "$*"; }
die() { printf '[bootstrap-edge] ERROR: %s\n' "$*" >&2; exit 1; }

# 0. Optional sparse-checkout: keep only the folders the Pi runs.
# Safe no-op unless this is a git work tree and git is available.
if [ "${SPARSE}" = "1" ]; then
  if command -v git >/dev/null 2>&1 && git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "configuring sparse-checkout (edge, packages/contracts, scripts)"
    git -C "${REPO_ROOT}" sparse-checkout init --cone
    git -C "${REPO_ROOT}" sparse-checkout set edge packages/contracts scripts
  else
    log "sparse requested but ${REPO_ROOT} is not a git work tree; skipping (full tree is fine)"
  fi
fi

[ -d "${EDGE_DIR}" ] || die "edge dir not found: ${EDGE_DIR}"
[ -d "${CONTRACTS_DIR}" ] || die "contracts dir not found: ${CONTRACTS_DIR}"

# 1. Python venv under the deploy prefix (prefer uv, fall back to venv+pip).
if command -v uv >/dev/null 2>&1; then
  log "creating venv with uv at ${PREFIX}/.venv"
  mkdir -p "${PREFIX}"
  uv venv "${PREFIX}/.venv"
  # shellcheck disable=SC1091
  source "${PREFIX}/.venv/bin/activate"
  uv pip install -e "${CONTRACTS_DIR}" -e "${EDGE_DIR}"
else
  log "uv not found; using python venv + pip at ${PREFIX}/.venv"
  mkdir -p "${PREFIX}"
  python3 -m venv "${PREFIX}/.venv"
  # shellcheck disable=SC1091
  source "${PREFIX}/.venv/bin/activate"
  pip install --upgrade pip >/dev/null
  pip install -e "${CONTRACTS_DIR}" -e "${EDGE_DIR}"
fi

# 2. Validate .env (must exist and define the required keys).
if [ ! -f "${ENV_FILE}" ]; then
  die ".env not found at ${ENV_FILE}. Copy edge/.env.example to edge/.env and fill it in."
fi
required=(SERVER_URL NODE_ID NODE_TOKEN EDGE_DB_PATH)
missing=()
for key in "${required[@]}"; do
  grep -Eq "^${key}=.+" "${ENV_FILE}" || missing+=("${key}")
done
[ ${#missing[@]} -eq 0 ] || die "missing/empty .env keys: ${missing[*]}"

# shellcheck disable=SC1090
set -a; source "${ENV_FILE}"; set +a

[ -f "${EDGE_DB_PATH}" ] || die "EDGE_DB_PATH does not exist: ${EDGE_DB_PATH}"

# 3. Run the additive DB migration (apply.py takes a timestamped backup first).
log "running edge DB migration (backup-first, idempotent)"
( cd "${EDGE_DIR}" && python -m migrations.apply "${EDGE_DB_PATH}" )

# 4. Dry-run a single sync cycle. Exit code is the signal (0 ok, 1 partial, 2 failed).
log "performing one dry-run sync cycle"
if ( cd "${EDGE_DIR}" && python -m sync_worker.run ); then
  log "dry-run sync completed (exit 0)"
else
  rc=$?
  log "dry-run sync exited with code ${rc} (non-fatal here; check server + logs)"
fi

log "bootstrap complete. Next: sudo scripts/install-edge-systemd.sh"
