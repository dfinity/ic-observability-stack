# IC observability stack

This collection of software lets you use your own equipment to observe the
health and operation of the Internet Computer, or parts thereof.

This stack can run either locally in a VirtualBox virtual machine, or in
a remote machine designated by you.

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
ansible-playbook -v playbooks/provision-node.yml
```

* If you selected Vagrant provisioning in the previous step:
  * This will provision a 2.5 GB RAM, 50 GB storage virtual Ubuntu instance on
    your machine, where the observability stack will be set up.
* In any other case:
  * This step will currently do nothing.

Then, run the following to upgrade the system (it will reboot once if any
updates took place):

```sh
ansible-playbook -v playbooks/update-node.yml
```

Then, run the following to deploy the stack:

```sh
ansible-playbook -v playbooks/deploy-minikube-onto-node.yml
```

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
