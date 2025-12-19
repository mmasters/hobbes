"""Update command implementation."""

from datetime import datetime

import click
from rich.console import Console

from hobbes.core.config import get_config
from hobbes.core.github import GitHubClient, GitHubError
from hobbes.core.platform import find_best_asset, get_platform_info
from hobbes.core.downloader import download_file, DownloadError
from hobbes.core.extractor import (
    extract_archive,
    install_binaries,
    uninstall_binaries,
    cleanup_temp_dir,
    ExtractionError,
)
from hobbes.core.checksum import verify_checksum, ChecksumError
from hobbes.core.manifest import Manifest
from hobbes.models.package import Package

console = Console()


def update_package(package: Package, manifest: Manifest, force: bool = False) -> bool:
    """Update a single package. Returns True if updated."""
    if package.pinned and not force:
        console.print(f"  [yellow]{package.name}[/yellow] is pinned, skipping")
        return False

    owner, repo = package.repo.split("/")

    with GitHubClient() as client:
        try:
            release = client.get_latest_release(owner, repo)
        except GitHubError as e:
            console.print(f"  [red]Error fetching {package.name}:[/red] {e}")
            return False

        if release.version == package.version and not force:
            console.print(f"  [green]{package.name}[/green] is up to date ({package.version})")
            return False

        console.print(
            f"  [blue]Updating[/blue] {package.name}: {package.version} → {release.version}"
        )

        platform_info = get_platform_info()
        asset = find_best_asset(release.assets, platform_info)
        if asset is None:
            console.print(f"    [red]No compatible binary found[/red]")
            return False

        # Download
        try:
            archive_path = download_file(asset.download_url, filename=asset.name)
        except DownloadError as e:
            console.print(f"    [red]Download failed:[/red] {e}")
            return False

        # Verify checksum
        try:
            verify_checksum(archive_path, release.assets, asset)
        except ChecksumError as e:
            console.print(f"    [red]Checksum failed:[/red] {e}")
            archive_path.unlink(missing_ok=True)
            return False

        # Remove old binaries
        uninstall_binaries(package.binaries)

        # Extract and install new
        temp_dir = None
        try:
            temp_dir = extract_archive(archive_path)
            binaries = install_binaries(temp_dir)

            if not binaries:
                console.print("    [red]No binaries found[/red]")
                return False

        except ExtractionError as e:
            console.print(f"    [red]Extraction failed:[/red] {e}")
            return False
        finally:
            if temp_dir:
                cleanup_temp_dir(temp_dir)
            archive_path.unlink(missing_ok=True)

        # Update manifest
        updated_package = Package(
            name=package.name,
            repo=package.repo,
            version=release.version,
            tag=release.tag_name,
            installed_at=datetime.now(),
            binaries=binaries,
            pinned=package.pinned,
            asset=asset.name,
        )
        manifest.add(updated_package)

        console.print(f"    [green]✓[/green] Updated to {release.version}")
        return True


@click.command()
@click.argument("package_name")
@click.option("--force", "-f", is_flag=True, help="Force update even if pinned")
def update(package_name: str, force: bool):
    """Update a package to the latest version.

    PACKAGE_NAME is the name of the installed package (repo name).
    """
    config = get_config()
    config.ensure_dirs()

    manifest = Manifest()

    package = manifest.get(package_name)
    if package is None:
        console.print(f"[red]Error:[/red] Package '{package_name}' is not installed")
        raise SystemExit(1)

    updated = update_package(package, manifest, force)
    if not updated:
        raise SystemExit(0)

    console.print(f"\n[green]✓[/green] Successfully updated [bold]{package_name}[/bold]")


@click.command("upgrade-all")
@click.option("--force", "-f", is_flag=True, help="Force update even if pinned")
def upgrade_all(force: bool):
    """Update all installed packages to their latest versions."""
    config = get_config()
    config.ensure_dirs()

    manifest = Manifest()
    packages = manifest.list_packages()

    if not packages:
        console.print("No packages installed")
        raise SystemExit(0)

    console.print(f"[blue]Checking {len(packages)} packages for updates...[/blue]\n")

    updated_count = 0
    for package in packages:
        if update_package(package, manifest, force):
            updated_count += 1

    console.print(f"\n[green]✓[/green] Updated {updated_count} package(s)")
