#!/bin/sh
set -eu

if [ "${KFIR_TOOLBOX_REQUIRE_AUTH:-0}" = "1" ]; then
    : "${KFIR_TOOLBOX_GOOGLE_CLIENT_ID:?KFIR_TOOLBOX_GOOGLE_CLIENT_ID is required}"
    : "${KFIR_TOOLBOX_GOOGLE_CLIENT_SECRET:?KFIR_TOOLBOX_GOOGLE_CLIENT_SECRET is required}"

    if [ -n "${KFIR_TOOLBOX_OIDC_REDIRECT_URI:-}" ]; then
        redirect_uri="$KFIR_TOOLBOX_OIDC_REDIRECT_URI"
    elif [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
        redirect_uri="https://${RAILWAY_PUBLIC_DOMAIN}/oauth2callback"
    else
        echo "KFIR_TOOLBOX_OIDC_REDIRECT_URI or RAILWAY_PUBLIC_DOMAIN is required for private hosting" >&2
        exit 1
    fi

    mkdir -p /app/.streamlit /data
    python - "$redirect_uri" <<'PY'
import json
import os
import pathlib
import secrets
import sys

redirect_uri = sys.argv[1]
secret_file = pathlib.Path("/data/.kfir-toolbox-cookie-secret")
cookie_secret = os.environ.get("KFIR_TOOLBOX_COOKIE_SECRET", "").strip()
if not cookie_secret:
    if secret_file.exists():
        cookie_secret = secret_file.read_text(encoding="utf-8").strip()
    else:
        cookie_secret = secrets.token_urlsafe(48)
        secret_file.write_text(cookie_secret, encoding="utf-8")
        try:
            secret_file.chmod(0o600)
        except OSError:
            pass

config = "\n".join(
    [
        "[auth]",
        f"redirect_uri = {json.dumps(redirect_uri)}",
        f"cookie_secret = {json.dumps(cookie_secret)}",
        f"client_id = {json.dumps(os.environ['KFIR_TOOLBOX_GOOGLE_CLIENT_ID'])}",
        f"client_secret = {json.dumps(os.environ['KFIR_TOOLBOX_GOOGLE_CLIENT_SECRET'])}",
        'server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"',
        "",
    ]
)
path = pathlib.Path("/app/.streamlit/secrets.toml")
path.write_text(config, encoding="utf-8")
try:
    path.chmod(0o600)
except OSError:
    pass
PY
fi

exec streamlit run private_app.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-8501}" \
    --server.headless=true
