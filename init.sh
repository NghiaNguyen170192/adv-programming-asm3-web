#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# init.sh — bootstrap the adv-programming-asm3-web stack
#
# Usage:
#   ./init.sh            # auto-detects mode from DOMAIN in .env
#   ./init.sh local      # force local dev (self-signed cert)
#   ./init.sh production # force production (Cloudflare DNS challenge)
# ---------------------------------------------------------------------------

# ── helpers ────────────────────────────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# ── load .env ──────────────────────────────────────────────────────────────
[[ -f .env ]] || error ".env not found. Copy .env.example and fill it in."
# shellcheck disable=SC2046
export $(grep -v '^\s*#' .env | grep -v '^\s*$' | xargs)

DOMAIN="${DOMAIN:-localhost}"
NGINX_SSL_DIR="./nginx/ssl"
CERT_DIR="$NGINX_SSL_DIR/live/$DOMAIN"
CERTBOT_INI="./certbot/cloudflare.ini"

# ── detect mode ────────────────────────────────────────────────────────────
if [[ "${1:-}" == "local" ]]; then
    MODE="local"
elif [[ "${1:-}" == "production" ]]; then
    MODE="production"
elif [[ "$DOMAIN" == "localhost" || "$DOMAIN" == *.local ]]; then
    MODE="local"
else
    MODE="production"
fi

info "Domain  : $DOMAIN"
info "Mode    : $MODE"

# ── pre-flight checks ──────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || error "docker is not installed."

if [[ "$MODE" == "production" ]]; then
    [[ -f "$CERTBOT_INI" ]] || error "certbot/cloudflare.ini not found."
    grep -q "YOUR_CLOUDFLARE_API_TOKEN" "$CERTBOT_INI" \
        && error "Fill in your Cloudflare API token in $CERTBOT_INI first."
    [[ -n "${CERTBOT_EMAIL:-}" ]] \
        || error "CERTBOT_EMAIL is not set in .env."
fi

# ── ensure external network exists ────────────────────────────────────────
if ! docker network ls --format '{{.Name}}' | grep -q '^nginx-network$'; then
    info "Creating external Docker network 'nginx-network'..."
    docker network create nginx-network
else
    info "Docker network 'nginx-network' already exists."
fi

# ── build images ───────────────────────────────────────────────────────────
info "Building Docker images..."
docker compose -f compose.yml build

# ── certificates ───────────────────────────────────────────────────────────
mkdir -p "$CERT_DIR"

if [[ "$MODE" == "local" ]]; then
    # Self-signed cert for local development
    KEY_FILE="$CERT_DIR/privkey.pem"
    CERT_FILE="$CERT_DIR/fullchain.pem"

    if [[ -f "$CERT_FILE" ]]; then
        info "Self-signed cert already exists, skipping generation."
    else
        info "Generating self-signed certificate for: $DOMAIN and subdomains..."
        SUBDOMAINS="DNS:$DOMAIN,DNS:dashboard.$DOMAIN,DNS:api.$DOMAIN,DNS:adminer.$DOMAIN"
        openssl req -x509 -nodes -days 365 \
            -newkey rsa:2048 \
            -keyout "$KEY_FILE" \
            -out "$CERT_FILE" \
            -subj "/CN=$DOMAIN" \
            -addext "subjectAltName=$SUBDOMAINS" \
            || error "Failed to generate self-signed certificate."
        info "Self-signed certificate created at $CERT_FILE"
    fi

else
    # Production: issue real cert via Cloudflare DNS challenge
    if [[ -f "$CERT_DIR/fullchain.pem" ]]; then
        info "Certificate already exists at $CERT_DIR, skipping certbot."
    else
        info "Issuing Let's Encrypt certificate via Cloudflare DNS challenge..."
        docker compose -f compose.yml run --rm certbot
        info "Certificate issued successfully."
    fi
fi

# ── start the stack ────────────────────────────────────────────────────────
info "Starting all services..."
docker compose -f compose.yml up -d

info "Done! Services are up."
echo ""
echo "  Frontend : https://dashboard.$DOMAIN"
echo "  API      : https://api.$DOMAIN"
echo "  Adminer  : https://adminer.$DOMAIN"
if [[ "$MODE" == "local" ]]; then
    echo ""
    echo "  Note: self-signed cert — you will see a browser security warning."
    echo "  Add $CERT_DIR/fullchain.pem to your OS/browser trust store to suppress it."
fi
