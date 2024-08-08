import glob
import os
import platform
from pathlib import Path
from typing import Any, Union
from textwrap import dedent as d, indent


class Strable:
    def __repr__(self) -> str:
        d = ", ".join(f"{k}: {v}" for k, v in self.__dict__.items() if v and v != self)
        return f"<{self.__class__.__name__} {d}>"

    def __str__(self) -> str:
        d = "\n".join(f"{k}: {v}" for k, v in self.__dict__.items() if v and v != self)
        return f"Type: {self.__class__.__name__}\n{d}>"


class Optioneer:
    unprocessed_options: dict[str, str]

    def to_options(self) -> dict[str, str]:
        opts: dict[str, str] = {}
        for k in self.__init__.__annotations__:  # type: ignore
            if k == "unprocessed_options":
                continue
            v = getattr(self, k)
            if not v:
                continue
            opts[k] = v
        for k, v in self.unprocessed_options.items():
            if not v:
                continue
            assert k not in opts
            opts[k] = v
        return opts

    @classmethod
    def from_options(klass, opts: dict[str, str]):
        processed_options: dict[str, Any] = {}
        for k in klass.__init__.__annotations__:
            if k in opts:
                processed_options[k] = opts[k]
                del opts[k]
            elif k != "unprocessed_options":
                processed_options[k] = None
        return klass(unprocessed_options=opts, **processed_options)  # type: ignore


class VagrantConnection(Optioneer, Strable):
    ansible_vagrantfile: Path | None
    ansible_remote_user: str | None
    unprocessed_options: dict[str, str]

    def __init__(
        self,
        ansible_vagrantfile: Path | None,
        ansible_remote_user: str | None,
        unprocessed_options: dict[str, str],
    ):
        for k, v in locals().items():
            setattr(self, k, v)

    @classmethod
    def default(klass) -> "VagrantConnection":
        pwd = os.getcwd()
        os.chdir(os.path.dirname(__file__))
        df = Path(glob.glob("*/Vagrantfile")[0])
        os.chdir(pwd)
        return klass(
            ansible_vagrantfile=df,
            ansible_remote_user="vagrant",
            unprocessed_options={},
        )

    def __str__(self) -> str:
        return d(
            f"""
            Vagrantfile: {self.ansible_vagrantfile}
            User on Vagrant VM: {self.ansible_remote_user}
            """  # noqa: E501
        ).rstrip()


class SSHConnection(Optioneer, Strable):
    ansible_host: str | None
    ansible_port: str | None
    ansible_remote_user: str | None
    ansible_ssh_private_key_file: Path | None
    unprocessed_options: dict[str, str]

    def __init__(
        self,
        ansible_host: str | None,
        ansible_port: str | None,
        ansible_remote_user: str | None,
        ansible_ssh_private_key_file: Path | None,
        unprocessed_options: dict[str, str],
    ):
        for k, v in locals().items():
            setattr(self, k, v)

    @classmethod
    def default(klass) -> "SSHConnection":
        return klass(
            ansible_host=None,
            ansible_port=None,
            ansible_remote_user=None,
            ansible_ssh_private_key_file=None,
            unprocessed_options={},
        )

    def __str__(self) -> str:
        return d(
            f"""
            Host: {self.ansible_host or '(use the host name)'}
            Port: {self.ansible_port or '(use the default SSH port)'}
            Remote user: {self.ansible_remote_user or '(use the default SSH remote user)'}
            SSH key file: {self.ansible_ssh_private_key_file or '(use any keys available to SSH)'}
            """  # noqa: E501
        ).rstrip()


class HostConfiguration(Strable):
    name: str
    kind: VagrantConnection | SSHConnection

    def __init__(self, name: str, kind: VagrantConnection | SSHConnection):
        self.name = name
        self.kind = kind

    def __str__(self) -> str:
        kind = indent(str(self.kind), "  ")
        return (
            (
                d(
                    f"""
            Name: {self.name}
            Type: {'local VirtualBox' if isinstance(self.kind, VagrantConnection) else 'remote SSH'}
            Parameters:
            """  # noqa: E501
                )
            ).rstrip()
            + kind
        )

    @classmethod
    def from_line(klass, line: str):

        def opts_str_to_opts(line: str) -> dict[str, str]:
            opts = {}
            for i in line.split():
                k, _, v = i.partition("=")
                opts[k] = v
            return opts

        name, _, opts_str = line.partition(" ")
        opts = opts_str_to_opts(opts_str)
        if opts.get("ansible_connection") == "vagrant":
            kind = VagrantConnection.from_options(opts)
            del opts["ansible_connection"]
        elif opts.get("ansible_connection") in ("ssh", None):
            kind = SSHConnection.from_options(opts)
            del opts["ansible_connection"]
        else:
            assert 0, "not reached"
        return klass(name, kind)

    def to_line(self) -> str:
        def opts_to_opts_str(opts: dict[str, str]) -> str:
            return " ".join(f"{k}={v}" for k, v in opts.items())

        opts = opts_to_opts_str(self.kind.to_options())
        if isinstance(self.kind, VagrantConnection):
            opts = "ansible_connection=vagrant " + opts
        return " ".join([self.name] + [opts] if opts else [])

    @classmethod
    def from_hosts(klass, name: str, hosts: str) -> Union["HostConfiguration", None]:
        for line in hosts.splitlines():
            if not line.strip():
                continue
            if line.split()[0] == name:
                return klass.from_line(line)
        return None

    def into_hosts(self, existing_hosts: str) -> str:
        hosts_lines = existing_hosts.splitlines(True)
        edited = False
        for n, line in enumerate(hosts_lines):
            if not line.strip():
                continue
            if line.split()[0] == self.name:
                hosts_lines[n] = self.to_line() + "\n"
                edited = True
                break
        if not edited:
            hosts_lines = [self.to_line() + "\n"] + hosts_lines
        return "".join(hosts_lines)


def prompt(prompt_text: str, choices: list[str]):
    while True:
        choice = input(prompt_text)
        if choice not in choices:
            print(f"{choice}: not a valid choice.  Please try again.")
            continue
        break
    return choice


def generic_input_string(prompt, callable):
    while True:
        c = input(prompt + " (or leave empty to make no changes): ")
        if not c:
            return
        try:
            callable(c)
        except Exception as e:
            print("Not a valid value: " + str(e))
            continue
        break


def main():
    hosts_path = os.path.join(os.path.dirname(__file__), "hosts")
    try:
        with open(hosts_path, "r") as f:
            hosts = f.read()
    except FileNotFoundError:
        hosts = ""

    cfg = HostConfiguration.from_hosts("observability", hosts)

    def vagrant_mac_warning() -> None:
        if isinstance(cfg.kind, VagrantConnection) and (
            "arm" in platform.processor()
            and sys.platform == "darwin"
        ):
            print("Warning: VirtualBox will not run reliably on Apple Silicon at this time.")
            print("Get more information on this particular in the README.md documentation file.")

    def change_target_type(must_choose: bool = False):
        nonlocal cfg
        if not must_choose:
            extra = """
                q) Return without making changes
            """.rstrip()
        else:
            extra = ""
        choice = prompt(
            d(
                f"""
                Where do you want to run your IC observability stack?

                a) Locally using a VirtualBox virtual machine
                b) In a remote host accessible through SSH{extra}
            
                Your choice (default: a): """  # noqa: E501
            ),
            ["a", "b", ""] + (["q"] if not must_choose else []),
        )
        if choice in ["a", ""]:
            cfg = HostConfiguration("observability", VagrantConnection.default())
        elif choice == "b":
            cfg = HostConfiguration("observability", SSHConnection.default())
        elif choice == "q" and not must_choose:
            return

    def change_target_vagrant_parameters():
        nonlocal cfg
        while True:
            print(f"\nCurrent VirtualBox parameters:{indent(str(cfg.kind), '  ')}")
            choice = prompt(
                d(
                    """
                    How do you want to alter the VirtualBox parameters?

                    a) Change the Vagrantfile used to set up the VM
                    b) Change the user to log in as into the VM
                
                    Your choice (default: q): """  # noqa: E501
                ),
                ["a", "b", "q", ""],
            )
            if choice == "a":

                def chg(v):
                    nonlocal cfg
                    cfg.kind.ansible_vagrantfile = v

                generic_input_string("Enter the path to the Vagrantfile to use", chg)
            elif choice == "b":

                def chg(v):
                    nonlocal cfg
                    cfg.kind.ansible_remote_user = v

                generic_input_string("Enter the user to log into the VM as", chg)
            elif choice in ["q", ""]:
                return

    def change_target_ssh_parameters():
        nonlocal cfg
        while True:
            print(f"\nCurrent SSH parameters:{indent(str(cfg.kind), '  ')}")
            choice = prompt(
                d(
                    f"""
                    How do you want to alter the SSH parameters?

                    a) Override the host name or IP address
                    b) Use the default host name ({cfg.name})
                    c) Override the port
                    d) Use the default port
                    e) Use a specific SSH private key file
                    f) Let the provisioning system use any available key material to log in
                    g) Change the user to log in as
                    h) Use the default remote user to log in
                
                    Your choice (default: q): """  # noqa: E501
                ),
                ["a", "b", "c", "d", "e", "f", "g", "h", "q", ""],
            )
            if choice == "a":

                def chg(v):
                    nonlocal cfg
                    cfg.kind.ansible_host = v

                generic_input_string("Enter the target SSH host", chg)
            elif choice == "b":
                cfg.kind.ansible_host = None
            if choice == "c":

                def chg(v):
                    nonlocal cfg
                    if int(v) < 1:
                        raise ValueError("port has to be a positive number")
                    cfg.kind.ansible_port = v

                generic_input_string("Enter the target SSH port", chg)
            elif choice == "d":
                cfg.kind.ansible_port = None
            if choice == "e":

                def chg(v):
                    nonlocal cfg
                    if not os.path.isfile(v):
                        raise FileNotFoundError(f"{v} does not exist or is not a file")
                    cfg.kind.ansible_ssh_private_key_file = v

                generic_input_string("Enter the private key file you want to use", chg)
            elif choice == "f":
                cfg.kind.ansible_ssh_private_key_file = None
            if choice == "g":

                def chg(v):
                    nonlocal cfg
                    cfg.kind.ansible_remote_user = v

                generic_input_string("Enter the remote user to connect as", chg)
            elif choice == "h":
                cfg.kind.ansible_remote_user = None
            elif choice in ["q", ""]:
                return

    if not cfg:
        print("No current configuration detected.  Starting a new configuration.")
        change_target_type(must_choose=True)
        if isinstance(cfg.kind, VagrantConnection):
            print(
                "\nSane defaults have been chosen for you.  The IC observability"
                " stack should come up without issue after you save the configuration."
            )
        elif isinstance(cfg.kind, SSHConnection):
            print(
                "\nYou will have to change the target settings to specify, "
                "at the very least, the host name or IP address of the target machine."
            )
            change_target_ssh_parameters()

    while True:
        print(f"\nCurrent configuration:{indent(str(cfg), '  ')}")
        choice = prompt(
            d(
                """
                t) Change target type
                p) Change target settings
                s) Save settings to disk and exit
                q) Quit without saving changes
            
                Your choice: """  # noqa: E501
            ),
            ["s", "q", "t", "p"],
        )
        if choice == "t":
            change_target_type()
        if choice == "p":
            if isinstance(cfg.kind, VagrantConnection):
                change_target_vagrant_parameters()
            elif isinstance(cfg.kind, SSHConnection):
                change_target_ssh_parameters()
            else:
                assert 0, "not reached"
        if choice == "s":
            new_hosts = cfg.into_hosts(hosts)
            with open(hosts_path, "w") as f:
                hosts = f.write(new_hosts)
            vagrant_mac_warning()
            break
        elif choice == "q":
            vagrant_mac_warning()
            break


if __name__ == "__main__":
    main()
