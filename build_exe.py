#!/usr/bin/env python3
"""Build script for creating standalone Windows executable using Nuitka.

This script compiles jmeter-gen CLI into a standalone Windows executable
that can be distributed without requiring Python installation.

Requirements:
    - Python 3.9+
    - Nuitka: pip install nuitka ordered-set zstandard
    - C compiler (MSVC or MinGW64)

Usage:
    python build_exe.py [--onefile] [--clean]

Output:
    dist/cli_standalone.dist/jmeter-gen.exe (folder mode, default)
    dist/jmeter-gen.exe (onefile mode)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def check_nuitka():
    """Check if Nuitka is installed."""
    try:
        import nuitka  # noqa: F401
        return True
    except ImportError:
        return False


def clean_build():
    """Remove previous build artifacts."""
    paths_to_clean = [
        "dist",
        "build",
        "cli_standalone.build",
        "cli_standalone.dist",
        "cli_standalone.onefile-build",
    ]
    for path in paths_to_clean:
        p = Path(path)
        if p.exists():
            print(f"Removing {path}...")
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


def build(onefile: bool = False):
    """Build the executable using Nuitka.

    Args:
        onefile: If True, create single executable file.
                 If False (default), create folder with exe + dependencies.
    """
    if not check_nuitka():
        print("Error: Nuitka not installed.")
        print("Install with: pip install nuitka ordered-set zstandard")
        sys.exit(1)

    print("=" * 60)
    print("Building jmeter-gen standalone executable")
    print("=" * 60)
    print(f"Mode: {'onefile' if onefile else 'folder'}")
    print()

    cmd = [
        sys.executable, "-m", "nuitka",
        # Output configuration
        "--output-dir=dist",
        "--output-filename=jmeter-gen",
        # Build mode
        "--standalone" if not onefile else "--onefile",
        # Include packages
        "--include-package=jmeter_gen.core",
        "--include-package=jmeter_gen.core.importers",
        # Required dependencies
        "--include-package=click",
        "--include-package=rich",
        "--include-package=yaml",
        "--include-package=questionary",
        "--include-package=pydantic",
        "--include-package=pydantic_core",
        # Exclude MCP (not needed for standalone)
        "--nofollow-import-to=mcp",
        "--nofollow-import-to=httpx",
        "--nofollow-import-to=anyio",
        "--nofollow-import-to=jmeter_gen.mcp_server",
        # Enable optimizations
        "--enable-plugin=anti-bloat",
        # Assume yes for downloads (e.g., dependency walker)
        "--assume-yes-for-downloads",
        # Windows console app
        "--windows-console-mode=force",
        # Show progress
        "--show-progress",
        "--show-memory",
        # Entry point
        "jmeter_gen/cli_standalone.py",
    ]

    print("Running Nuitka...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("Build successful!")
        print("=" * 60)
        if onefile:
            print("Output: dist/jmeter-gen.exe")
        else:
            print("Output: dist/cli_standalone.dist/jmeter-gen.exe")
        print()
        print("Test with:")
        if onefile:
            print("  ./dist/jmeter-gen.exe --version")
        else:
            print("  ./dist/cli_standalone.dist/jmeter-gen.exe --version")
    else:
        print()
        print("Build failed!")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build jmeter-gen as standalone Windows executable"
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create single executable file (slower startup, easier distribution)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean build artifacts, don't build",
    )

    args = parser.parse_args()

    if args.clean or args.clean_only:
        clean_build()
        if args.clean_only:
            print("Clean complete.")
            return

    build(onefile=args.onefile)


if __name__ == "__main__":
    main()
