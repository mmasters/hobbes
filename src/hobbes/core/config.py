"""Configuration and path management for hobbes."""

from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class HobbesConfig:
    """Configuration for hobbes package manager."""

    base_dir: Path
    bin_dir: Path
    cache_dir: Path
    manifest_path: Path

    @classmethod
    def default(cls) -> "HobbesConfig":
        """Create config with default paths."""
        base = Path(os.environ.get("HOBBES_HOME", Path.home() / ".hobbes"))
        return cls(
            base_dir=base,
            bin_dir=base / "bin",
            cache_dir=base / "cache",
            manifest_path=base / "manifest.yaml",
        )

    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: HobbesConfig | None = None


def get_config() -> HobbesConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = HobbesConfig.default()
    return _config


def set_config(config: HobbesConfig) -> None:
    """Set a custom configuration (useful for testing)."""
    global _config
    _config = config
