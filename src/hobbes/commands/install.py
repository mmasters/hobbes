"""Install command implementation."""

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm

from hobbes.core.config import get_config
from hobbes.core.github import GitHubClient, GitHubError, parse_repo_spec
from hobbes.core.platform import find_best_asset, find_best_assets, get_platform_info
from hobbes.core.downloader import download_file, DownloadError
from hobbes.core.extractor import (
    extract_archive,
    install_binaries,
    find_scripts,
    make_executable,
    cleanup_temp_dir,
    ExtractionError,
)
from hobbes.core.checksum import verify_checksum, ChecksumError
from hobbes.core.manifest import Manifest
from hobbes.models.package import Package
from hobbes.models.release import Release, Asset

console = Console()


def install_from_binary(
    release: Release,
    asset: Asset,
    owner: str,
    repo: str,
    manifest: Manifest,
    config,
) -> bool:
    """Install from a binary asset. Returns True on success."""
    console.print(f"  Selected asset: [cyan]{asset.name}[/cyan]")

    # Download
    try:
        archive_path = download_file(asset.download_url, filename=asset.name)
    except DownloadError as e:
        console.print(f"[red]Error:[/red] {e}")
        return False

    # Verify checksum
    try:
        verify_checksum(archive_path, release.assets, asset)
        console.print("  [green]✓[/green] Checksum verified")
    except ChecksumError as e:
        console.print(f"[red]Error:[/red] {e}")
        archive_path.unlink(missing_ok=True)
        return False

    # Extract and install
    temp_dir = None
    try:
        temp_dir = extract_archive(archive_path)
        binaries = install_binaries(temp_dir)

        if not binaries:
            console.print("[red]Error:[/red] No executable binaries found in archive")
            return False

        console.print(f"  Installed binaries: {', '.join(binaries)}")

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
        console.print(f"\n[dim]Make sure {config.bin_dir} is in your PATH[/dim]")
        return True

    except ExtractionError as e:
        console.print(f"[red]Error:[/red] {e}")
        return False
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)
        archive_path.unlink(missing_ok=True)


def install_from_source(
    release: Release,
    owner: str,
    repo: str,
    manifest: Manifest,
    config,
) -> bool:
    """Install scripts from source tarball. Returns True on success."""
    if not release.tarball_url:
        console.print("[red]Error:[/red] No source tarball available")
        return False

    console.print("  Downloading source tarball...")

    # Download source
    try:
        tarball_name = f"{repo}-{release.tag_name}.tar.gz"
        archive_path = download_file(release.tarball_url, filename=tarball_name)
    except DownloadError as e:
        console.print(f"[red]Error:[/red] {e}")
        return False

    # Extract and find scripts
    temp_dir = None
    try:
        temp_dir = extract_archive(archive_path)
        scripts = find_scripts(temp_dir, repo_name=repo)

        if not scripts:
            console.print("[yellow]No executable scripts found in source[/yellow]")
            return False

        # Show found scripts
        console.print(f"\n  Found {len(scripts)} script(s):")
        for i, script in enumerate(scripts[:10]):  # Limit display
            rel_path = script.relative_to(temp_dir)
            # Read shebang to show interpreter
            with open(script, "rb") as f:
                shebang = f.readline().decode("utf-8", errors="ignore").strip()
            console.print(f"    {i+1}. [cyan]{script.name}[/cyan] ({shebang})")
            if script.name.lower() == repo.lower():
                console.print(f"       [green]↑ matches repo name[/green]")

        if len(scripts) > 10:
            console.print(f"    ... and {len(scripts) - 10} more")

        # Prompt for confirmation
        console.print("")
        if not Confirm.ask("Install these scripts?", default=True):
            console.print("Installation cancelled")
            return False

        # Install scripts
        bin_dir = config.bin_dir
        bin_dir.mkdir(parents=True, exist_ok=True)

        installed = []
        for script in scripts:
            # For source installs, only install scripts matching repo name
            # or scripts in the root/bin directory
            rel_parts = script.relative_to(temp_dir).parts
            # Skip if deeply nested (more than 2 levels in extracted dir)
            if len(rel_parts) > 3:
                continue

            dest = bin_dir / script.name
            import shutil
            shutil.copy2(script, dest)
            make_executable(dest)
            installed.append(script.name)

        if not installed:
            # Fall back to installing the first script that matches repo name
            for script in scripts:
                if script.name.lower() == repo.lower():
                    dest = bin_dir / script.name
                    import shutil
                    shutil.copy2(script, dest)
                    make_executable(dest)
                    installed.append(script.name)
                    break

            if not installed and scripts:
                # Just install the first one
                script = scripts[0]
                dest = bin_dir / script.name
                import shutil
                shutil.copy2(script, dest)
                make_executable(dest)
                installed.append(script.name)

        if not installed:
            console.print("[red]Error:[/red] No scripts installed")
            return False

        console.print(f"  Installed scripts: {', '.join(installed)}")

        # Update manifest
        package = Package(
            name=repo,
            repo=f"{owner}/{repo}",
            version=release.version,
            tag=release.tag_name,
            installed_at=datetime.now(),
            binaries=installed,
            asset="(source)",
        )
        manifest.add(package)

        console.print(
            f"\n[green]✓[/green] Successfully installed [bold]{repo}[/bold] {release.version} from source"
        )
        console.print(f"\n[dim]Make sure {config.bin_dir} is in your PATH[/dim]")
        return True

    except ExtractionError as e:
        console.print(f"[red]Error:[/red] {e}")
        return False
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)
        archive_path.unlink(missing_ok=True)


def find_asset_by_name(assets: list[Asset], pattern: str) -> Asset | None:
    """Find an asset by exact name or glob pattern."""
    import fnmatch

    # Try exact match first
    for asset in assets:
        if asset.name == pattern:
            return asset

    # Try glob pattern match
    for asset in assets:
        if fnmatch.fnmatch(asset.name.lower(), pattern.lower()):
            return asset

    return None


@click.command()
@click.argument("repo_spec")
@click.option("--version", "-v", "version_tag", help="Specific version/tag to install")
@click.option("--force", "-f", is_flag=True, help="Force reinstall if already installed")
@click.option("--source", "-s", is_flag=True, help="Install from source (for script-only repos)")
@click.option("--asset", "-a", "asset_pattern", help="Specific asset name or pattern to install")
@click.option("--list-assets", "-l", is_flag=True, help="List available assets and exit")
def install(repo_spec: str, version_tag: str | None, force: bool, source: bool, asset_pattern: str | None, list_assets: bool):
    """Install a package from GitHub releases.

    REPO_SPEC can be:
      - owner/repo format (e.g., junegunn/fzf)
      - Full GitHub URL (e.g., https://github.com/junegunn/fzf)

    Use --source for repositories that only provide source releases (like neofetch).
    Use --asset to specify which release asset to install (exact name or glob pattern).
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

        # If --list-assets, show assets and exit
        if list_assets:
            if not release.assets:
                console.print("\n[yellow]No assets in this release[/yellow]")
            else:
                console.print(f"\n[bold]Available assets ({len(release.assets)}):[/bold]")
                for a in release.assets:
                    size_mb = a.size / (1024 * 1024)
                    console.print(f"  [cyan]{a.name}[/cyan] ({size_mb:.1f} MB)")
            raise SystemExit(0)

        # If --source flag, skip binary search
        if source:
            console.print("  [dim]Installing from source (--source flag)[/dim]")
            if install_from_source(release, owner, repo, manifest, config):
                raise SystemExit(0)
            raise SystemExit(1)

        # If --asset specified, find that specific asset
        if asset_pattern:
            asset = find_asset_by_name(release.assets, asset_pattern)
            if asset is None:
                console.print(f"[red]Error:[/red] No asset matching '{asset_pattern}'")
                console.print("\nAvailable assets:")
                for a in release.assets:
                    console.print(f"  - {a.name}")
                raise SystemExit(1)

            if install_from_binary(release, asset, owner, repo, manifest, config):
                raise SystemExit(0)
            raise SystemExit(1)

        # Try to find binary asset automatically
        platform_info = get_platform_info()
        console.print(f"  Platform: {platform_info.os}/{platform_info.arch}")

        matching_assets = find_best_assets(release.assets, platform_info)

        if len(matching_assets) == 1:
            # Single best match, install it
            asset = matching_assets[0]
            if install_from_binary(release, asset, owner, repo, manifest, config):
                raise SystemExit(0)
            raise SystemExit(1)

        elif len(matching_assets) > 1:
            # Multiple equally-good matches, prompt user to choose
            console.print(f"\n[yellow]Multiple compatible assets found:[/yellow]")
            for i, a in enumerate(matching_assets, 1):
                size_mb = a.size / (1024 * 1024)
                console.print(f"  {i}. [cyan]{a.name}[/cyan] ({size_mb:.1f} MB)")

            console.print("")
            while True:
                choice = click.prompt(
                    "Select asset number",
                    type=int,
                    default=1,
                )
                if 1 <= choice <= len(matching_assets):
                    asset = matching_assets[choice - 1]
                    break
                console.print(f"[red]Please enter a number between 1 and {len(matching_assets)}[/red]")

            if install_from_binary(release, asset, owner, repo, manifest, config):
                raise SystemExit(0)
            raise SystemExit(1)

        # No binary found - offer source install
        if release.assets:
            console.print(
                f"[yellow]No compatible binary found for {platform_info.os}/{platform_info.arch}[/yellow]"
            )
            console.print("Available assets:")
            for a in release.assets:
                console.print(f"  - {a.name}")
            console.print("\n[dim]Tip: Use --asset <name> to install a specific asset[/dim]")
        else:
            console.print("[yellow]This release has no binary assets[/yellow]")

        # Prompt for source install
        console.print("")
        if Confirm.ask("Try installing from source?", default=True):
            if install_from_source(release, owner, repo, manifest, config):
                raise SystemExit(0)

        raise SystemExit(1)
