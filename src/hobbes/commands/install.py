"""Install command implementation."""

from datetime import datetime

import click
from rich.console import Console

from hobbes.core.config import get_config
from hobbes.core.github import GitHubClient, GitHubError, parse_repo_spec
from hobbes.core.platform import find_best_asset, get_platform_info
from hobbes.core.downloader import download_file, DownloadError
from hobbes.core.extractor import (
    extract_archive,
    install_binaries,
    cleanup_temp_dir,
    ExtractionError,
)
from hobbes.core.checksum import verify_checksum, ChecksumError
from hobbes.core.manifest import Manifest
from hobbes.models.package import Package

console = Console()


@click.command()
@click.argument("repo_spec")
@click.option("--version", "-v", "version_tag", help="Specific version/tag to install")
@click.option("--force", "-f", is_flag=True, help="Force reinstall if already installed")
def install(repo_spec: str, version_tag: str | None, force: bool):
    """Install a package from GitHub releases.

    REPO_SPEC can be:
      - owner/repo format (e.g., junegunn/fzf)
      - Full GitHub URL (e.g., https://github.com/junegunn/fzf)
    """
    config = get_config()
    config.ensure_dirs()

    # Parse repo spec
    try:
        owner, repo = parse_repo_spec(repo_spec)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    manifest = Manifest()

    # Check if already installed
    if manifest.has(repo) and not force:
        pkg = manifest.get(repo)
        console.print(
            f"[yellow]{repo}[/yellow] is already installed (version {pkg.version}). "
            f"Use --force to reinstall."
        )
        raise SystemExit(0)

    console.print(f"[blue]Installing[/blue] {owner}/{repo}...")

    with GitHubClient() as client:
        # Get release
        try:
            if version_tag:
                release = client.get_release_by_tag(owner, repo, version_tag)
            else:
                release = client.get_latest_release(owner, repo)
        except GitHubError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        console.print(f"  Found release: [green]{release.tag_name}[/green]")

        # Find best matching asset
        platform_info = get_platform_info()
        console.print(f"  Platform: {platform_info.os}/{platform_info.arch}")

        asset = find_best_asset(release.assets, platform_info)
        if asset is None:
            console.print(
                f"[red]Error:[/red] No compatible binary found for {platform_info.os}/{platform_info.arch}"
            )
            console.print("Available assets:")
            for a in release.assets:
                console.print(f"  - {a.name}")
            raise SystemExit(1)

        console.print(f"  Selected asset: [cyan]{asset.name}[/cyan]")

        # Download
        try:
            archive_path = download_file(asset.download_url, filename=asset.name)
        except DownloadError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        # Verify checksum
        try:
            verify_checksum(archive_path, release.assets, asset)
            console.print("  [green]✓[/green] Checksum verified")
        except ChecksumError as e:
            console.print(f"[red]Error:[/red] {e}")
            archive_path.unlink(missing_ok=True)
            raise SystemExit(1)

        # Extract and install
        temp_dir = None
        try:
            temp_dir = extract_archive(archive_path)
            binaries = install_binaries(temp_dir)

            if not binaries:
                console.print("[red]Error:[/red] No executable binaries found in archive")
                raise SystemExit(1)

            console.print(f"  Installed binaries: {', '.join(binaries)}")

        except ExtractionError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        finally:
            if temp_dir:
                cleanup_temp_dir(temp_dir)
            archive_path.unlink(missing_ok=True)

        # Update manifest
        package = Package(
            name=repo,
            repo=f"{owner}/{repo}",
            version=release.version,
            tag=release.tag_name,
            installed_at=datetime.now(),
            binaries=binaries,
            asset=asset.name,
        )
        manifest.add(package)

        console.print(
            f"\n[green]✓[/green] Successfully installed [bold]{repo}[/bold] {release.version}"
        )
        console.print(
            f"\n[dim]Make sure {config.bin_dir} is in your PATH[/dim]"
        )
