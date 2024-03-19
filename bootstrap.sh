#!/bin/bash -e

u=$(uname -s)
case "$u" in
    Linux*) {
        which pip3 >/dev/null || {
            which apt-get && {
                sudo apt-get install -y python3-pip || {
                    >&2 echo pip installation failed.
                    exit 32
                }
            } || which dnf && {
                sudo dnf install -y python3-pip || {
                    >&2 echo pip installation failed.
                    exit 32
                }
            } || {
                >&2 echo "Your operating system is not currently supported by this script."
                exit 32
            }
        }
        which ansible >/dev/null && {
            ansible --version | head -1 | grep -q '[[]core' || {
                >&2 echo "Your system's Ansible version is too old"
                >&2 ansible --version
                >&@ echo "Please uninstall the existing Ansible and retry running this script.  See installation instructions provided by Ansible: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html "
                exit 18
            }
        } || {
            pip3 install --user ansible || {
                ret=$?
                >&2 echo Ansible installation failed.
                exit $ret
            }
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

>&2 echo "Ansible is going to run on your machine, and you will now be prompted for your user account password (what Ansible calls 'BECOME password').  This will be used to become administrator and deploy various packages needed locally; if 'sudo' does not require a password on this machine, simply hit ENTER.  Follow onscreen instructions as the playbook runs.  If the next step just hangs for a long period of time, interrupt it and check that you typed your root password correctly."
ansible-playbook -v -K playbooks/prepare-local-system.yml
