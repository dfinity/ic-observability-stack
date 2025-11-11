#!/bin/bash
set -e

# Backfill last 40 days on startup
backfill_data() {
    echo "Starting backfill of last 40 days..."
    for i in {40..1}; do
        date=$(date -u -d "$i days ago" +%Y-%m-%d || date -u -v-${i}d +%Y-%m-%d)
        echo "Backfilling data for $date..."
        dre node-rewards push-to-influx --date "$date" || echo "Warning: Failed to backfill $date"
    done
    echo "Backfill complete!"
}

# Run daily job at 00:05 UTC
run_daily_job() {
    # Calculate time until next 00:05 UTC
    current_time=$(date -u +%s)
    next_run=$(date -u -d "tomorrow 00:05" +%s 2>/dev/null || date -u -v+1d -v00H -v05M +%s)
    
    if [ $next_run -le $current_time ]; then
        next_run=$(date -u -d "00:05" +%s 2>/dev/null || date -u -v00H -v05M +%s)
    fi
    
    sleep_seconds=$((next_run - current_time))
    
    echo "Next run scheduled at $(date -u -d @$next_run +%Y-%m-%d\ %H:%M:%S 2>/dev/null || date -u -r $next_run +%Y-%m-%d\ %H:%M:%S) UTC (in ${sleep_seconds}s)"
    sleep $sleep_seconds
    
    # Run the job for yesterday
    yesterday=$(date -u -d "yesterday" +%Y-%m-%d 2>/dev/null || date -u -v-1d +%Y-%m-%d)
    echo "Running daily job for $yesterday..."
    dre node-rewards push-to-influx --date "$yesterday"
}

# Check if backfill marker exists
BACKFILL_MARKER="/scheduler/backfill_done"
if [ ! -f "$BACKFILL_MARKER" ]; then
    backfill_data
    touch "$BACKFILL_MARKER"
fi

# Run daily job in a loop
while true; do
    run_daily_job
done

