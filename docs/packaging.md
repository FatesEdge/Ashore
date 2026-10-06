# Packaging

Ashore uses PyInstaller through `make.py`.

The build script keeps a reviewed `PYINSTALLER_EXCLUDES` list for large optional Python/Qt modules that Ashore does not use. Required Qt modules such as Core, Gui, Widgets, Network, Svg, and WebSockets must never be added to that list. Linux builds also request binary stripping to reduce the shipped Qt/Python footprint.

PyInstaller module exclusions apply to Python import modules. They are not a reliable way to remove arbitrary shared libraries or Qt plugins. Linux packaging therefore uses a generated PyInstaller spec to filter a deliberately small set of native Qt components after dependency analysis and before the onefile archive is assembled. The filter keeps X11, Wayland, GTK/portal integration, input methods, SVG, Network, WebSockets and Qt translations; it removes only reviewed embedded/headless platform plugins and unused image/PDF plugins. Native libraries should only be removed when their dependency relationship has been verified.

## Linux

Supported build modes:

```bash
python make.py onefile
python make.py onedir
```

Outputs:

- `dist/Ashore.Linux.onefile/`
- `dist/Ashore.Linux.onedir/`

Both package directories contain:

- the Ashore executable or onedir application directory
- `icon.png`
- `ashore.desktop`
- `install.sh`

For `onedir`, the entire generated Ashore directory is required because it contains the PyInstaller runtime files.

Install with:

```bash
sudo ./install.sh
```

The installer stages the new application under `/opt`, preserves the previous installation in a backup directory during replacement, installs the desktop entry, and leaves the user's configuration untouched. It deliberately does not require aria2 to be installed first; runtime environment validation belongs to Ashore itself. If aria2 is missing at launch, Ashore presents the platform-specific installation guidance and can recheck after the dependency is installed.

Linux size optimization must be validated on both X11 and Wayland. Do not remove XCB, Wayland, platform input contexts, GTK/desktop-portal integration, SVG support, Qt Network/WebSockets, or ICU merely to reduce package size.

## macOS

Supported build modes:

```bash
python make.py app
python make.py dmg
```

The macOS build injects protocol and torrent-document associations from `packaging/Info.plist` and uses the application version from `core/applicationInfo.py`. Release dependencies pin PyQt6 6.8.1 and Qt 6.8.2; this combination has been validated on Intel macOS 12.7.6 with Python 3.10.2. Packaged GUI launches do not inherit the user's shell PATH reliably, so aria2 discovery checks PATH first and then common Homebrew (`/usr/local/bin`, `/opt/homebrew/bin`) and MacPorts (`/opt/local/bin`) locations. Linux and Windows also include common package-manager fallback locations.

The DMG contains `Ashore.app` and an `Applications` shortcut. macOS release artifacts are architecture-specific; build the Intel/x86_64 DMG on an Intel Mac and the ARM64 DMG on an Apple Silicon runner or machine.

## Windows

Windows supports a portable onefile build:

```bash
python make.py onefile
```

Output:

- `dist/Ashore.Windows.onefile/Ashore.exe`
- `dist/Ashore.Windows.onefile/icon.png`

This is intentionally a portable release rather than a formal installer. A Windows installer and system-level protocol/file-association installation should be added only after those behaviours have been validated on a physical Windows system.

## Release validation

Before publishing a release:

1. Confirm the version in `core/applicationInfo.py` and `pyproject.toml` matches.
2. Run the full unit-test suite and static checks.
3. Confirm CI is green on Linux, Windows, and macOS.
4. Build the platform artifact on the target platform.
5. Start the packaged application, verify normal exit, and exercise window move/resize.
6. Verify URL/magnet and `.torrent` routing where supported.
7. Verify the missing-aria2 startup guidance on a clean system or equivalent environment.
8. Perform at least one real aria2 download.
9. Verify download-complete/error notifications open Ashore and route to the downloaded-task view.
10. Verify settings persist across restart.
11. Verify external RPC remains disabled by default.
12. On Linux, validate the packaged build on both X11 and Wayland and confirm Qt reports no missing/unloadable required plugins.
13. Verify the release package contains no development-only files or credentials.

The release-build workflow creates native Linux, macOS, and Windows artifacts on GitHub-hosted runners and uploads them to the workflow run. It does not publish a GitHub Release automatically.
