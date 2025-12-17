# Building Standalone Windows Executable

This guide explains how to build jmeter-gen as a standalone Windows executable using Nuitka.

## Overview

The standalone executable allows distribution of jmeter-gen without requiring Python installation on the target machine. The executable includes all dependencies and runs independently.

**Note:** The standalone version excludes MCP Server functionality. For full features including MCP Server, install from PyPI: `pip install jmeter-test-generator`

## Prerequisites

### Python
- Python 3.9 or higher

### C Compiler (one of the following)
- **MSVC** - Visual Studio Build Tools (recommended)
  - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - Select "Desktop development with C++" workload
- **MinGW64** via MSYS2
  - Download: https://www.msys2.org/
  - Install gcc: `pacman -S mingw-w64-x86_64-gcc`

### Disk Space
- ~2GB for build cache (first build)
- ~100MB for final output

## Install Build Dependencies

```bash
# Option 1: Install build extras
pip install -e ".[build]"

# Option 2: Install directly
pip install nuitka ordered-set zstandard
```

## Build Process

### Folder Mode (Recommended)

Folder mode produces faster startup times and is recommended for most use cases.

```bash
python -m nuitka \
    --standalone \
    --output-dir=dist \
    --output-filename=jmeter-gen \
    --include-package=jmeter_gen.core \
    --enable-plugin=anti-bloat \
    --windows-console-mode=force \
    jmeter_gen/cli_standalone.py
```

### Onefile Mode

Single file mode is easier to distribute but has slower startup.

```bash
python -m nuitka \
    --onefile \
    --output-dir=dist \
    --output-filename=jmeter-gen \
    --include-package=jmeter_gen.core \
    --enable-plugin=anti-bloat \
    --windows-console-mode=force \
    jmeter_gen/cli_standalone.py
```

### Clean Previous Builds

```bash
# Remove build artifacts before rebuilding
rm -rf dist/ build/ *.build/
```

## Output

### Folder Mode (default)
```
dist/
  cli_standalone.dist/
    jmeter-gen.exe      # Main executable (~5-10 MB)
    python3X.dll        # Python runtime
    *.pyd               # Compiled modules
    ...                 # Total: ~50-80 MB
```

### Onefile Mode
```
dist/
  jmeter-gen.exe        # Single file (~100-150 MB)
```

## Usage

```bash
# From dist folder (folder mode)
./dist/cli_standalone.dist/jmeter-gen.exe --help
./dist/cli_standalone.dist/jmeter-gen.exe --version
./dist/cli_standalone.dist/jmeter-gen.exe analyze
./dist/cli_standalone.dist/jmeter-gen.exe generate --spec openapi.yaml

# Onefile mode
./dist/jmeter-gen.exe --help
```

## Distribution

### Folder Mode
Copy the entire `cli_standalone.dist` folder to the target machine. All files must remain in the same directory structure.

### Onefile Mode
Copy only `jmeter-gen.exe`. The executable is self-contained.

**No Python installation required on target machine.**

## Available Commands (Standalone)

| Command | Description |
|---------|-------------|
| `analyze` | Find OpenAPI specs in project |
| `generate` | Generate JMX from spec |
| `validate script FILE` | Validate JMX file |
| `validate scenario FILE` | Validate scenario file |
| `new scenario` | Interactive scenario wizard |

## Limitations

- **MCP Server not available** - The `jmeter-gen mcp` command is not included
- **Windows only** - Cross-platform use requires PyPI package

## Troubleshooting

### Missing C Compiler

```
Error: Unable to find a C compiler
```

Install Visual Studio Build Tools or MinGW64 (see Prerequisites).

### Build Fails with Import Errors

```
Error: Could not find module 'xxx'
```

Ensure all dependencies are installed:
```bash
pip install -e ".[dev,build]"
```

### Slow First Build

The first build takes longer as Nuitka compiles Python to C. Subsequent builds use cached results and are faster.

### Large Executable Size

Use folder mode (default) instead of `--onefile` for smaller total size and faster startup.

### Anti-virus False Positives

Some anti-virus software may flag Nuitka executables. Add an exclusion for the dist folder if needed.

## Build Time Reference

| Mode | First Build | Cached Build |
|------|-------------|--------------|
| Folder | 5-15 min | 1-3 min |
| Onefile | 10-20 min | 2-5 min |

Times vary based on CPU, disk speed, and available memory.
