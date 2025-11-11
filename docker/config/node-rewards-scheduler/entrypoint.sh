#!/bin/bash
set -e

echo "====================================="
echo "Node Rewards Scheduler for VictoriaMetrics"
echo "====================================="

# Install dependencies
echo "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq curl cron ca-certificates > /dev/null 2>&1

# Set up directories
mkdir -p /scheduler
cd /scheduler


# # Download dre binary if not already present
# if [ ! -f "/scheduler/.dre_installed" ]; then
#   echo "Downloading dre v${DRE_VERSION} binary..."
  
#   # Detect architecture
#   ARCH=$(uname -m)
#   if [ "$ARCH" = "x86_64" ]; then
#     DRE_BINARY="dre-x86_64-unknown-linux"
#   elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
#     # Note: v0.7.0 only has x86_64 Linux binary, no ARM64 Linux binary available
#     echo "⚠️  ARM64 Linux binary not available, using x86_64 (may require emulation)"
#     DRE_BINARY="dre-x86_64-unknown-linux"
#   else
#     echo "❌ Unsupported architecture: $ARCH"
#     exit 1
#   fi
  
#   # Download from GitHub releases
#   DRE_URL="https://github.com/dfinity/dre/releases/download/v${DRE_VERSION}/${DRE_BINARY}"
#   echo "Downloading from: $DRE_URL"
  
#   curl -L -o /usr/local/bin/dre "$DRE_URL"
#   chmod +x /usr/local/bin/dre
  
#   # Verify it works
#   if /usr/local/bin/dre --version; then
#     echo "✅ dre v${DRE_VERSION} installed successfully"
#     touch /scheduler/.dre_installed
#   else
#     echo "❌ Failed to install dre"
#     exit 1
#   fi
# else
#   echo "✅ dre already installed"
# fi

# Use locally built dre binary mounted from host
echo "Using locally built dre binary from /dre-binary/dre"

if [ -f "/dre-binary/dre" ]; then
  cp /dre-binary/dre /usr/local/bin/dre
  chmod +x /usr/local/bin/dre
  
  # Verify it works
  if /usr/local/bin/dre --version; then
    echo "✅ Local dre binary installed successfully"
  else
    echo "❌ Failed to run local dre binary"
    exit 1
  fi
else
  echo "❌ Local dre binary not found at /dre-binary/dre"
  echo "Please build the binary with: cd /Users/pietro.di.marco/dre && cargo build --release --bin dre"
  exit 1
fi

# Wait for VictoriaMetrics to be ready
echo "Waiting for VictoriaMetrics to be ready..."
until curl -s "${VICTORIA_METRICS_URL}/-/ready" > /dev/null 2>&1; do
  echo "  Waiting for VictoriaMetrics at ${VICTORIA_METRICS_URL}..."
  sleep 2
done
echo "✅ VictoriaMetrics is ready"

# Backfill last 40 days on initial startup
if [ ! -f /scheduler/.backfill_done ]; then
  echo ""
  echo "====================================="
  echo "Starting backfill of last 40 days..."
  echo "====================================="
  
  for i in $(seq 40 -1 1); do
    DATE=$(date -u -d "$i days ago" +%Y-%m-%d 2>/dev/null || date -u -v-${i}d +%Y-%m-%d)
    echo "[$(printf "%2d" $((41 - i)))/40] Backfilling data for $DATE..."
    
    if /usr/local/bin/dre node-rewards push-to-victoria --date "$DATE" --victoria-url "${VICTORIA_METRICS_URL}"; then
      echo "  ✅ Successfully pushed data for $DATE"
    else
      echo "  ⚠️  No data available or error for $DATE"
    fi
  done
  
  touch /scheduler/.backfill_done
  echo ""
  echo "✅ Backfill complete!"
  echo "====================================="
fi

# Set up cron job for daily push at 00:05 UTC (yesterday's data)
echo ""
echo "Setting up daily cron job (00:05 UTC)..."
mkdir -p /var/log
touch /var/log/node-rewards-cron.log
echo "05 00 * * * /usr/local/bin/dre node-rewards push-to-victoria --victoria-url ${VICTORIA_METRICS_URL} >> /var/log/node-rewards-cron.log 2>&1" | crontab -

echo "✅ Cron job configured"
echo ""
echo "====================================="
echo "Scheduler is running. Logs:"
echo "====================================="

# Start cron in foreground
cron && tail -f /var/log/node-rewards-cron.log 2>/dev/null || cron -f
