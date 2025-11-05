# To-do items

## Functionality

* Reduce maintenance cost of the stack:
  * Re-use the DFINITY observability stack code to provide dashboards
    for this stack.
* Allow specifying the setup local-path where k3s will store data
* Set sane defaults for prometheus resources
* Add alerting configuration
* Rework the sample dashboard to use principal ids instead of hosts
* Document service discovery endpoint

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
