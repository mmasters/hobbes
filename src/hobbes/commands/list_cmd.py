"""List command implementation."""

import click
from rich.console import Console
from rich.table import Table

from hobbes.core.manifest import Manifest

console = Console()


@click.command("list")
def list_packages():
    """List all installed packages."""
    manifest = Manifest()
    packages = manifest.list_packages()

    if not packages:
        console.print("No packages installed")
        console.print("\nInstall packages with: hobbes install <owner/repo>")
        raise SystemExit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Package")
    table.add_column("Version")
    table.add_column("Repo")
    table.add_column("Asset")
    table.add_column("Binaries")
    table.add_column("Pinned")

    for pkg in sorted(packages, key=lambda p: p.name):
        pinned = "📌" if pkg.pinned else ""
        table.add_row(
            pkg.name,
            pkg.version,
            pkg.repo,
            pkg.asset or "(source)",
            ", ".join(pkg.binaries),
            pinned,
        )

    console.print(table)
