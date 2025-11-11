# Node Rewards Dashboard with InfluxDB

This setup provides a Grafana dashboard displaying daily node rewards metrics from the IC network, stored in InfluxDB with discrete daily data points.

## Architecture

```
┌─────────────────────┐
│  DRE CLI (Rust)     │ ──> Fetches daily metrics from IC Node Rewards Canister
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   InfluxDB 2.7      │ ──> Stores daily discrete metrics
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Grafana 12.2.1    │ ──> Displays dashboards with daily data points
└─────────────────────┘

┌─────────────────────┐
│ Node Rewards        │ ──> Runs daily at 00:05 UTC + backfills 40 days on startup
│ Scheduler (cron)    │
└─────────────────────┘
```

## Components

### 1. InfluxDB
- **Image**: `influxdb:2.7`
- **Port**: `8086`
- **Organization**: `ic-org`
- **Bucket**: `node-rewards`
- **Retention**: 90 days
- **Token**: `my-super-secret-auth-token` (configured in docker-compose.yaml)

### 2. Node Rewards Scheduler
- **Image**: `ghcr.io/dfinity/dre/dre:latest`
- **Function**: 
  - Backfills last 40 days of metrics on first startup
  - Runs daily at 00:05 UTC to push yesterday's metrics
- **Command**: `dre node-rewards push-to-influx --date <YYYY-MM-DD>`

### 3. Grafana Dashboard
- **Dashboard**: `Node Provider Rewards Dashboard - InfluxDB`
- **UID**: `node-rewards-influxdb`
- **Data Source**: InfluxDB (Flux queries)
- **Features**:
  - Daily discrete data points (not continuous)
  - Provider overview statistics
  - Base vs Adjusted rewards trends
  - Efficiency metrics over time
  - Provider filtering

## Metrics Stored

### Provider-Level Metrics
- `latest_nodes_count`: Number of nodes per provider
- `latest_total_base_rewards_xdr_permyriad`: Base rewards (before performance adjustment)
- `latest_total_adjusted_rewards_xdr_permyriad`: Adjusted rewards (after performance adjustment)

### Node-Level Metrics
- `latest_original_failure_rate`: Original failure rate per node
- `latest_relative_failure_rate`: Relative failure rate per node

### Subnet-Level Metrics
- `subnet_failure_rate`: Failure rate per subnet

### Governance Metrics
- `governance_latest_reward_event_timestamp_seconds`: Latest rewards distribution timestamp

## Data Flow

1. **Daily Push (00:05 UTC)**:
   ```
   DRE CLI → IC Node Rewards Canister → Fetch Yesterday's Data → Push to InfluxDB
   ```

2. **Backfill (On Startup)**:
   ```
   For each day in last 40 days:
     DRE CLI → IC Node Rewards Canister → Fetch Day's Data → Push to InfluxDB
   ```

3. **Grafana Visualization**:
   ```
   Grafana → Flux Query → InfluxDB → Daily Discrete Data Points → Dashboard
   ```

## Setup Instructions

### 1. Start the Services

```bash
cd /path/to/ic-observability-stack/docker
export UID=$(id -u)
export GID=$(id -g)
docker-compose up -d
```

### 2. Verify InfluxDB

```bash
# Check InfluxDB is running
curl http://localhost:8086/health

# Check bucket exists
curl -H "Authorization: Token my-super-secret-auth-token" \
  http://localhost:8086/api/v2/buckets?org=ic-org
```

### 3. Check Backfill Progress

```bash
# View scheduler logs
docker-compose logs -f node-rewards-scheduler
```

The backfill will take some time as it fetches 40 days of historical data.

### 4. Access Grafana

1. Open browser: `http://localhost:3000`
2. Navigate to: Dashboards → Node Provider Rewards Dashboard - InfluxDB
3. Select time range: Last 30 days (or desired range)
4. Filter by provider (optional)

## Dashboard Features

### Overview Section
- **Latest Rewards Calculation**: Timestamp of most recent rewards distribution
- **Total Providers**: Count of all providers
- **Total Nodes**: Sum of all nodes across providers
- **Total Adjusted Rewards**: Sum of adjusted rewards (in XDR)

### Provider Summary Table
Shows for each provider:
- Number of nodes
- Base total rewards
- Adjusted total rewards  
- Difference (Adjusted - Base)
- Efficiency % (Adjusted/Base * 100)

### Trends Charts
- **Base vs Adjusted Rewards Over Time**: Daily points showing both metrics
- **Provider Rewards Efficiency Over Time**: Daily efficiency percentage

## Configuration

### InfluxDB Settings
Edit in `docker-compose.yaml`:
```yaml
influxdb:
  environment:
    DOCKER_INFLUXDB_INIT_TOKEN: my-super-secret-auth-token  # Change this!
    DOCKER_INFLUXDB_INIT_BUCKET: node-rewards
    DOCKER_INFLUXDB_INIT_RETENTION: 90d
```

### Scheduler Settings
Edit in `config/node-rewards-scheduler/entrypoint.sh`:
- Backfill days: Change `{40..1}` to different range
- Schedule time: Change `"tomorrow 00:05"` to different time

### Grafana Datasource
Edit in `config/grafana/provisioning/datasources/observability.yaml`:
```yaml
- name: InfluxDB (Node Rewards)
  uid: influxdb-node-rewards
  url: http://localhost:8086
  secureJsonData:
    token: my-super-secret-auth-token  # Must match InfluxDB token
```

## Troubleshooting

### No Data in Dashboard

1. Check InfluxDB has data:
   ```bash
   docker exec -it $(docker ps -qf "name=influxdb") influx \
     --org ic-org \
     --token my-super-secret-auth-token \
     query 'from(bucket:"node-rewards") |> range(start: -30d) |> limit(n: 10)'
   ```

2. Check scheduler logs:
   ```bash
   docker-compose logs node-rewards-scheduler
   ```

3. Verify backfill completed:
   ```bash
   # Check if backfill marker exists
   ls -la volumes/node-rewards-scheduler/backfill_done
   ```

### Scheduler Not Running

```bash
# Restart scheduler
docker-compose restart node-rewards-scheduler

# Check entrypoint is executable
ls -l config/node-rewards-scheduler/entrypoint.sh
```

### Manual Data Push

You can manually push data for a specific date:

```bash
# Inside the scheduler container
docker exec -it $(docker ps -qf "name=node-rewards-scheduler") \
  dre node-rewards push-to-influx --date 2025-01-15
```

### Query InfluxDB Directly

```bash
# List measurements
curl -XPOST http://localhost:8086/api/v2/query \
  -H "Authorization: Token my-super-secret-auth-token" \
  -H "Content-Type: application/vnd.flux" \
  --data 'import "influxdata/influxdb/schema"
schema.measurements(bucket: "node-rewards")'
```

## Data Retention

- InfluxDB retention policy: **90 days**
- After 90 days, old data is automatically deleted
- To change retention, modify `DOCKER_INFLUXDB_INIT_RETENTION` in docker-compose.yaml

## Backup and Restore

### Backup InfluxDB Data
```bash
# Backup to tar.gz
docker exec $(docker ps -qf "name=influxdb") \
  influx backup /tmp/backup -t my-super-secret-auth-token
  
docker cp $(docker ps -qf "name=influxdb"):/tmp/backup ./influxdb-backup
tar -czf influxdb-backup-$(date +%Y%m%d).tar.gz influxdb-backup
```

### Restore InfluxDB Data
```bash
# Extract backup
tar -xzf influxdb-backup-YYYYMMDD.tar.gz

# Copy to container
docker cp influxdb-backup $(docker ps -qf "name=influxdb"):/tmp/

# Restore
docker exec $(docker ps -qf "name=influxdb") \
  influx restore /tmp/influxdb-backup -t my-super-secret-auth-token
```

## Development

### Testing Queries in InfluxDB UI

1. Open http://localhost:8086
2. Login with username/password from docker-compose
3. Go to Data Explorer
4. Write Flux queries to test data

### Modifying the Dashboard

1. Edit dashboard in Grafana UI
2. Export JSON: Dashboard Settings → JSON Model → Copy
3. Save to: `config/grafana/provisioning/dashboards/node-rewards/node-rewards-influx.json`
4. Restart Grafana: `docker-compose restart grafana`

## Performance Notes

- **Data Volume**: ~1 data point per provider per day
- **Query Performance**: Flux queries are optimized for daily aggregations
- **Backfill Time**: ~5-10 minutes for 40 days (depends on number of providers)
- **Daily Push Time**: ~10-30 seconds

## Security Notes

⚠️ **Important**: The default token `my-super-secret-auth-token` is for development only!

For production:
1. Generate a secure token: `openssl rand -hex 32`
2. Update in docker-compose.yaml (influxdb and scheduler)
3. Update in datasources/observability.yaml
4. Restart all services

## References

- [InfluxDB 2.x Documentation](https://docs.influxdata.com/influxdb/v2.7/)
- [Flux Query Language](https://docs.influxdata.com/flux/v0.x/)
- [Grafana InfluxDB Data Source](https://grafana.com/docs/grafana/latest/datasources/influxdb/)
- [DRE CLI Documentation](../../dre/rs/cli/README.md)

