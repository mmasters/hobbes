"""Outdated command implementation."""

import click
from rich.console import Console
from rich.table import Table

from hobbes.core.manifest import Manifest
from hobbes.core.github import GitHubClient, GitHubError

console = Console()


@click.command()
def outdated():
    """List packages with available updates."""
    manifest = Manifest()
    packages = manifest.list_packages()

    if not packages:
        console.print("No packages installed")
        raise SystemExit(0)

    console.print("[blue]Checking for updates...[/blue]\n")

    outdated_packages = []

    with GitHubClient() as client:
        for package in packages:
            owner, repo = package.repo.split("/")
            try:
                release = client.get_latest_release(owner, repo)
                if release.version != package.version:
                    outdated_packages.append({
                        "name": package.name,
                        "current": package.version,
                        "latest": release.version,
                        "pinned": package.pinned,
                    })
            except GitHubError:
                # Skip packages we can't check
                pass

    if not outdated_packages:
        console.print("[green]All packages are up to date![/green]")
        raise SystemExit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Package")
    table.add_column("Current")
    table.add_column("Latest")
    table.add_column("Status")

    for pkg in outdated_packages:
        status = "📌 pinned" if pkg["pinned"] else ""
        table.add_row(
            pkg["name"],
            pkg["current"],
            f"[green]{pkg['latest']}[/green]",
            status,
        )

    console.print(table)
    console.print(f"\n{len(outdated_packages)} package(s) can be updated")
    console.print("[dim]Run 'hobbes upgrade-all' to update all packages[/dim]")
