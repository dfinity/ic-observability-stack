# Node Rewards Dashboard - Quick Start Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Start All Services

```bash
cd /Users/pietro.di.marco/ic-observability-stack/docker
export UID=$(id -u)
export GID=$(id -g)
docker-compose up -d
```

### Step 2: Monitor Backfill Progress

The system will automatically backfill the last 40 days of metrics on first startup:

```bash
# Watch the backfill progress
docker-compose logs -f node-rewards-scheduler
```

You should see output like:
```
Starting backfill of last 40 days...
Backfilling data for 2024-12-02...
Backfilling data for 2024-12-03...
...
Backfill complete!
```

This will take approximately 5-10 minutes.

### Step 3: Access Grafana Dashboard

1. Open your browser to: **http://localhost:3000**
2. Navigate to: **Dashboards** → **Node Provider Rewards Dashboard - InfluxDB**
3. Set time range to: **Last 30 days**
4. Enjoy your node rewards metrics! 📊

## 📅 Daily Updates

The system automatically:
- Fetches yesterday's metrics every day at **00:05 UTC**
- Stores them as discrete daily data points in InfluxDB
- Updates the Grafana dashboard automatically

## 🎯 What You'll See

### Provider Overview
- Total providers and nodes
- Latest rewards calculation timestamp
- Total adjusted rewards across all providers

### Provider Summary Table
| Provider | Nodes | Base Total | Adjusted Total | Difference | Efficiency % |
|----------|-------|------------|----------------|------------|--------------|
| prov1... | 45    | 1,234,567  | 1,200,000      | -34,567    | 97.2% 🟡     |
| prov2... | 32    | 987,654    | 985,000        | -2,654     | 99.7% 🟢     |

### Trends Charts
- **Base vs Adjusted Rewards**: Daily points showing both metrics over time
- **Efficiency Over Time**: Track provider performance day by day

## 🔧 Quick Commands

### Check System Status
```bash
# View all running services
docker-compose ps

# Check InfluxDB health
curl http://localhost:8086/health

# Check if data exists
curl -H "Authorization: Token my-super-secret-auth-token" \
  "http://localhost:8086/api/v2/buckets?org=ic-org"
```

### Manual Data Push
```bash
# Push data for a specific date
docker exec -it $(docker ps -qf "name=node-rewards-scheduler") \
  dre node-rewards push-to-influx --date 2025-01-15
```

### View Logs
```bash
# Scheduler logs
docker-compose logs -f node-rewards-scheduler

# InfluxDB logs
docker-compose logs -f influxdb

# Grafana logs
docker-compose logs -f grafana
```

### Restart Services
```bash
# Restart everything
docker-compose restart

# Restart specific service
docker-compose restart node-rewards-scheduler
```

## 🎨 Dashboard Customization

### Filter by Provider
1. At the top of the dashboard, click the **Provider** dropdown
2. Select one or more providers to focus on
3. The dashboard updates automatically

### Change Time Range
- Click the time range selector (top right)
- Choose from: Last 7 days, Last 30 days, Last 90 days
- Or set a custom range

### Export Data
1. Click on any panel
2. Click the **"..."** menu
3. Select **Inspect** → **Data** → **Download CSV**

## 📊 Understanding the Metrics

### Base Rewards
- Rewards before any performance adjustments
- What providers would receive with perfect performance

### Adjusted Rewards
- Actual rewards after performance multipliers
- Reduced if nodes have high failure rates

### Efficiency %
- `(Adjusted Rewards / Base Rewards) × 100`
- **98-100%** 🟢 Excellent performance
- **95-98%** 🟡 Good performance  
- **90-95%** 🟠 Warning - check node health
- **<90%** 🔴 Poor performance - investigate immediately

## 🛠️ Troubleshooting

### No Data Appearing?

1. **Check backfill completed:**
   ```bash
   ls -la volumes/node-rewards-scheduler/backfill_done
   ```
   If this file doesn't exist, backfill is still running.

2. **Check InfluxDB has data:**
   ```bash
   docker exec -it $(docker ps -qf "name=influxdb") influx \
     --org ic-org \
     --token my-super-secret-auth-token \
     query 'from(bucket:"node-rewards") |> range(start: -30d) |> limit(n: 5)'
   ```

3. **Verify Grafana datasource:**
   - Go to Grafana → Configuration → Data Sources
   - Check "InfluxDB (Node Rewards)" is green/connected

### Dashboard Shows "No Data"?

- Make sure you've selected a time range that includes the backfilled data
- Try setting the time range to "Last 30 days"
- Check that "Provider" filter is set to "All" or specific providers

### Scheduler Container Keeps Restarting?

```bash
# Check what's wrong
docker-compose logs node-rewards-scheduler

# Common issues:
# - DRE CLI not in PATH → Update docker image
# - InfluxDB not ready → Wait a minute and check again
# - Auth issues → Verify INFLUXDB_TOKEN matches
```

## 🔐 Security Reminder

⚠️ The default InfluxDB token `my-super-secret-auth-token` is for **development only**!

For production, update in these files:
1. `docker-compose.yaml` (influxdb and scheduler services)
2. `config/grafana/provisioning/datasources/observability.yaml`

## 📚 Learn More

- Full documentation: [NODE_REWARDS_SETUP.md](./NODE_REWARDS_SETUP.md)
- InfluxDB UI: http://localhost:8086
- Grafana: http://localhost:3000

## 🎉 You're All Set!

Your node rewards monitoring system is now running and will automatically update daily. The dashboard provides real-time insights into provider performance with clean, discrete daily data points.

**Questions?** Check the full documentation in `NODE_REWARDS_SETUP.md`

