"""Checksum verification for downloaded files."""

import hashlib
import re
from pathlib import Path

from hobbes.core.downloader import download_text
from hobbes.models.release import Asset


class ChecksumError(Exception):
    """Checksum verification failed."""

    pass


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_checksum_asset(assets: list[Asset], target_asset: Asset) -> Asset | None:
    """Find a checksum file asset for the target asset."""
    target_name = target_asset.name.lower()

    # Common checksum file patterns
    checksum_patterns = [
        "sha256sums",
        "sha256",
        "checksums",
        "checksums.txt",
        f"{target_asset.name}.sha256",
        f"{target_asset.name}.sha256sum",
    ]

    for asset in assets:
        name = asset.name.lower()
        if any(pattern in name for pattern in checksum_patterns):
            return asset

    return None


def parse_checksum_file(content: str, target_filename: str) -> str | None:
    """Parse a checksum file and find the hash for target file.

    Supports formats:
    - <hash>  <filename>
    - <hash> *<filename>
    - <filename>: <hash>
    """
    target_filename_lower = target_filename.lower()

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Format: hash  filename or hash *filename
        match = re.match(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
        if match:
            hash_value, filename = match.groups()
            if filename.lower() == target_filename_lower:
                return hash_value.lower()

        # Format: filename: hash
        match = re.match(r"(.+?):\s*([a-fA-F0-9]{64})", line)
        if match:
            filename, hash_value = match.groups()
            if filename.lower() == target_filename_lower:
                return hash_value.lower()

    return None


def verify_checksum(
    file_path: Path,
    assets: list[Asset],
    target_asset: Asset,
) -> bool:
    """Verify checksum of downloaded file if checksum is available.

    Returns True if:
    - Checksum matches
    - No checksum file is available (skip verification)

    Raises ChecksumError if checksum doesn't match.
    """
    checksum_asset = find_checksum_asset(assets, target_asset)
    if checksum_asset is None:
        return True  # No checksum available, skip

    # Download checksum file
    checksum_content = download_text(checksum_asset.download_url)
    if checksum_content is None:
        return True  # Couldn't download, skip

    expected_hash = parse_checksum_file(checksum_content, target_asset.name)
    if expected_hash is None:
        return True  # Couldn't find hash for our file, skip

    actual_hash = calculate_sha256(file_path)

    if actual_hash != expected_hash:
        raise ChecksumError(
            f"Checksum mismatch for {target_asset.name}:\n"
            f"  Expected: {expected_hash}\n"
            f"  Got:      {actual_hash}"
        )

    return True
