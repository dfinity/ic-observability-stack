#!/bin/bash -e

UNSUPPORTED=32
FAILED=16
MANUAL_INTERVENTION=8

check_ansible_version() {
    if ansible --version | head -1 | grep -q '[[]core'
    then
        >&2 echo '* Ansible found and up-to-date enough.'
    else
        >&2 echo "Your system's Ansible version is too old"
        >&2 ansible --version
        >&@ echo "Please uninstall the existing Ansible and retry running this script.  See installation instructions provided by Ansible: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html "
        exit $MANUAL_INTERVENTION
    fi
}

got() {
    which "$1" >/dev/null 2>&1
}

case "$(uname -s)" in
    Linux*) {
        if got pip3
        then
            >&2 echo '* pip found and installed.'
        else
            if got apt-get
            then
                sudo apt-get install -y python3-pip || {
                    >&2 echo "* pip installation failed."
                    exit $FAILED
                }
            elif got dnf
            then
                sudo dnf install -y python3-pip || {
                    >&2 echo "* pip installation failed."
                    exit $FAILED
                }
            else
                >&2 echo "Your operating system is not currently supported by this script.  Please install the Python pip package using your operating system's package manager or the documented method for your operating system."
                exit $UNSUPPORTED
            fi
        fi
        if got ansible
        then
            check_ansible_version
        else
            pip3 install --user ansible || {
                >&2 echo "* Ansible installation failed."
                exit $FAILED
            }
        fi
    };;
    Darwin*) {
        if got brew
        then
            >&2 echo "* Homebrew found and installed."
        else
            >&2 echo "Homebrew is not installed, but it is necessary.  Please install Homebrew by running:"
            >&2 echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            >&2 read -p 'Do you want to run that command right now [y/n]?' install_brew
            if [ "$install_brew" == "y" ]
            then
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || exit $FAILED
            else
                exit $MANUAL_INTERVENTION
            fi
        fi
        if got ansible
        then
            check_ansible_version
        else
            brew install ansible || {
                >&2 echo "* Ansible installation failed."
                exit $FAILED
            }
        fi
    };;
    *) {
       >&2 echo "Your operating system is not currently supported by this script.  Please install the Ansible package using your operating system's package manager or the documented method for your operating system."
        exit $UNSUPPORTED
    };;
esac

>&2 echo "Ansible is going to run on your machine to install some software, and you will now be prompted for your user account password (what Ansible calls 'BECOME password').  This will be used to become administrator and deploy various packages needed locally; if 'sudo' does not require a password on this machine, simply hit ENTER.  Follow onscreen instructions as the playbook runs.  If the next step hangs for a long period of time, interrupt it and check that you typed your root password correctly."
export PATH="$HOME/.local/bin:$PATH"
ansible-playbook -v -K playbooks/prepare-local-system.yml
