#!/usr/bin/env python3

# This script configures ssh for new hosts
# Author:  Valentin Kolb
# Version: 1.1
# License: MIT
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import re
import argparse
from prompt_toolkit import PromptSession, HTML, print_formatted_text
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
import subprocess

#########################
# DEFAULT CONFIGURATION #
#########################

DEFAULT_USER = "admin"
DEFAULT_PORT = 22
CONFIG_FILE = str(Path.home()) + "/.ssh/config"
SSH_KEY_DIR = str(Path.home()) + "/.ssh/keys"


#########################
# END DEFAULTS          #
#########################


def bottom_toolbar():
    return HTML('SSH Wizard - type <b>help</b> to list all commands')


def stderr(text, end="\n"):
    """
    prints error msg
    """
    print_formatted_text(text, file=sys.stderr, end=end)


session = PromptSession(
    bottom_toolbar=bottom_toolbar,
    complete_while_typing=True
)

style = Style.from_dict({
    'cmd': '#ff0066',
    'hlp': '#44ff00 italic',
})

REVERSED = u"\u001b[7m"
RESET = u"\u001b[0m"
FNULL = open(os.devnull, 'w')

SSH_KEY_FILE_REGEX = r"Host +(?P<ID>.+)\n\tHostname +(?P<hostname>\S+)\n\tUser +(?P<user>\S+)\n\tPort +(?P<port>\d+)\n\tIdentityFile +(?P<key_file>\S+)\n?"


@dataclass(frozen=True)
class SSHConfig:
    ID: str
    hostname: str
    user: str
    port: int
    key_file: str


def file_to_dataclass(file: str) -> List[SSHConfig]:
    """
    reads a ssh config file an parses it to an list of dataclasses
    :param file: the ssh config file
    :return: an array of dataclasses
    """
    with open(file) as file:
        content = file.read()
    results = []
    for match in re.finditer(pattern=SSH_KEY_FILE_REGEX, string=content):
        results.append(
            SSHConfig(
                ID=match.group("ID"),
                hostname=match.group("hostname"),
                user=match.group("user"),
                port=int(match.group("port")),
                key_file=match.group("key_file")
            )
        )
    return results


def dataclass_to_file(file: str, data: List[SSHConfig]):
    """
    writes the ssh config file
    :param file: the path of the file
    :param data: the data to be written
    """
    with open(file, mode="w") as file:
        for config in data:
            file.write(
                f'Host {config.ID}\n' +
                f'\tHostname {config.hostname}\n' +
                f'\tUser {config.user}\n' +
                f'\tPort {config.port}\n' +
                f'\tIdentityFile {config.key_file}\n\n'
            )


def yes(prompt="[Y/n]"):
    """
    asks user yes or no question, yes is default
    :param prompt: the prompt for the user
    :return: true if answer was yes
    """
    while True:
        _in = session.prompt(prompt).strip().lower()
        if _in in ["y", "yes", ""]:
            return True
        elif _in in ["n", "no"]:
            return False


def list_config():
    """
    this will print all currently configured hosts
    """
    hosts = file_to_dataclass(CONFIG_FILE)
    i = max(len(h.ID) for h in hosts)
    j = max(len(h.hostname) + 1 + len(h.user) for h in hosts)
    print(f'{"identifier".upper().ljust(i)} | HOST')
    print("=" * (i + j + 3))
    for host in hosts:
        print(f'{host.ID.ljust(i, ".")} | {(host.user + "@" + host.hostname).ljust(j, ".")}')

    print(f"\nUsage: 'ssh <identifier>' (eg: ssh {hosts[0].ID})")


def add_host():
    # domain name
    hostname = session.prompt("Enter the domain name. (e.g. host.example.com): ").strip().lower()
    ID, _ = hostname.split(".", 1)
    ID = session.prompt(
        f"Enter an alias of the host (usage: ssh <alias>) [{ID}]: ") or ID

    # check if host is up
    if not subprocess.run(["ping", "-c", "1", "-i", "0.5", hostname],
                          stdout=FNULL,
                          stderr=subprocess.STDOUT).returncode == 0:
        stderr(f"{hostname} can't be reached, do want to continue anyway? [Y/n] ", end="")
        if not yes(prompt=""):
            stderr("... aborting")
            return

    # user name
    user = session.prompt(f"please enter the user [{DEFAULT_USER}]: ").strip() or DEFAULT_USER

    # port
    port = int(session.prompt(f"please enter the port [{DEFAULT_PORT}]: ").strip() or 22)

    # check for existing configuration
    hosts = file_to_dataclass(CONFIG_FILE)
    if any(hostname == h.hostname for h in hosts):
        stderr(f"There is already a configuration for the host {hostname}, do you want to overwrite it? [Y/n] ", end="")
        if not yes(prompt=""):
            stderr("... aborting")
            return
        else:
            hosts = [h for h in hosts if h.hostname != hostname]

    # generate public and private key
    print("generating keys ...")
    subprocess.run(["mkdir", "-p", SSH_KEY_DIR])
    key_file = f'{SSH_KEY_DIR}/{hostname.replace(".", "_")}'
    if os.path.exists(key_file):
        os.remove(key_file)
        os.remove(f'{key_file}.pub')
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-C", f"'key for {hostname}'", "-f", key_file, "-q"])

    new_config_data = SSHConfig(
        ID=ID,
        hostname=hostname,
        user=user,
        port=port,
        key_file=key_file
    )

    with open(f'{key_file}.pub') as file:
        public_key = file.read().strip()

    dataclass_to_file(CONFIG_FILE, hosts + [new_config_data])

    print("... wizard done.")
    print()
    print(f'PUBLIC KEY: {REVERSED}{public_key}{RESET}')
    print()
    print("To connect to the VM follow these steps:")
    print(f"\t1. copy the public key to the cloud-init drive of the VM. "
          f"\n\t   this can be done in proxmox")
    print(f"\t2. run {REVERSED}ssh {ID}{RESET} to connect to the VM")


def configure(cmd: List[str]):
    """
    change the default values of this script
    """
    if cmd[0] == "show":
        print("Configured values for this script:")
        print(f"  DEFAULT-USER : {DEFAULT_USER}")
        print(f"  DEFAULT-PORT : {DEFAULT_PORT}")
        print(f"  CONFIG-FILE  : {CONFIG_FILE}")
        print(f"  SSH-KEY-DIR  : {SSH_KEY_DIR}")
    elif cmd[0] == "set" and len(cmd) == 3:
        if cmd[1] == "DEFAULT-USER":
            ...
        elif cmd[1] == "DEFAULT-PORT":
            ...
        elif cmd[1] == "CONFIG-FILE":
            ...
        elif cmd[1] == "SSH-KEY-DIR":
            ...

    else:
        stderr(f"Invalid cmd for 'configure: {' '.join(cmd)}")


if __name__ == '__main__':

    while True:
        hosts = file_to_dataclass(CONFIG_FILE)

        completer = NestedCompleter.from_nested_dict({
            'ssh ': {host.ID for host in hosts},
            'remove ': {host.ID for host in hosts},
            'add': None,
            'list': None,
            'help': None,
            'exit': None,
            'clear': None,
            'configure': {
                "show", "set"
            }
        })

        try:
            text: str = session.prompt(message=">>> ",
                                       completer=completer)
        except KeyboardInterrupt:
            stderr(HTML("Enter <b>exit</b> to exit the shell or press <b>CTRL-D</b>."))
            continue
        except EOFError:
            stderr("... exiting")
            exit(-1)

        if text.startswith("ssh"):
            cmd = text.split(" ")
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    stderr(result.stderr)
            except KeyboardInterrupt:
                stderr(" Keyboard Interrupt!")

        elif text.startswith("remove"):
            ...
        elif text.startswith("add"):
            ...
        elif text.startswith("list"):
            list_config()
        elif text.startswith("help"):
            help_text = {
                'ssh <alias>': "Connect to a ssh host by it's alias.",
                'remove <alias>': "Remove an ssh host from the config.",
                'add': "Run wizard to add a new ssh host.",
                'list': "List all ssh hosts.",
                'help': "Print this help.",
                'exit': "Exit the shell.",
                'clear': "Clears the screen.",
                'configure [show | set ..]': "Show and change the default values of the wizard."
            }
            width = max(len(s) for s in help_text)
            for cmd in help_text:
                print(f'{cmd.ljust(width)} : {help_text[cmd]}')
        elif text.startswith("exit"):
            break
        elif text.startswith("configure"):
            _, *cmd = text.split(" ")
            configure(cmd)
        elif text.startswith("clear"):
            clear()
        else:
            print_formatted_text(HTML(f"Unknown Command: {text}\nEnter <b>help</b> for a list of all commands."))
