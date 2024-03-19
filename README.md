# IC observability stack

This collection of software lets you use your own equipment to observe the
health and operation of the Internet Computer, or parts thereof.

This stack can run either locally in a VirtualBox virtual machine, or in
a remote machine designated by you.

For usage instructions, see below under heading *Usage*.

## Prerequisites

* IPv6 connectivity.
  * If you plan to run the stack as a local VirtualBox VM, your local
    network and machine must have working IPv6 networking.
  * If you plan to run the stack in a remote machine (which will be
    configured via SSH), the remote machine must have working IPv6
    networking.
  * In both cases, tests for IPv6 connectivity will be conducted at
    the end of the provisioning step.
* Root-equivalent access on your workstation, to deploy the software
  this stack needs to be set up.
* If you plan to run this stack in a remote machine, the user account
  you log onto this machine with must have root-equivalent access via
  `sudoers`, and should be an Ubuntu machine.  Support for Fedora
  targets is in the works.

## Preparation

Clone this repository on your workstation.

Change into the directory of the cloned repository.

Run `./bootstrap.sh`.  The program will require your administrative password
(usually your local user's password) to set up the software necessary to
manage your observability stack.  **Follow the onscreen instructions as
the playbook executes.**

## Setup

Once your system is prepared, configure where the playbooks will operate.
The following command will run wizard will let you decide whether you'll
use a preexisting machine you can SSH into, or create a locally-provisoned
virtual machine using Vagrant and VirtualBox.  Run:

```sh
python3 configure.py
```

Once the provisioning configuration step is done, create your scrape
configuration variable `scrape_configs`.  This configuration will be used
to let the observability stack know which targets to obtain telemetry from.
See the documentation [on scrape configuration](doc/scrape-configs.md) for
more information on how to describe these targets.

With the scrape configuration in place, run:

```sh
ansible-playbook -v playbooks/prepare-node.yml
```

* If you selected Vagrant provisioning in the previous step:
  * This will provision a 2.5 GB RAM, 50 GB storage virtual Ubuntu instance on
    your machine, where the observability stack will be set up.
  * The machine will be rebooted after updates.
  * K3s will be provisioned.
* In any other case:
  * The remote machine will update and reboot.
  * K3s will be deployed on the remote machine after that.

Once K3s is deployed, an instance of Prometheus will be deployed onto
the observability stack node, and all the telemetry targets will be
configured.

Roughly 4 minutes after this process is done, Prometheus should be
successfully obtaining telemetry data from the targets.

## Usage

Once the stack is set up, you will be able to access Prometheus on HTTP
port 32090 of the target machine:

* If deploying via VirtualBox, the host name will be localhost, as the
  service TCP ports will be locally forwarded.
  * The URL to access will be `http://localhost:32090/`.
* If deploying on a remote machine via SSH, Prometheus will be listening
  on TCP 32090 on that machine.
  * Note that the service will be running unsecured by TLS and,
    generally, firewall rules will not permit access to this port
    remotely.
  * Therefore, you should deploy a proxy service with support for an
    HTTPS provider such as Let's Encrypt, then use the proxy service
    to reverse-proxy TCP port 32090 onto the standard HTTPS 443 port
    to the public.  Make sure to also instruct the proxy service to
    add some form of authentication.
  * You can also use SSH port forwarding to forward local connections
    to port 32090 in order to access the URL (which should be in that
    case `http://localhost:32090/` from the machine you initiated the
    forwarding).
  * In the future, we plan to offer automated SSL support for stacks
    deployed in this way.

### Querying data

The stack can be queried using the standard URL `http://localhost:32090/graph`
— a screen that lets you enter
[PromQL queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)
at will.

Try these sample queries:

* `up`
* `power_average_watts`

### Updating the scrape configuration

Whenever you want to update the scrape configuration, you can change
the appropriate `scrape_configs.yml` file and then run this command:

```sh
ansible-playbook -v playbooks/prepare-node.yml -t scrape_configs
```

This will run only the parts of the playbook that configure the
scraping on Prometheus, and nothing more.  It will certainly be much
faster, and it will skip rebooting the target machine when updates
are applied.

Be patient and pemember to wait a couple of minutes for Prometheus
to reload its scrape configuration from disk.

## Troubleshooting

### Debugging Vagrant-provisioned VMs

You can SSH into the Vagrant-provisioned VM by running the following
commands in the repository folder:

```sh
cd files/local-ubuntu
vagrant ssh observability
```

This should get you logged into the virtual machine.  You can `sudo`
without a password within the VM.

If you get an error noting:

```
The provider 'virtualbox' that was requested to back the machine
'observability' is reporting that it isn't usable on this system.
```

you most likely need to re-bootstrap, so follow the instructions
under the *Preparation* heading.

If, conversely, you get an error noting:

```
A Vagrant environment or target machine is required to run this
command. Run `vagrant init` to create a new Vagrant environment.
```

then follow the *Setup* instructions above (ensuring that you
have selected Vagrant as the provisioning mechanism).

### Telemetry targets and Prometheus configuration

Inspect which telemetry targets have been set up by browsing to the
Prometheus instance (example address: `http://localhost:32090/`), then
click on *Status* on the top bar, then click on *Targets*.  A list
should appear onscreen with the list of targets being monitored by
your observability stack, with their up/down status.

Just like the active targets appear under URL path `/targets`, the
active prometheus configuration should be accessible at URL path
`/config` of the same URL.
