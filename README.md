# Hobbes

A package manager for GitHub release binaries.

Hobbes downloads binaries from GitHub releases, extracts them, and manages versions locally.

## Installation

### One-liner (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/mmasters/hobbes/main/scripts/install.sh | bash
```

### Using pip

```bash
pip install git+https://github.com/mmasters/hobbes.git
```

### Using pipx

```bash
pipx install git+https://github.com/mmasters/hobbes.git
```

## Setup

Add the hobbes bin directory to your PATH:

```bash
export PATH="$HOME/.hobbes/bin:$PATH"
```

Add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.).

## Usage

### Install a package

```bash
# Using owner/repo format
hobbes install junegunn/fzf

# Using full GitHub URL
hobbes install https://github.com/BurntSushi/ripgrep

# Install specific version
hobbes install sharkdp/bat --version v0.24.0

# Install from source (for repos without binaries, like neofetch)
hobbes install dylanaraps/neofetch --source
```

For repositories that only provide source releases (no pre-built binaries), hobbes will automatically detect executable scripts and offer to install them.

### List installed packages

```bash
hobbes list
```

### Update packages

```bash
# Update single package
hobbes update fzf

# Update all packages
hobbes upgrade-all
```

### Check for updates

```bash
hobbes outdated
```

### Show package info

```bash
hobbes info fzf
```

### Search for packages

```bash
hobbes search "fuzzy finder"
```

### Pin/unpin versions

```bash
# Pin to current version (skip during upgrade-all)
hobbes pin fzf

# Unpin
hobbes unpin fzf
```

### Uninstall a package

```bash
hobbes uninstall fzf
```

### Uninstall hobbes

To completely remove hobbes from your system:

```bash
# Remove hobbes and all installed packages
rm -rf ~/.hobbes

# If installed with pip
pip uninstall hobbes

# If installed with pipx
pipx uninstall hobbes
```

Don't forget to remove the PATH export from your shell profile (`~/.bashrc`, `~/.zshrc`, etc.).

## Configuration

Hobbes stores everything in `~/.hobbes/` by default:

- `~/.hobbes/bin/` - Installed binaries
- `~/.hobbes/cache/` - Downloaded archives (temporary)
- `~/.hobbes/manifest.yaml` - Package database

Set `HOBBES_HOME` environment variable to change the base directory.

## How it works

1. Fetches release information from GitHub API
2. Auto-detects your platform (OS and architecture)
3. Selects the best matching binary asset
4. Verifies checksum if available
5. Extracts archive and installs executables
6. Tracks installed packages in manifest

## Supported formats

- `.tar.gz`, `.tgz`
- `.tar.xz`
- `.zip`
- `.gz` (single file)
- Raw binaries (no extension)

## License

MIT
