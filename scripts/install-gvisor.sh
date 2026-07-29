#!/usr/bin/env bash
# Install gVisor (runsc) and register it with the Docker daemon so SandBench can
# execute submissions behind a userspace kernel instead of the host kernel.
#
#   sudo bash scripts/install-gvisor.sh
#
# Linux + x86_64/arm64 only. On macOS and Windows, Docker Desktop already runs
# containers inside a Linux VM, so an escape lands in a disposable VM rather
# than on your machine; gVisor is not installable there and not needed for local
# development. Install this on any host that runs the worker for real.
set -euo pipefail

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Linux" ]] || die "gVisor requires Linux. See docs/isolation.md for macOS/Windows."
[[ $EUID -eq 0 ]] || die "Run as root: sudo bash scripts/install-gvisor.sh"

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ARCH=x86_64 ;;
  aarch64|arm64) ARCH=aarch64 ;;
  *) die "Unsupported architecture: $ARCH" ;;
esac

command -v docker >/dev/null 2>&1 || die "Docker not found. Install Docker first."

if command -v runsc >/dev/null 2>&1; then
  log "runsc already installed: $(runsc --version | head -1)"
else
  log "Installing gVisor for $ARCH..."
  URL="https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  cd "$TMP"

  for f in runsc containerd-shim-runsc-v1; do
    log "Downloading $f"
    curl -fsSL -O "${URL}/${f}"
    curl -fsSL -O "${URL}/${f}.sha512"
  done
  log "Verifying checksums"
  sha512sum -c runsc.sha512 containerd-shim-runsc-v1.sha512 \
    || die "Checksum verification failed — do not install."

  install -o root -g root -m 0755 runsc containerd-shim-runsc-v1 /usr/local/bin/
  log "Installed to /usr/local/bin"
fi

# Register runsc with the Docker daemon. `runsc install` edits
# /etc/docker/daemon.json and adds the runtime entry.
log "Registering runsc with the Docker daemon"
if [[ -f /etc/docker/daemon.json ]]; then
  cp /etc/docker/daemon.json "/etc/docker/daemon.json.bak.$(date +%s)"
  log "Backed up existing /etc/docker/daemon.json"
fi
runsc install

log "Restarting Docker"
systemctl restart docker || service docker restart

log "Verifying"
if docker run --rm --runtime=runsc alpine:latest dmesg 2>/dev/null | grep -qi gvisor; then
  log "gVisor is live — 'dmesg' inside the container reports the Sentry kernel."
else
  warn "Could not confirm via dmesg. Check manually:"
  warn "  docker run --rm --runtime=runsc alpine dmesg | head"
fi

cat <<'EOF'

Next steps
----------
  1. Confirm SandBench sees it:
       python cli/main.py doctor

  2. Make hardened isolation mandatory on this host (engine/.env):
       SANDBOX_RUNTIME=auto
       SANDBOX_REQUIRE_HARDENED=1

     With SANDBOX_REQUIRE_HARDENED=1 a run is refused rather than executed on
     the shared-kernel runtime. Set this on any worker that evaluates code you
     did not write.

  3. Restart the worker:
       python worker.py

Note: safety-suite audit runs stay on runc on purpose — under gVisor the Sentry
services syscalls itself, so host seccomp audit records (the evidence those
tasks cite) are never produced. See docs/isolation.md.
EOF
