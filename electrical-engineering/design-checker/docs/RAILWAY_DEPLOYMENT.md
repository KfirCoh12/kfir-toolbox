# Railway deployment path

This is the preferred zero-cost test path for the private browser-hosted Toolbox.

Railway's current Free plan provides up to 0.5 GB persistent volume storage, which is far more than the Board Planner JSON autosaves require. The service still needs to fit inside Railway's monthly free resource allowance; that must be confirmed by real usage rather than assumed.

## Service source

Connect the GitHub repository and set the service Root Directory to:

`/electrical-engineering/design-checker`

Set the Railway config file path to:

`/electrical-engineering/design-checker/railway.json`

The Dockerfile in that directory remains the deployment image source.

## Required service variables

Set these in Railway's service variables. Do not commit real values to Git.

- `KFIR_TOOLBOX_REQUIRE_AUTH=1`
- `KFIR_TOOLBOX_DATA_DIR=/data`
- `KFIR_TOOLBOX_ALLOWED_EMAILS=<comma-separated authorized Google accounts>`
- `RAILWAY_RUN_UID=0`

`RAILWAY_RUN_UID=0` is required for the current Railway volume model because Railway mounts persistent volumes as root-owned paths. The Docker image normally runs the Toolbox as a non-root user, but a mounted `/data` volume would otherwise not be writable. This is a Railway-specific deployment compromise, not a change to the local app.

## Persistent volume

Create one volume and attach it to the Toolbox service at:

`/data`

On the current Free plan the volume limit is 0.5 GB and one volume per project. Do not deploy the persistent version without the volume attached.

## Public HTTPS domain

Generate a Railway public domain for the service. Railway supplies the `PORT` environment variable automatically, and the Docker command already listens on that port.

Once the HTTPS domain exists, its Google callback URL is:

`https://<railway-domain>/oauth2callback`

Use that exact callback URL in both Google OAuth and the Streamlit auth secrets.

## Streamlit OIDC secret file

The hosted app needs `.streamlit/secrets.toml` with real Google values. Use `.streamlit/secrets.toml.example` only as the template.

The real file must contain the Railway HTTPS callback URL, a random cookie secret, the Google OAuth Client ID, the Google OAuth Client secret, and Google's OIDC discovery URL.

Keep the real secret file outside Git. If Railway's UI cannot mount the file directly, inject the file at runtime or use the platform's supported secret-file mechanism rather than committing it.

## First acceptance test

Before calling the deployment private, verify:

1. Anonymous access is stopped at Google login.
2. The allowlisted Google account can enter.
3. A non-allowlisted authenticated account is denied.
4. Board Planner autosave survives a service restart/redeploy.
5. Persistent data is stored under `/data` and is not present in Git.
6. Railway usage remains inside the Free plan allowance for the intended personal usage pattern.

If normal personal usage exhausts Railway's monthly free allowance, stop and reassess rather than silently converting the project to a paid service.
