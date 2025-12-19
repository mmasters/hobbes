"""Platform detection and asset matching."""

import platform
import re
from dataclasses import dataclass

from hobbes.models.release import Asset


@dataclass
class PlatformInfo:
    """Current platform information."""

    os: str  # darwin, linux, windows
    arch: str  # amd64, arm64

    @classmethod
    def detect(cls) -> "PlatformInfo":
        """Detect current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize OS
        if system == "darwin":
            os_name = "darwin"
        elif system == "linux":
            os_name = "linux"
        elif system == "windows":
            os_name = "windows"
        else:
            os_name = system

        # Normalize architecture
        if machine in ("x86_64", "amd64"):
            arch = "amd64"
        elif machine in ("arm64", "aarch64"):
            arch = "arm64"
        elif machine in ("i386", "i686", "x86"):
            arch = "386"
        else:
            arch = machine

        return cls(os=os_name, arch=arch)


# Patterns to match OS in asset names
OS_PATTERNS = {
    "darwin": [r"darwin", r"macos", r"mac", r"osx", r"apple"],
    "linux": [r"linux"],
    "windows": [r"windows", r"win", r"win64", r"win32"],
}

# Patterns to match architecture in asset names
ARCH_PATTERNS = {
    "amd64": [r"amd64", r"x86_64", r"x64", r"64bit"],
    "arm64": [r"arm64", r"aarch64"],
    "386": [r"386", r"i386", r"i686", r"x86", r"32bit"],
}


def score_asset(asset: Asset, platform_info: PlatformInfo) -> int:
    """Score an asset based on platform match. Higher is better, -1 means no match."""
    name = asset.name.lower()

    # Skip non-binary files
    skip_extensions = [".txt", ".md", ".sha256", ".sig", ".asc", ".sbom"]
    if any(name.endswith(ext) for ext in skip_extensions):
        return -1

    # Check for binary/archive extensions
    binary_extensions = [".tar.gz", ".tgz", ".zip", ".tar.xz", ".gz", ".exe", ""]
    has_valid_extension = any(
        name.endswith(ext) for ext in binary_extensions if ext
    ) or "." not in name.split("/")[-1].rsplit("-", 1)[-1]

    if not has_valid_extension:
        # Check if it might be a raw binary (no extension or executable)
        pass

    score = 0

    # Match OS
    os_matched = False
    for pattern in OS_PATTERNS.get(platform_info.os, []):
        if re.search(pattern, name, re.IGNORECASE):
            os_matched = True
            score += 100
            break

    # Match architecture
    arch_matched = False
    for pattern in ARCH_PATTERNS.get(platform_info.arch, []):
        if re.search(pattern, name, re.IGNORECASE):
            arch_matched = True
            score += 50
            break

    # Require at least OS match
    if not os_matched:
        # Check if this might be a universal/any-platform binary
        if re.search(r"(universal|any|all)", name, re.IGNORECASE):
            score += 10
        else:
            return -1

    # Prefer exact matches
    if os_matched and arch_matched:
        score += 25

    # Prefer certain archive formats
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        score += 10
    elif name.endswith(".zip"):
        score += 8
    elif name.endswith(".tar.xz"):
        score += 6

    return score


def find_best_assets(assets: list[Asset], platform_info: PlatformInfo | None = None) -> list[Asset]:
    """Find all matching assets with the highest score for the current platform.

    Returns multiple assets if they tie for the highest score.
    """
    if platform_info is None:
        platform_info = PlatformInfo.detect()

    scored = []
    for asset in assets:
        score = score_asset(asset, platform_info)
        if score >= 0:
            scored.append((score, asset))

    if not scored:
        return []

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return all assets with the top score
    top_score = scored[0][0]
    return [asset for score, asset in scored if score == top_score]


def find_best_asset(assets: list[Asset], platform_info: PlatformInfo | None = None) -> Asset | None:
    """Find the best matching asset for the current platform."""
    best = find_best_assets(assets, platform_info)
    return best[0] if best else None


def get_platform_info() -> PlatformInfo:
    """Get current platform information."""
    return PlatformInfo.detect()
