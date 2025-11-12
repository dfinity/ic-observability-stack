# IC observability stack

This collection of software lets you use your own equipment to observe the health and 
operation of the nodes in your datacenter that are part of the Internet Computer. It
is a collection of docker containers that, when deployed and configured, will collect
metrics about the performance of selected nodes and send alerts if something is off.

## How does this work?

The stack selects IC nodes and collects metrics from each node, saving them
in a local Prometheus database every few seconds.  This database is
queryable through a Grafana deployed side-to-side with Prometheus.

Nodes of the Internet Computer all make available to the public a series
of metrics (in [Prometheus text format](https://github.com/Prometheus/docs/blob/777846211d502a287ab2b304cb515dc779de3474/content/docs/instrumenting/exposition_formats.md#text-based-format))
that can be collected and analyzed by software such as this.

The stack has to be deployed within the same *network subnet* as the nodes so that 
the scraping of the nodes can take place. This practically means that the nodes and the 
machine that is running this stack have to be within the same data center and connected
to the same router.

## Prerequisites

* IPv6 connectivity.
* Root-equivalent access on your workstation, to deploy the software this stack 
  needs to be set up.
* Hardware.
  * It is recommended to run this stack on a machine with at least 16GB ram and 
    80-100GB storage.
* SSH access to the machine.
  * This is needed to later remotely connect to the services and inspect issues.
  * Setting up ssh server [guide](https://documentation.ubuntu.com/server/how-to/security/openssh-server/).

## Preparation

To start preparing your workstation for scraping and observing your nodes you have to 
`ssh` into the machine (or be physically next to it in order to run commands on the
machine).

Install [Docker](https://docs.docker.com/engine/install/) for your machine. There
shouldn't be visible differences across different operating systems. This setup has
been tested on Mac OS and Manjaro OS (Linux flavour) but hasn't been tested on 
Windows machines.

Once you can run docker commands and have `docker compose` you can proceed to the next step.

## Configuration

Now that you have `docker` you can proceed to configure the stack. 

### Ensuring proper user and group

To properly configure the user and group which will be used for all docker workloads
run the following setup script:
```bash
# NOTE: you have to be within the same directory as this README!
./setup.sh
```

### Scraping targets

First thing that you have to configure is your scraping targets. To do that, find your 
[principal id](https://support.dfinity.org/hc/en-us/articles/7365913875988-What-is-a-principal) 
that correclates to your node provider id. You can find that from the [public dashboard](https://dashboard.internetcomputer.org/network/providers). After that you should find the id of the data center to which
you are deploying this stack. You can find that information also on the [public dashboard](https://dashboard.internetcomputer.org/network/providers).

With that you can run the following command:
```bash
# NOTE: you have to be within the same directory as this README!
docker compose -f ./docker-compose.tools.yaml run --rm prom-config-builder tools/prom-config-builder/prom_config_builder.py --node-provider-id <node-provider-id> --dc-id <dc-id>
```

Example command for node provider Dfinity Stiftung for data center se1:
```bash
docker compose -f ./docker-compose.tools.yaml run --rm prom-config-builder tools/prom-config-builder/prom_config_builder.py --node-provider-id bvcsg-3od6r-jnydw-eysln-aql7w-td5zn-ay5m6-sibd2-jzojt-anwag-mqe --dc-id se1
```

Once that executes, you should be able to see a new file at `./config/prometheus/config.yaml`. 
This file contains the definitions for the scraping targets. It will be slightly different 
for each node provider and each data center. It is not versione controlled and you can 
always recreate it with running the above command if you lose it, or delete it.

### Contact points

This stack uses [Grafana](https://grafana.com/) to present the dashboards and to send
alerts. Sending alerts is done using the [contact points](https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/contact-points/) which need to be configured. Grafana supports
various contact points, some of them can be used for free, some of them are paid. 
This stack was tested with the following contact points:
* Discord [free]
* Slack
* Google chat

To setup your prefered contact point copy over the template with the following command:
```bash
cp ./config/grafana/templates/template_contact_points.yaml ./config/grafana/provisioning/alerting/contact_points.yaml
```

After that, edit the new file on path `./config/grafana/provisioning/alerting/contact_points.yaml`
and uncomment your prefered contact point and configure it (to _uncomment_ you should
remove the initial `#` from the contact point definition.

## Running the stack

To deploy the stack run the following command:
```bash
# This will spawn the containers 
docker compose -f ./docker-compose.yaml up -d 
```

It will take some time for the services to start and to sync between one another. 
You can monitor if containers are failing by running `docker ps` and see if 
there are some restarts happening in the containers. To see more about Troubleshooting
read *Troubleshooting*

## Usage

Once started, you will see the following applications:
* Prometheus - http://localhost:9090
* Grafana - http://localhost:3000 - default creds can be see in `./config/grafana/grafana.ini` 
* Service discovery - http://localhost:8000

After 5-10 minutes you should see targets discovered in prometheus on the [targets page](http://localhost:9090/targets?search=). Initially, they might apear in red and if you keep monitoring they should
slowly start getting blue, which means that the targets are successfuly scraped.

You should also see some data incoming in the grafana [sample dashboard for the 
node exporter](http://localhost:3000/d/1/node-exporter?orgId=1&from=now-3h&to=now&timezone=utc&var-datasource=prometheus&var-instance=$__all&var-diskdevice=%5Ba-z%5D%2B%7Cnvme%5B0-9%5D%2Bn%5B0-9%5D%2B%7Cmmcblk%5B0-9%5D%2B).
Here, you can see various information about the performance of nodes and their health.

[Alerting tab](http://localhost:3000/alerting/list) will show `obs alert evaluations` 
which will contain a list of preconfigured alerts. Here you can see if any of the 
alerts are in in a problematic state. Most of the time they should be in `Normal` 
state, this means that everything is fine. Some of them may occasionally go into a 
`Pending` state, which means that they crossed the threshold for an alert but still
isn't happening for long enough to consider this a problem. When a `Pending` alert
is happening for long enough it will go into `Error` mode and you should receive an
alert on your preconfigured contact point. 

*NOTE*: Not all alerts are configured to send notifications if they fire, usually
because they are just warnings and cannot be acted upon. To see which are and 
which aren't you can see `./config/grafana/provisioning/alerting/alerts.yaml` and
see which have the lavel `severity: critical` attached to them because only they
will send alerts to your contact point. If you wish to send all of them, just replace
the other ones that contain `severity: warning` with `severity: critical`.

### Access to the services of the stack

To access the stack remotely you can do the following:
```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -L 8000:localhost:8000 <machine-with-obs-stack>
```

Example command with all parameters:
```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -i ~/.ssh/priv_key.pem myuser@192.168.15.15
```

## Extending

Extending this stack usually means adding new alerts or dashboards. Those might
be your own modifications or the ones that come from someone else.

### Dashboards

Building grafana dashboards is usually done via [grafana ui](http://localhost:3000/dashboard/new?orgId=1&from=now-6h&to=now&timezone=browser). You can follow
[this tutorial](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/create-dashboard/) from grafana to make your custom dashboards.

After creating the dashboard it is suggested to export it and save it
`./config/grafana/provisioning/dashboards/`. This will make sure that
if you later need to restore the dashboard or do a fresh deployment 
of grafana it will be persisted.

*NOTE*: Storing a dashboard and restarting can make lead to errors 
due to overlapping dashboard `uids`. If you export the dashboard and 
save it you should, be sure to do a clean deployment of grafana.

### Alerts

Adding grafana alerts can also be done via [grafana ui](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/).

Similarly to dashboards, it is suggested to export alerts and save them 
in `./config/grafana/provisioning/alerting/` which will make sure that
they persist after full grafana redeployments.

## Troubleshooting

### Service discovery failing

It is possible that usually due to networking issues, service discovery component
may fail. To debug why you can run the following command to inspect the logs:
```bash
# From the same folder of this README
docker compose logs multiservice-discovery
```

You may see something along the lines of:
```bash
multiservice-discovery-1  | Nov 10 13:25:07.044 WARN Failed to sync registry for mercury @ interval Instant { tv_sec: 9050, tv_nsec: 707832535 }: SyncWithNnsFailed { failures: [("targets", RegistryTransportError { source: UnknownError("Failed to query get_certified_changes_since on canister rwlgt-iiaaa-aaaaa-aaaaa-cai: Request failed for http://[2606:fb40:201:1001:6801:2fff:fef5:b129]:8080/api/v2/canister/rwlgt-iiaaa-aaaaa-aaaaa-cai/query: hyper_util::client::legacy::Error(Connect, ConnectError(\"tcp connect error\", [2606:fb40:201:1001:6801:2fff:fef5:b129]:8080, Os { code: 101, kind: NetworkUnreachable, message: \"Network is unreachable\" }))") })] }
```

This is usually a transient error and may happen from time to time. What this 
means is that the discovery cannot sync with the registry canister and may be 
serving stale targets. Usually this is acceptable but if that happens when 
deploying and the initial sync fails you may be unable to see any of your 
nodes. As long as you can see your nodes on the following link you can safely
ignore the transient failures.
```bash
curl http://localhost:8000/prom/targets?node_provider_id=<node-provider-id>&dc_id=<dc-id>
```

*NOTE*: The initial sync of service discovery may take up to 15 minutes! Syncing 
will be clearly logged in the multiservice discovery.

### Prometheus

#### No targets visible in targets view

If you don't see anything in the [prometheus targets view](http://localhost:9090/targets?search=), 
that means that prometheus failed to receive targets from the service discovery.

To check the logs run:
```bash
# From the same folder of this README
docker compose logs prometheus
```

Check if you can see your nodes by running the following command:
```bash
curl http://localhost:8000/prom/targets?node_provider_id=<node-provider-id>&dc_id=<dc-id>
```

#### Targets visible but are being shown in read

You should now see 4 jobs:
* `host_node_exporter`
* `node_exporter`
* `orchestrator`
* `replica`

If any of them are shown in read it means that some of the targets (or all of them)
are failing to be scraped. You can see that from the logs as well:
```bash
# From the same folder of this README
docker compose logs prometheus
```

This means that the prometheus scraper cannot reach the nodes it is trying
to scrape. It can be because the workstation for this observability stack
isn't in the same network subnet as the nodes, or due to other network 
issues.

### Stack restart

To make a full clean restart (or partial) you can do the following:
* Ensure that everything you created through grafana ui is exported
  * Dashboards (save them into `./config/grafana/provisioning/dashboards/`)
  * Alerts (save them into `./config/grafana/provisioning/alerting/`)
  * Contact points (save them into `./config/grafana/provisioning/alerting/`)
  * Message templates (save them into `./config/grafana/provisioning/alerting/`)
  * Notification policies (save them into `./config/grafana/provisioning/alerting/`)
* If you haven't created the resources, or don't mind losing them 
  you can proceed.
* Stop the stack: `docker compose -f ./docker-compose.yaml down`
* Clean the volumes. You don't have to clean everything, pick just
  ones that you wish to restart fully:
  * prometheus: `rm -rf ./volumes/prometheus/`
  * grafana: `rm -rf ./volumes/grafana/`
  * multiservice discovery: `rm -rf ./volumes/msd/`
* Reset the folder structure: `git checkout -- ./volumes/`
* Run the stack again: `docker compose -f ./docker-compose.yaml up -d`

