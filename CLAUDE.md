# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hobbes is a Python CLI package manager that downloads binaries from GitHub releases and manages them locally. It auto-detects platform (OS/architecture), verifies checksums when available, and tracks installed packages in a YAML manifest.

## Commands

```bash
# Install dependencies and hobbes in development mode
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run hobbes CLI
hobbes --help
hobbes install junegunn/fzf
hobbes list

# Run tests
pip install -e ".[dev]"
pytest
```

## Architecture

```
src/hobbes/
├── cli.py              # Click CLI entry point, registers all commands
├── commands/           # One file per CLI command
│   ├── install.py      # Main install flow: fetch release → download → verify → extract → install
│   ├── update.py       # Update and upgrade-all commands
│   └── ...
├── core/
│   ├── config.py       # HobbesConfig dataclass, paths (~/.hobbes/)
│   ├── manifest.py     # YAML manifest read/write for tracking packages
│   ├── github.py       # GitHub API client using httpx
│   ├── platform.py     # OS/arch detection and asset matching logic
│   ├── downloader.py   # Download with rich progress bar
│   ├── extractor.py    # Archive extraction (tar.gz, zip, tar.xz, raw)
│   └── checksum.py     # SHA256 verification from release checksums
└── models/
    ├── package.py      # Package dataclass (installed package)
    └── release.py      # Release/Asset dataclasses (GitHub API response)
```

## Key Design Decisions

- **Platform matching**: `core/platform.py` scores assets by OS/arch patterns in filename. Higher score = better match.
- **Manifest**: YAML file at `~/.hobbes/manifest.yaml` tracks all installed packages with version, binaries list, pinned status.
- **Binary detection**: `core/extractor.py` uses file magic bytes (ELF, Mach-O, PE, shebang) to identify executables in archives.
- **No auth required**: Public repos only, no GitHub token needed.

## Dependencies

- `click` - CLI framework
- `httpx` - HTTP client
- `pyyaml` - Manifest serialization
- `rich` - Progress bars and formatted output
