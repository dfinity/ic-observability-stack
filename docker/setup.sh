# /usr/bin/env bash
set -euo pipefail

# Resolve the directory of the script (so it works regardless of where it's run from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# If .env already exists, do nothing
if [[ -f "$ENV_FILE" ]]; then
  echo ".env already exists at $ENV_FILE"
  exit 0
fi

# Get current user's UID and GID
UID_VAL=$(id -u)
GID_VAL=$(id -g)

# Write them to .env
cat > "$ENV_FILE" <<EOF
UID=${UID_VAL}
GID=${GID_VAL}
EOF

echo "Created $ENV_FILE with UID=${UID_VAL} and GID=${GID_VAL}"

