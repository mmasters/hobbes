"""Uninstall command implementation."""

import click
from rich.console import Console

from hobbes.core.manifest import Manifest
from hobbes.core.extractor import uninstall_binaries

console = Console()


@click.command()
@click.argument("package_name")
def uninstall(package_name: str):
    """Uninstall a package.

    PACKAGE_NAME is the name of the installed package (repo name).
    """
    manifest = Manifest()

    package = manifest.get(package_name)
    if package is None:
        console.print(f"[red]Error:[/red] Package '{package_name}' is not installed")
        raise SystemExit(1)

    console.print(f"[blue]Uninstalling[/blue] {package_name}...")

    # Remove binaries
    uninstall_binaries(package.binaries)
    console.print(f"  Removed binaries: {', '.join(package.binaries)}")

    # Remove from manifest
    manifest.remove(package_name)

    console.print(f"\n[green]✓[/green] Successfully uninstalled [bold]{package_name}[/bold]")
