# Packaging

Ashore uses PyInstaller through `make.py`.

The build script keeps a reviewed `PYINSTALLER_EXCLUDES` list for large optional Python/Qt modules that Ashore does not use. Required Qt modules such as Core, Gui, Widgets, Network, Svg, and WebSockets must never be added to that list. Linux builds also request binary stripping to reduce the shipped Qt/Python footprint.

PyInstaller module exclusions apply to Python import modules. They are not a reliable way to remove arbitrary shared libraries such as `libssl` or `libcrypto`; native libraries should only be removed when their dependency relationship has been verified.

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

## macOS

Supported build modes:

```bash
python make.py app
python make.py dmg
```

The macOS build injects protocol and torrent-document associations from `packaging/Info.plist` and uses the application version from `core/applicationInfo.py`.

The DMG contains `Ashore.app` and an `Applications` shortcut.

## Windows

Windows application logic is covered by CI, but there is currently no formal Windows packaging target in `make.py`.

A Windows installer should be added only after the packaging format and protocol/file-association behaviour have been validated on a physical Windows system.

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
9. Verify settings persist across restart.
10. Verify external RPC remains disabled by default.
11. Verify the release package contains no development-only files or credentials.

CI does not publish GitHub Releases automatically.
