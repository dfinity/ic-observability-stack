## Command for configuring prometheus:
```bash
docker compose -f ./docker-compose.tools.yaml run --rm prom-config-builder config/prometheus/prom_config_builder.py --node-provider-id <np-id> [--dc-id <dc-id>]
```
