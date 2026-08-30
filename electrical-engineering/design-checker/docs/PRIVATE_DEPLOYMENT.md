# Private deployment with Google login

This document is the deployment checklist for the browser-hosted private Toolbox.
The repository contains placeholders only. Real OAuth credentials and cookie secrets must remain outside Git.

## 1. Choose the final HTTPS hostname

Decide the public browser URL before creating the Google client, for example:

`https://toolbox.example.com`

The corresponding OAuth redirect URI is always the same host plus:

`/oauth2callback`

Example:

`https://toolbox.example.com/oauth2callback`

The redirect URI configured in Google and in Streamlit must match exactly, including scheme, host, path, case, and trailing slash behavior.

## 2. Create the Google web client

In Google Auth Platform / Google Cloud:

1. Create or select the project used for the Toolbox.
2. Configure the app/consent information required by Google.
3. Create an OAuth client with application type **Web application**.
4. Add the exact hosted redirect URI from step 1 under **Authorized redirect URIs**.
5. Save the generated Client ID and Client secret in a password manager or the hosting platform's secret store.

The Toolbox does not need Google API access. Google is used only as the OpenID Connect identity provider.

## 3. Configure Streamlit OIDC secrets

Use `.streamlit/secrets.toml.example` as the shape of the configuration.
Do not replace the example file with real values in Git.

The private host must provide:

- `auth.redirect_uri` — the exact HTTPS callback URL.
- `auth.cookie_secret` — a strong random secret used to sign identity cookies.
- `auth.client_id` — the Google Web application Client ID.
- `auth.client_secret` — the Google Web application Client secret.
- `auth.server_metadata_url` — `https://accounts.google.com/.well-known/openid-configuration`.

No OIDC tokens are exposed by the application configuration.

## 4. Configure Toolbox access controls

The container already defaults to authentication-required mode. The host must additionally provide:

`KFIR_TOOLBOX_ALLOWED_EMAILS`

as a comma-separated list of explicitly authorized Google account email addresses.

Example shape only:

`owner@example.com,second-user@example.com`

Do not commit a real allowlist if the addresses should remain private; set it in the hosting environment.

The private entrypoint fails closed when authentication is disabled or the allowlist is empty.

## 5. Configure persistent storage

Mount a persistent private volume at `/data`.

The container sets:

`KFIR_TOOLBOX_DATA_DIR=/data`

Authenticated users are assigned separate opaque hashed storage scopes, so one authorized user's Board Planner autosave does not share a file with another user's autosave. Actual email addresses are not used as directory names.

The volume must survive container restarts and redeployments.

## 6. Deploy the container

Build from `electrical-engineering/design-checker/Dockerfile`.

The image runs:

`private_app.py`

rather than the local `app.py` entrypoint. It runs as a non-root user, exposes Streamlit on the platform-provided `PORT` (default 8501), and includes a Streamlit health check.

The hosting platform or reverse proxy must provide HTTPS. Do not expose a production login flow over plain HTTP.

## 7. Acceptance test before treating the deployment as private

Verify all of the following on the real hosted URL:

1. An anonymous browser is stopped at Google login.
2. An authorized Google account can sign in and reach the Toolbox.
3. An authenticated but non-allowlisted Google account is denied.
4. Logout removes access and a fresh private/incognito window requires login again.
5. Board Planner data survives a container restart/redeploy.
6. Two authorized test accounts receive separate Board Planner autosaves.
7. No `.streamlit/secrets.toml`, OAuth client secret, cookie secret, or private board data exists in Git or the built image layers.

The deployment should not be described as private until these checks pass on the chosen host.
