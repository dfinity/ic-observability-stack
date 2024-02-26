#!/bin/bash -e

which apt-get >/dev/null && {
    which ansible >/dev/null || {
        sudo apt-get install -y ansible
        exit 0
    }
} || which dnf >/dev/null && {
    which ansible >/dev/null || {
        sudo dnf install -y ansible
        exit 0
    }
} || {
    >&2 echo "Your operating system is not currently supported by this script.  Please install the Ansible package using your operating system's package manager or the documented method for your operating system."
    exit 32
}

>&2 echo "You will now be prompted for your user account password."
>&2 echo "This will be used to become administrator and deploy various packages needed locally."
ansible-playbook -K playbooks/prepare-local-system.yml
