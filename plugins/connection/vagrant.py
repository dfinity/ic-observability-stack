# Based on vagra.py from Ansible
#
# Copyright (c) 2023 DFINITY Stiftung
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import os
import os.path
import subprocess

from ansible.errors import AnsibleError
from ansible.module_utils.common.process import get_bin_path
from ansible.module_utils._text import to_native
from ansible.utils.display import Display
from ansible.plugins.connection import ssh

__metaclass__ = type


DOCUMENTATION = """
    connection: vagrant
    short_description: Interact with local Vagrant boxes
    description:
        - Run commands or put/fetch files to a Vagrant box on the Ansible controller.
    options:
      host:
          description: Hostname/IP to connect to.
          default: inventory_hostname
          type: string
          vars:
               - name: inventory_hostname
               - name: ansible_host
               - name: ansible_ssh_host
               - name: delegated_vars['ansible_host']
               - name: delegated_vars['ansible_ssh_host']
      host_key_checking:
          description: Determines if SSH should check host keys.
          default: True
          type: boolean
          ini:
              - section: defaults
                key: 'host_key_checking'
              - section: ssh_connection
                key: 'host_key_checking'
                version_added: '2.5'
          env:
              - name: ANSIBLE_HOST_KEY_CHECKING
              - name: ANSIBLE_SSH_HOST_KEY_CHECKING
                version_added: '2.5'
          vars:
              - name: ansible_host_key_checking
                version_added: '2.5'
              - name: ansible_ssh_host_key_checking
                version_added: '2.5'
      password:
          description: Authentication password for the O(remote_user). Can be supplied as CLI option.
          type: string
          vars:
              - name: ansible_password
              - name: ansible_ssh_pass
              - name: ansible_ssh_password
      sshpass_prompt:
          description:
              - Password prompt that sshpass should search for. Supported by sshpass 1.06 and up.
              - Defaults to C(Enter PIN for) when pkcs11_provider is set.
          default: ''
          type: string
          ini:
              - section: 'ssh_connection'
                key: 'sshpass_prompt'
          env:
              - name: ANSIBLE_SSHPASS_PROMPT
          vars:
              - name: ansible_sshpass_prompt
          version_added: '2.10'
      ssh_args:
          description: Arguments to pass to all SSH CLI tools.
          default: '-C -o ControlMaster=auto -o ControlPersist=60s'
          type: string
          ini:
              - section: 'ssh_connection'
                key: 'ssh_args'
          env:
              - name: ANSIBLE_SSH_ARGS
          vars:
              - name: ansible_ssh_args
                version_added: '2.7'
      ssh_common_args:
          description: Common extra args for all SSH CLI tools.
          type: string
          ini:
              - section: 'ssh_connection'
                key: 'ssh_common_args'
                version_added: '2.7'
          env:
              - name: ANSIBLE_SSH_COMMON_ARGS
                version_added: '2.7'
          vars:
              - name: ansible_ssh_common_args
          cli:
              - name: ssh_common_args
          default: ''
      ssh_executable:
          default: ssh
          description:
            - This defines the location of the SSH binary. It defaults to V(ssh) which will use the first SSH binary available in $PATH.
            - This option is usually not required, it might be useful when access to system SSH is restricted,
              or when using SSH wrappers to connect to remote hosts.
          type: string
          env: [{name: ANSIBLE_SSH_EXECUTABLE}]
          ini:
          - {key: ssh_executable, section: ssh_connection}
          #const: ANSIBLE_SSH_EXECUTABLE
          version_added: "2.2"
          vars:
              - name: ansible_ssh_executable
                version_added: '2.7'
      sftp_executable:
          default: sftp
          description:
            - This defines the location of the sftp binary. It defaults to V(sftp) which will use the first binary available in $PATH.
          type: string
          env: [{name: ANSIBLE_SFTP_EXECUTABLE}]
          ini:
          - {key: sftp_executable, section: ssh_connection}
          version_added: "2.6"
          vars:
              - name: ansible_sftp_executable
                version_added: '2.7'
      scp_executable:
          default: scp
          description:
            - This defines the location of the scp binary. It defaults to V(scp) which will use the first binary available in $PATH.
          type: string
          env: [{name: ANSIBLE_SCP_EXECUTABLE}]
          ini:
          - {key: scp_executable, section: ssh_connection}
          version_added: "2.6"
          vars:
              - name: ansible_scp_executable
                version_added: '2.7'
      scp_extra_args:
          description: Extra exclusive to the C(scp) CLI
          type: string
          vars:
              - name: ansible_scp_extra_args
          env:
            - name: ANSIBLE_SCP_EXTRA_ARGS
              version_added: '2.7'
          ini:
            - key: scp_extra_args
              section: ssh_connection
              version_added: '2.7'
          cli:
            - name: scp_extra_args
          default: ''
      sftp_extra_args:
          description: Extra exclusive to the C(sftp) CLI
          type: string
          vars:
              - name: ansible_sftp_extra_args
          env:
            - name: ANSIBLE_SFTP_EXTRA_ARGS
              version_added: '2.7'
          ini:
            - key: sftp_extra_args
              section: ssh_connection
              version_added: '2.7'
          cli:
            - name: sftp_extra_args
          default: ''
      ssh_extra_args:
          description: Extra exclusive to the SSH CLI.
          type: string
          vars:
              - name: ansible_ssh_extra_args
          env:
            - name: ANSIBLE_SSH_EXTRA_ARGS
              version_added: '2.7'
          ini:
            - key: ssh_extra_args
              section: ssh_connection
              version_added: '2.7'
          cli:
            - name: ssh_extra_args
          default: ''
      reconnection_retries:
          description:
            - Number of attempts to connect.
            - Ansible retries connections only if it gets an SSH error with a return code of 255.
            - Any errors with return codes other than 255 indicate an issue with program execution.
          default: 0
          type: integer
          env:
            - name: ANSIBLE_SSH_RETRIES
          ini:
            - section: connection
              key: retries
            - section: ssh_connection
              key: retries
          vars:
            - name: ansible_ssh_retries
              version_added: '2.7'
      port:
          description: Remote port to connect to.
          type: int
          ini:
            - section: defaults
              key: remote_port
          env:
            - name: ANSIBLE_REMOTE_PORT
          vars:
            - name: ansible_port
            - name: ansible_ssh_port
          keyword:
            - name: port
      remote_user:
          description:
              - User name with which to login to the remote server, normally set by the remote_user keyword.
              - If no user is supplied, Ansible will let the SSH client binary choose the user as it normally.
          type: string
          ini:
            - section: defaults
              key: remote_user
          env:
            - name: ANSIBLE_REMOTE_USER
          vars:
            - name: ansible_user
            - name: ansible_ssh_user
          cli:
            - name: user
          keyword:
            - name: remote_user
      pipelining:
          env:
            - name: ANSIBLE_PIPELINING
            - name: ANSIBLE_SSH_PIPELINING
          ini:
            - section: defaults
              key: pipelining
            - section: connection
              key: pipelining
            - section: ssh_connection
              key: pipelining
          vars:
            - name: ansible_pipelining
            - name: ansible_ssh_pipelining

      private_key_file:
          description:
              - Path to private key file to use for authentication.
          type: string
          ini:
            - section: defaults
              key: private_key_file
          env:
            - name: ANSIBLE_PRIVATE_KEY_FILE
          vars:
            - name: ansible_private_key_file
            - name: ansible_ssh_private_key_file
          cli:
            - name: private_key_file
              option: '--private-key'

      control_path:
        description:
          - This is the location to save SSH's ControlPath sockets, it uses SSH's variable substitution.
          - Since 2.3, if null (default), ansible will generate a unique hash. Use ``%(directory)s`` to indicate where to use the control dir path setting.
          - Before 2.3 it defaulted to ``control_path=%(directory)s/ansible-ssh-%%h-%%p-%%r``.
          - Be aware that this setting is ignored if C(-o ControlPath) is set in ssh args.
        type: string
        env:
          - name: ANSIBLE_SSH_CONTROL_PATH
        ini:
          - key: control_path
            section: ssh_connection
        vars:
          - name: ansible_control_path
            version_added: '2.7'
      control_path_dir:
        default: ~/.ansible/cp
        description:
          - This sets the directory to use for ssh control path if the control path setting is null.
          - Also, provides the ``%(directory)s`` variable for the control path setting.
        type: string
        env:
          - name: ANSIBLE_SSH_CONTROL_PATH_DIR
        ini:
          - section: ssh_connection
            key: control_path_dir
        vars:
          - name: ansible_control_path_dir
            version_added: '2.7'
      sftp_batch_mode:
        default: true
        description: 'TODO: write it'
        env: [{name: ANSIBLE_SFTP_BATCH_MODE}]
        ini:
        - {key: sftp_batch_mode, section: ssh_connection}
        type: bool
        vars:
          - name: ansible_sftp_batch_mode
            version_added: '2.7'
      ssh_transfer_method:
        description:
            - "Preferred method to use when transferring files over ssh"
            - Setting to 'smart' (default) will try them in order, until one succeeds or they all fail
            - For OpenSSH >=9.0 you must add an additional option to enable scp (scp_extra_args="-O")
            - Using 'piped' creates an ssh pipe with C(dd) on either side to copy the data
        choices: ['sftp', 'scp', 'piped', 'smart']
        type: string
        env: [{name: ANSIBLE_SSH_TRANSFER_METHOD}]
        ini:
            - {key: transfer_method, section: ssh_connection}
        vars:
            - name: ansible_ssh_transfer_method
              version_added: '2.12'
      scp_if_ssh:
        deprecated:
              why: In favor of the O(ssh_transfer_method) option.
              version: "2.17"
              alternatives: O(ssh_transfer_method)
        default: smart
        description:
          - "Preferred method to use when transferring files over SSH."
          - When set to V(smart), Ansible will try them until one succeeds or they all fail.
          - If set to V(True), it will force 'scp', if V(False) it will use 'sftp'.
          - For OpenSSH >=9.0 you must add an additional option to enable scp (C(scp_extra_args="-O"))
          - This setting will overridden by O(ssh_transfer_method) if set.
        env: [{name: ANSIBLE_SCP_IF_SSH}]
        ini:
        - {key: scp_if_ssh, section: ssh_connection}
        vars:
          - name: ansible_scp_if_ssh
            version_added: '2.7'
      use_tty:
        version_added: '2.5'
        default: true
        description: add -tt to ssh commands to force tty allocation.
        env: [{name: ANSIBLE_SSH_USETTY}]
        ini:
        - {key: usetty, section: ssh_connection}
        type: bool
        vars:
          - name: ansible_ssh_use_tty
            version_added: '2.7'
      vagrantfile:
        description:
            - Path to the Vagrantfile that instantiated the Vagrant machine
        default: ./Vagrantfile
        vars:
            - name: ansible_vagrantfile
      vagrant_exe:
        description:
            - User specified Vagrant binary
        ini:
          - section: vagrant_connection
            key: exe
        env:
          - name: ANSIBLE_VAGRANT_EXE
        vars:
          - name: ansible_vagrant_exe
        default: vagrant
      timeout:
        default: 10
        description:
            - This is the default amount of time we will wait while establishing an SSH connection.
            - It also controls how long we can wait to access reading the connection once established (select on the socket).
        env:
            - name: ANSIBLE_TIMEOUT
            - name: ANSIBLE_SSH_TIMEOUT
              version_added: '2.11'
        ini:
            - key: timeout
              section: defaults
            - key: timeout
              section: ssh_connection
              version_added: '2.11'
        vars:
          - name: ansible_ssh_timeout
            version_added: '2.11'
        cli:
          - name: timeout
        type: integer
      pkcs11_provider:
        version_added: '2.12'
        default: ""
        type: string
        description:
          - "PKCS11 SmartCard provider such as opensc, example: /usr/local/lib/opensc-pkcs11.so"
          - Requires sshpass version 1.06+, sshpass must support the -P option.
        env: [{name: ANSIBLE_PKCS11_PROVIDER}]
        ini:
          - {key: pkcs11_provider, section: ssh_connection}
        vars:
          - name: ansible_ssh_pkcs11_provider
"""


display = Display()


def get_cachedir():
    return os.environ.get("XDG_CACHE_DIR", os.path.expanduser("~/.cache"))


class Connection(ssh.Connection):
    """Local Vagrant based connections"""

    transport = "vagrant"
    documentation = DOCUMENTATION
    has_pipelining = True
    # su currently has an undiagnosed issue with calculating the file
    # checksums (so copy, for instance, doesn't work right)
    # Have to look into that before re-enabling this
    has_tty = False

    def _connect(self):
        """connect to the Vagrant host"""
        if os.path.isabs(self.get_option("vagrant_exe")):
            self.vagrant_cmd = self.get_option("vagrant_exe")
        else:
            try:
                self.vagrant_cmd = get_bin_path(self.get_option("vagrant_exe"))
            except ValueError as e:
                raise AnsibleError(to_native(e))
        self.vagrantfile = self.get_option("vagrantfile")
        if not os.path.isfile(self.vagrantfile):
            raise AnsibleError("%s is not a file" % self.vagrantfile)

        ssh_config_dir = os.path.join(get_cachedir(), "ansible-vagrant-ssh")
        ssh_config_file = os.path.join(ssh_config_dir, self.host)
        if not os.path.isfile(ssh_config_file):
            display.vvv("THIS IS A VAGRANT INSTANCE", host=self.host)
            vagrantdir = os.path.dirname(self.vagrantfile)
            os.makedirs(ssh_config_dir, exist_ok=True)

            try:
                ssh_config = subprocess.run(
                    [self.vagrant_cmd, "ssh-config", self.host],
                    cwd=vagrantdir,
                    text=True,
                    check=True,
                    capture_output=True,
                )
            except Exception as e:
                raise AnsibleError(
                    f"SSH configuration for {self.host} defined in {self.vagrantfile}"
                    f"could not be created:\n{e.stderr}"
                )

            with open(ssh_config_file, "w") as f:
                f.write(ssh_config.stdout)
        self.ssh_config_file = ssh_config_file

        if not self._connected:
            super(Connection, self)._connect()
            self._connected = True

    def _build_command(self, binary, *other_args):
        res = super()._build_command(binary, *other_args)
        res.insert(1, b"-F")
        res.insert(2, self.ssh_config_file.encode("utf-8"))
        return res
