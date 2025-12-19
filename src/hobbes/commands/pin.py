"""Pin/unpin command implementations."""

import click
from rich.console import Console

from hobbes.core.manifest import Manifest

console = Console()


@click.command()
@click.argument("package_name")
def pin(package_name: str):
    """Pin a package to its current version.

    Pinned packages are skipped during 'upgrade-all'.
    """
    manifest = Manifest()

    if not manifest.has(package_name):
        console.print(f"[red]Error:[/red] Package '{package_name}' is not installed")
        raise SystemExit(1)

    package = manifest.get(package_name)
    if package.pinned:
        console.print(f"[yellow]{package_name}[/yellow] is already pinned to {package.version}")
        raise SystemExit(0)

    manifest.pin(package_name)
    console.print(f"[green]✓[/green] Pinned [bold]{package_name}[/bold] to version {package.version}")


@click.command()
@click.argument("package_name")
def unpin(package_name: str):
    """Unpin a package, allowing it to be upgraded."""
    manifest = Manifest()

    if not manifest.has(package_name):
        console.print(f"[red]Error:[/red] Package '{package_name}' is not installed")
        raise SystemExit(1)

    package = manifest.get(package_name)
    if not package.pinned:
        console.print(f"[yellow]{package_name}[/yellow] is not pinned")
        raise SystemExit(0)

    manifest.unpin(package_name)
    console.print(f"[green]✓[/green] Unpinned [bold]{package_name}[/bold]")
