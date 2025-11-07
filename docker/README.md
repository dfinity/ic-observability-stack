## Command for configuring prometheus:
```bash
docker compose -f ./docker-compose.tools.yaml run --rm prom-config-builder tools/prom-config-builder/prom_config_builder.py --node-provider-id bvcsg-3od6r-jnydw-eysln-aql7w-td5zn-ay5m6-sibd2-jzojt-anwag-mqe --dc-id se1
```

# Explain how to configure contact points

- sudo chmod 777 -R ./volumes/grafana/ 
- sudo chmod 777 -R ./volumes/prometheus/
