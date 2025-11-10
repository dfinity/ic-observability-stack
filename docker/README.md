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

### Volumes

Since prometheus and grafana have their own users which probably differ from yours
you need to make the volumes readable and writiable by those users. There are number
of ways how you can do this, but the easiest is to make it readable and writable 
for all users on the machine:
```bash
sudo chmod 777 -R ./volumes/grafana/
sudo chmod 777 -R ./volumes/prometheus/
```

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
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 <machine-with-obs-stack>
```

Example command with all parameters:
```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -i ~/.ssh/priv_key.pem myuser@192.168.15.15
```

## Extending
### Dashboards
### Alerts

## Troubleshooting


- sudo chmod 777 -R ./volumes/grafana/ 
- sudo chmod 777 -R ./volumes/prometheus/
