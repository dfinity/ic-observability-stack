# To-do items

## Functionality

* Provide Prometheus + Grafana interfaces using Let's Encrypt TLS
  certificates and authenticated access, when setting up a stack on
  a SSH remote target.
* Enable auto-discovery for machines of particular node providers.
  This skips having to specify addresses manually.
* Allow the user to specify “I’m a node provider” mode during auto-
  discovery, which will cause the stack to scrape host/guest node
  exporter, orchestrator and replica directly.  This is already
  possible to do by manually saying `mode: direct` but not yet
  working in practice due to IC firewall rules.
* Reduce maintenance cost of the stack:
  * Re-use the DFINITY observability stack code to provide dashboards
    for this stack.
  * Re-use the DFINITY observability stack code to provide infrastructure
    services (such as VictoriaMetrics and Grafana) for this stack.
    * This may not end up being that necessary.

## Long shots

* Persistent storage for Grafana would be nice to have.
  Unfortunately, customizing volumes is not currently supported by
  the Grafana Operator Helm chart, and they explicitly disclaim
  it as https://grafana.github.io/grafana-operator/docs/installation/helm/#out-of-scope
  leaving us with the non-functional option of overriding the `volumes`
  key in the Grafana CRD instance, which isn't going to work because
  one cannot override single volumes, and one of the volumes created
  by the operator has a hash-based name it controls.  Therefore
  we would have to give up on using the Grafana operator and
  set up our Grafana instance manually (it's doable, but it's
  more work that, at the moment, cannot be done).

## Testing

* Test of successful Vagrant provisioning:
  * With Fedora VM.
  * With Ubuntu VM.
* Test that scrape configs work and return expected data.
* Test that Grafana dashboards are deployed.
