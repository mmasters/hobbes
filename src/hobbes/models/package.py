"""Package data model."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Package:
    """Represents an installed package."""

    name: str
    repo: str  # owner/repo format
    version: str
    tag: str
    installed_at: datetime
    binaries: list[str] = field(default_factory=list)
    pinned: bool = False
    asset: str = ""  # The asset filename that was downloaded

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "repo": self.repo,
            "version": self.version,
            "tag": self.tag,
            "installed_at": self.installed_at.isoformat(),
            "binaries": self.binaries,
            "pinned": self.pinned,
            "asset": self.asset,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Package":
        """Create Package from dictionary."""
        installed_at = data.get("installed_at")
        if isinstance(installed_at, str):
            installed_at = datetime.fromisoformat(installed_at)
        elif installed_at is None:
            installed_at = datetime.now()

        return cls(
            name=name,
            repo=data["repo"],
            version=data["version"],
            tag=data["tag"],
            installed_at=installed_at,
            binaries=data.get("binaries", []),
            pinned=data.get("pinned", False),
            asset=data.get("asset", ""),
        )
