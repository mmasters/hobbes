"""Manifest file management for tracking installed packages."""

from pathlib import Path
from datetime import datetime
import yaml

from hobbes.core.config import get_config
from hobbes.models.package import Package


MANIFEST_VERSION = 1


class Manifest:
    """Manages the hobbes manifest file."""

    def __init__(self, path: Path | None = None):
        self.path = path or get_config().manifest_path
        self._packages: dict[str, Package] = {}
        self._load()

    def _load(self) -> None:
        """Load manifest from file."""
        if not self.path.exists():
            self._packages = {}
            return

        with open(self.path) as f:
            data = yaml.safe_load(f) or {}

        packages_data = data.get("packages", {})
        self._packages = {
            name: Package.from_dict(name, pkg_data)
            for name, pkg_data in packages_data.items()
        }

    def save(self) -> None:
        """Save manifest to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": MANIFEST_VERSION,
            "packages": {
                name: pkg.to_dict() for name, pkg in self._packages.items()
            },
        }

        with open(self.path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get(self, name: str) -> Package | None:
        """Get a package by name."""
        return self._packages.get(name)

    def add(self, package: Package) -> None:
        """Add or update a package."""
        self._packages[package.name] = package
        self.save()

    def remove(self, name: str) -> Package | None:
        """Remove a package by name."""
        package = self._packages.pop(name, None)
        if package:
            self.save()
        return package

    def list_packages(self) -> list[Package]:
        """List all installed packages."""
        return list(self._packages.values())

    def has(self, name: str) -> bool:
        """Check if a package is installed."""
        return name in self._packages

    def pin(self, name: str) -> bool:
        """Pin a package to its current version."""
        if name in self._packages:
            self._packages[name].pinned = True
            self.save()
            return True
        return False

    def unpin(self, name: str) -> bool:
        """Unpin a package."""
        if name in self._packages:
            self._packages[name].pinned = False
            self.save()
            return True
        return False
