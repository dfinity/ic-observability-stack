# Setting up a scrape configuration for your observability stack

A *scrape configuration* is information that lets your observability stack
monitor the different systems you are interested in — primarily nodes from
the Internet Computer.  Here's a sample:

```
# Sample scrape configuration
scrape_configs:
  ic_nodes:
    mode: proxied
    nodes:
      - 2001:920:401a:1706:6800:17ff:fecb:6834
```

To make your scrape configuration, create a file named `scrape_configs.yml`
in the root folder of this project, then add the necessary data.  The file
should preferably be in YAML format, although JSON is also acceptable.

Here is a reference of the various fields that the data must have:

## `scrape_configs`

A dictionary, currently composed of only the `ic_nodes` key at the moment.

## `ic_nodes`

A dictionary with the following values:

* `nodes` (mandatory) a list where each element is one of:
  * an IPv6 address of IC nodes to monitor, as a string; IP addresses refer
    specifically to the *host* IP address of the IC node, rather than its
    *guest* IP address.
  * a list of `node`, described below.
* `mode` (optional): can be set to either `proxied` or `direct`, and defaults
  to `proxied`.
  * When set to `proxied`, the publicly-available metrics endpoint is used to
    obtain metrics from each node, at a lower resolution.
  * When set to `direct`, a private endpoint is used — this private endpoint
    may not be available to you since it is usually firewalled.

## `node`

A dictionary with the following values:

* `address`: an IPv6 address of an IC node to monitor.  This list refers
  specifically to the *host* IP address of the IC node.
* `ic_node`: the IC node name corresponding to the IC node, in the standard
  `wo2z6-ksxrk-kujkh-yqiov-cajqj-2mbuj-6sbln-qwp3x-yzvss-rul7r-uqe` format.