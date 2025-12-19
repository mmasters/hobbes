"""CLI entry point for hobbes."""

import click
from rich.console import Console

from hobbes import __version__
from hobbes.commands import install, uninstall, update, list_cmd, search, info, outdated, pin

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="hobbes")
def main():
    """Hobbes - A package manager for GitHub release binaries.

    Install binaries from GitHub releases and manage them locally.

    Examples:

        hobbes install junegunn/fzf

        hobbes install BurntSushi/ripgrep --version 14.0.0

        hobbes list

        hobbes update fzf
    """
    pass


# Register commands
main.add_command(install.install)
main.add_command(uninstall.uninstall)
main.add_command(update.update)
main.add_command(update.upgrade_all)
main.add_command(list_cmd.list_packages)
main.add_command(search.search)
main.add_command(info.info)
main.add_command(outdated.outdated)
main.add_command(pin.pin)
main.add_command(pin.unpin)


if __name__ == "__main__":
    main()
