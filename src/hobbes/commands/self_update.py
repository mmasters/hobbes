"""Self-update command implementation."""

import subprocess
import sys

import click
from rich.console import Console

from hobbes import __version__
from hobbes.core.github import GitHubClient, GitHubError

console = Console()

HOBBES_REPO = "mmasters/hobbes"


@click.command("self-update")
@click.option("--force", "-f", is_flag=True, help="Force update even if up to date")
def self_update(force: bool):
    """Update hobbes itself to the latest version."""
    console.print(f"[blue]Current version:[/blue] {__version__}")

    # Check for latest version
    latest_version = None
    with GitHubClient() as client:
        try:
            release = client.get_latest_release(*HOBBES_REPO.split("/"))
            latest_version = release.version
            console.print(f"[blue]Latest version:[/blue]  {latest_version}")
        except GitHubError:
            # No releases yet, will update from main branch
            console.print("[dim]No releases found, updating from main branch[/dim]")

    if latest_version and latest_version == __version__ and not force:
        console.print("\n[green]Already up to date![/green]")
        raise SystemExit(0)

    console.print(f"\n[blue]Updating hobbes...[/blue]")

    # Determine how to update based on how hobbes was installed
    # Try pip upgrade from git
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"git+https://github.com/{HOBBES_REPO}.git",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            if latest_version:
                console.print(f"\n[green]✓[/green] Updated to version {latest_version}")
            else:
                console.print("\n[green]✓[/green] Updated to latest")
            console.print("[dim]Restart hobbes to use the new version[/dim]")
        else:
            console.print(f"[red]Error updating:[/red] {result.stderr}")
            raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\nTry updating manually:")
        console.print(f"  pip install --upgrade git+https://github.com/{HOBBES_REPO}.git")
        raise SystemExit(1)
