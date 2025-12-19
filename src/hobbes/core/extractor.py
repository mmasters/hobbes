"""Archive extraction and binary installation."""

from pathlib import Path
import tarfile
import zipfile
import gzip
import shutil
import stat
import os
import tempfile

from hobbes.core.config import get_config


class ExtractionError(Exception):
    """Error during extraction."""

    pass


def is_executable(path: Path) -> bool:
    """Check if a file is likely an executable binary."""
    if not path.is_file():
        return False

    # Check if it's already marked executable
    if os.access(path, os.X_OK):
        return True

    # Check for common binary signatures
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            # ELF binary
            if header[:4] == b"\x7fELF":
                return True
            # Mach-O binary (macOS)
            if header[:4] in (
                b"\xfe\xed\xfa\xce",  # 32-bit
                b"\xfe\xed\xfa\xcf",  # 64-bit
                b"\xca\xfe\xba\xbe",  # Universal
                b"\xcf\xfa\xed\xfe",  # 64-bit reversed
                b"\xce\xfa\xed\xfe",  # 32-bit reversed
            ):
                return True
            # Windows PE
            if header[:2] == b"MZ":
                return True
            # Shell script
            if header[:2] == b"#!":
                return True
    except (IOError, OSError):
        pass

    return False


def find_executables(directory: Path) -> list[Path]:
    """Find all executable files in a directory."""
    executables = []

    for item in directory.rglob("*"):
        if item.is_file() and is_executable(item):
            executables.append(item)

    return executables


def is_script(path: Path) -> bool:
    """Check if a file is an executable script (has shebang)."""
    if not path.is_file():
        return False

    try:
        with open(path, "rb") as f:
            header = f.read(2)
            return header == b"#!"
    except (IOError, OSError):
        return False


def find_scripts(directory: Path, repo_name: str | None = None) -> list[Path]:
    """Find script files in a source directory.

    Looks for files with shebangs, prioritizing those matching repo_name.
    Excludes common non-entry-point scripts.
    """
    exclude_patterns = {
        "test", "tests", "spec", "specs", "example", "examples",
        "doc", "docs", "build", "dist", ".git", "node_modules",
        "vendor", "__pycache__", ".github",
    }
    exclude_extensions = {".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml"}

    scripts = []

    for item in directory.rglob("*"):
        if not item.is_file():
            continue

        # Skip files in excluded directories
        if any(part.lower() in exclude_patterns for part in item.parts):
            continue

        # Skip files with excluded extensions
        if item.suffix.lower() in exclude_extensions:
            continue

        if is_script(item):
            scripts.append(item)

    # Sort: prioritize scripts matching repo name, then by path depth (shallower first)
    def sort_key(p: Path) -> tuple[int, int, str]:
        name_match = 0 if (repo_name and p.stem.lower() == repo_name.lower()) else 1
        depth = len(p.relative_to(directory).parts)
        return (name_match, depth, p.name.lower())

    scripts.sort(key=sort_key)
    return scripts


def make_executable(path: Path) -> None:
    """Make a file executable."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def extract_archive(archive_path: Path, dest_dir: Path | None = None) -> Path:
    """Extract an archive to a temporary directory.

    Returns the directory containing extracted files.
    """
    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix="hobbes_"))
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)

    name = archive_path.name.lower()

    try:
        if name.endswith(".tar.gz") or name.endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(dest_dir, filter="data")

        elif name.endswith(".tar.xz"):
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(dest_dir, filter="data")

        elif name.endswith(".tar"):
            with tarfile.open(archive_path, "r:") as tar:
                tar.extractall(dest_dir, filter="data")

        elif name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)

        elif name.endswith(".gz"):
            # Single gzipped file
            output_name = archive_path.stem  # Remove .gz
            output_path = dest_dir / output_name
            with gzip.open(archive_path, "rb") as gz:
                with open(output_path, "wb") as out:
                    shutil.copyfileobj(gz, out)

        else:
            # Assume raw binary - just copy it
            output_path = dest_dir / archive_path.name
            shutil.copy2(archive_path, output_path)

    except (tarfile.TarError, zipfile.BadZipFile, gzip.BadGzipFile, OSError) as e:
        raise ExtractionError(f"Failed to extract {archive_path}: {e}")

    return dest_dir


def install_binaries(
    source_dir: Path,
    bin_dir: Path | None = None,
) -> list[str]:
    """Install executables from extracted directory to bin directory.

    Returns list of installed binary names.
    """
    if bin_dir is None:
        bin_dir = get_config().bin_dir

    bin_dir.mkdir(parents=True, exist_ok=True)

    executables = find_executables(source_dir)
    installed = []

    for exe in executables:
        dest = bin_dir / exe.name
        shutil.copy2(exe, dest)
        make_executable(dest)
        installed.append(exe.name)

    return installed


def uninstall_binaries(binaries: list[str], bin_dir: Path | None = None) -> None:
    """Remove installed binaries."""
    if bin_dir is None:
        bin_dir = get_config().bin_dir

    for name in binaries:
        path = bin_dir / name
        if path.exists():
            path.unlink()


def cleanup_temp_dir(temp_dir: Path) -> None:
    """Clean up a temporary directory."""
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
