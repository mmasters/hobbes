"""Info command implementation."""

import click
from rich.console import Console
from rich.panel import Panel

from hobbes.core.manifest import Manifest
from hobbes.core.github import GitHubClient, GitHubError, parse_repo_spec

console = Console()


@click.command()
@click.argument("package_name")
def info(package_name: str):
    """Show detailed information about a package.

    PACKAGE_NAME can be:
      - Name of an installed package
      - owner/repo format for any GitHub repo
    """
    manifest = Manifest()
    package = manifest.get(package_name)

    if package:
        # Show installed package info
        lines = [
            f"[bold]Name:[/bold] {package.name}",
            f"[bold]Repository:[/bold] {package.repo}",
            f"[bold]Version:[/bold] {package.version}",
            f"[bold]Tag:[/bold] {package.tag}",
            f"[bold]Installed:[/bold] {package.installed_at.strftime('%Y-%m-%d %H:%M')}",
            f"[bold]Binaries:[/bold] {', '.join(package.binaries)}",
            f"[bold]Asset:[/bold] {package.asset}",
            f"[bold]Pinned:[/bold] {'Yes' if package.pinned else 'No'}",
        ]
        console.print(Panel("\n".join(lines), title=f"[green]{package.name}[/green] (installed)"))

        # Also show available versions
        owner, repo = package.repo.split("/")
    else:
        # Try to parse as repo spec
        try:
            owner, repo = parse_repo_spec(package_name)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

    # Fetch release info from GitHub
    with GitHubClient() as client:
        try:
            releases = client.get_releases(owner, repo, per_page=5)
        except GitHubError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        if releases:
            console.print("\n[bold]Recent releases:[/bold]")
            for release in releases[:5]:
                marker = ""
                if package and release.tag_name == package.tag:
                    marker = " [green](installed)[/green]"
                prerelease = " [yellow](prerelease)[/yellow]" if release.prerelease else ""
                console.print(f"  • {release.tag_name}{prerelease}{marker}")
