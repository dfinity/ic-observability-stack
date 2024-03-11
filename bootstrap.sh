#!/bin/bash -e

u=$(uname -s)
case "$u" in
    Linux*) {
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
        } ||
        {
            >&2 echo "Your Linux distribution is not currently supported by this script.  Please install the Ansible package using your operating system's package manager or the documented method for your operating system."
            exit 32
        }
    };;
    Darwin*) {
        which brew >/dev/null || {
            >&2 echo "Homebrew is not installed, but it is necessary.  Please install Homebrew by running:"
            >&2 echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            >&2 read -p 'Do you want to run that command right now [y/n]?' install_brew
            if [ "$install_brew" == "y" ]
            then
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || exit $?
            else
                exit 4
            fi
        }
        which ansible >/dev/null || {
            brew install ansible
            exit 0
        }
    };;
    *) {
       >&2 echo "Your operating system is not currently supported by this script.  Please install the Ansible package using your operating system's package manager or the documented method for your operating system."
        exit 32
    };;
esac

>&2 echo "Ansible is going to run on your machine, and you will now be prompted for your user account password (what Ansible calls 'BECOME password').  This will be used to become administrator and deploy various packages needed locally."
ansible-playbook -K playbooks/prepare-local-system.yml
