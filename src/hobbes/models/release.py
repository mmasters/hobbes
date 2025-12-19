"""GitHub release data models."""

from dataclasses import dataclass


@dataclass
class Asset:
    """Represents a GitHub release asset."""

    name: str
    download_url: str
    size: int
    content_type: str

    @classmethod
    def from_api_response(cls, data: dict) -> "Asset":
        """Create Asset from GitHub API response."""
        return cls(
            name=data["name"],
            download_url=data["browser_download_url"],
            size=data["size"],
            content_type=data.get("content_type", "application/octet-stream"),
        )


@dataclass
class Release:
    """Represents a GitHub release."""

    tag_name: str
    name: str
    prerelease: bool
    draft: bool
    assets: list[Asset]
    published_at: str
    tarball_url: str = ""
    zipball_url: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> "Release":
        """Create Release from GitHub API response."""
        assets = [Asset.from_api_response(a) for a in data.get("assets", [])]
        return cls(
            tag_name=data["tag_name"],
            name=data.get("name") or data["tag_name"],
            prerelease=data.get("prerelease", False),
            draft=data.get("draft", False),
            assets=assets,
            published_at=data.get("published_at", ""),
            tarball_url=data.get("tarball_url", ""),
            zipball_url=data.get("zipball_url", ""),
        )

    @property
    def version(self) -> str:
        """Get version string (tag without 'v' prefix if present)."""
        tag = self.tag_name
        if tag.startswith("v"):
            return tag[1:]
        return tag
