# Setting up a scrape configuration for your observability stack

A *scrape configuration* is information that lets your observability stack
monitor the different systems you are interested in — primarily nodes from
the Internet Computer.  Here's a sample with a static node to monitor:

```
# Sample scrape configuration
scrape_configs:
  ic_nodes:
    mode: proxied
    nodes:
      # Only monitor this node:
      - 2001:920:401a:1710:6800:f1ff:fe8c:31c2
```

Here is another sample, this time using autodiscovery of nodes to monitor:

```
# Sample scrape configuration
scrape_configs:
  ic_nodes:
    mode: proxied
    criteria:
      # Only monitor nodes from this node provider:
      node_provider_id: 5o66h-77qch-43oup-7aaui-kz5ty-tww4j-t2wmx-e3lym-cbtct-l3gpw-wae
```

To make your scrape configuration, create a file named `scrape_configs.yml`
in the `vars` folder of this project, then add the necessary data.  The file
should preferably be in YAML format, although JSON is also acceptable.  You
can then check in this file in your copy of the repository.

> ℹ️ You can also create the file `scrape_configs.yml` in the root folder.
> If you do so, then the file will be ignored by version control. The
> contents of the file in the root folder always trump the contents of
> the version-controlled file in the `vars` folder.

Once the file is created, refer to the *Updating the scrape configuration*
section on the [main usage documentation](../README.md) for the procedure
to apply the new scrape configuration.

Here is a reference of the various fields that the data must have:

## `scrape_configs`

A dictionary, currently composed of the `ic_nodes` element.

## `ic_nodes`

A dictionary with the following values:

* `nodes` (optional if `criteria` is defined, otherwise mandatory) a list
  of elements, where each element is one of:
  * an IPv6 address of IC nodes to monitor, as a string; IP addresses refer
    specifically to the *host* IP address of the IC node, rather than its
    *guest* IP address.
  * a list of `node`, described below.
* `criteria` (optional if `nodes` is defined, otherwise mandatory): a dictionary
  of criteria for auto discovery (see `criteria` below).
* `mode`: one of
  * `proxied`: (the default, if omitted) configures the stack to use the
    publicly-available metrics served by Internet Computer hosts and guests,
    on port 42372 exposed to the public.
    * Most of these metrics update roughly every 30 seconds.
    * This endpoint exposes only a limited set of metrics.
  * `direct`: configures the stack to poll the specific services' internal
    ports (such as 9100 for node exporter) directly.
    * These metrics are not publicly accessible by default, and require
      custom firewall configuration on each Internet Computer node.
    * You should not use this mode unless you are a node provider and you
      have deployed the requisite firewall rules across your infrastructure
      to open these ports up properly and securely.
    * Consult file [`scrape_profiles.yml`](../vars/scrape_profiles.yml)
      for detailed information on which ports are scraped.

## `node`

A dictionary specifiying a statically configured node, that accepts the
following values:

* `address`: (mandatory) an IPv6 address of an IC node to monitor.  This list refers
  specifically to the *host* IP address of the IC node.
* `ic_node`: (optional) the IC node name corresponding to the IC node, in the standard
  `wo2z6-ksxrk-kujkh-yqiov-cajqj-2mbuj-6sbln-qwp3x-yzvss-rul7r-uqe` format.
* `labels`: (optional) a dictionary of custom string key and value pairs to use as labels
  for this node.

## `criteria`

A dictionary specifying parameters for autodiscovery of nodes, that can contain
the following values:

* `ic_name`: the name of the IC network to monitor.  Defaults to `mercury`,
  which is the production Internet Computer.
* `node_provider_id`: if present, limits automatically discovered nodes to
  those nodes belonging to the specific node provider.  This value is a string
  that follows the typical
  `wdjjk-blh44-lxm74-ojj43-rvgf4-j5rie-nm6xs-xvnuv-j3ptn-25t4v-6ae` format.
* `operator_id`: if present, limits automatically discovered nodes to those
  nodes operated by a specific operator.  This value is a string that follows
  the same principal format as `node_provider_id`.
* `dc_id`: if present, limits automatically discovered nodes to those nodes
  in a specific datacenter.  This parameter follows the typical three-character
  datacenter ID convention.
* `subnet_id`: if present, limits automatically discovered nodes to nodes
  belonging to a specific subnet ID.

An empty criteria dictionary uses the default values (as noted above).

These criteria come from the filtering criteria specification of the
[DRE multiservice-discovery service](https://github.com/dfinity/dre/tree/main/rs/ic-observability/multiservice-discovery#get-targets)
API.
