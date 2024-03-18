# IC observability stack

This collection of software lets you use your own equipment to observe the
health and operation of the Internet Computer, or parts thereof.

This stack can run either locally in a VirtualBox virtual machine, or in
a remote machine designated by you.

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
  `sudoers``.

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

Once the provisioning configuration step is done, run:

```sh
ansible-playbook -v playbooks/prepare-node.yml
```

* If you selected Vagrant provisioning in the previous step:
  * This will provision a 2.5 GB RAM, 50 GB storage virtual Ubuntu instance on
    your machine, where the observability stack will be set up.
  * The machine will be rebooted after updates.
  * K3s will be provisioned.
* In any other case:
  * The machine will update and reboot.
  * K3s will be deployed after that.

## Troubleshooting

### For users of Vagrant-provisioned VMs

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
