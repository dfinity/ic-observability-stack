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
manage your observability stack.

## Setup

Once your system is prepared, configure where the playbooks will operate:

```sh
python3 configure.py
```

Now run:

```sh
ansible-playbook playbooks/provision-node.yml
```

* If you selected Vagrant provisioning in the previous step:
  * This will provision a 2.5 GB RAM, 50 GB storage virtual Ubuntu instance on
    your machine, where the observability stack will be set up.
* In any other case:
  * This step will do nothing.

Then, run the following to upgrade the system (it will reboot once if any
updates took place):

```sh
ansible-playbook playbooks/update-node.yml
```

Then, run the following to deploy the stack:

```sh
ansible-playbook playbooks/deploy-minikube-onto-node.yml
```
