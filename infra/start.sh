#!/bin/sh
# Production entrypoint. Secrets come from Render's secret file (never baked into the image).
set -e
if [ -f /etc/secrets/kavach.env ]; then cp /etc/secrets/kavach.env /srv/.env; fi
# honcho sets $PORT per process, so hand Render's port to the api under its own name
export KAVACH_PORT="${PORT:-8000}"
exec honcho start -f infra/Procfile.prod --no-colour
