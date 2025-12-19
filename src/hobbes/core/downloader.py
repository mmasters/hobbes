"""Download functionality with progress reporting."""

from pathlib import Path
import httpx
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from hobbes.core.config import get_config


class DownloadError(Exception):
    """Error during download."""

    pass


def download_file(
    url: str,
    dest: Path | None = None,
    filename: str | None = None,
    show_progress: bool = True,
) -> Path:
    """Download a file from URL.

    Args:
        url: URL to download from
        dest: Destination directory (defaults to cache dir)
        filename: Filename to save as (defaults to URL filename)
        show_progress: Whether to show progress bar

    Returns:
        Path to downloaded file
    """
    if dest is None:
        dest = get_config().cache_dir
    dest.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = url.split("/")[-1]

    file_path = dest / filename

    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        if response.status_code != 200:
            raise DownloadError(
                f"Failed to download {url}: HTTP {response.status_code}"
            )

        total = int(response.headers.get("content-length", 0))

        if show_progress and total > 0:
            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task(f"Downloading {filename}", total=total)

                with open(file_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
        else:
            with open(file_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    return file_path


def download_text(url: str) -> str | None:
    """Download text content from URL.

    Returns None if download fails.
    """
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        if response.status_code == 200:
            return response.text
    except httpx.HTTPError:
        pass
    return None
