# Ashore

<p align="center">
  <img src="static/icon/functionIcons/appIcon.png" width="96" alt="Ashore icon">
</p>

<p align="center">
  A focused cross-platform desktop download manager powered by aria2 and PyQt6.
</p>

<p align="center">
  <a href="README.CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/PyQt-6-green" alt="PyQt6">
  <img src="https://img.shields.io/badge/license-MPL--2.0-blue" alt="MPL-2.0">
</p>

## Overview

Ashore is a native-feeling desktop front end for [aria2](https://github.com/aria2/aria2). It keeps the product scope deliberately narrow: managing downloads well, exposing the aria2 features that matter in day-to-day use, and behaving consistently across desktop platforms.

The application uses aria2 JSON-RPC for authoritative task state and WebSocket notifications for prompt refreshes. It also provides task naming persistence, Tracker source management and health checks, system notifications, theme support, single-instance routing, and desktop protocol/file integration.

## Highlights

- HTTP, HTTPS, FTP, BitTorrent, magnet links, and local `.torrent` files through aria2
- Compact PyQt6 desktop interface with light, dark, and system themes
- Download state, speed, aria2 connection state, and task actions in one window
- WebSocket notifications for immediate refresh with HTTP polling as the authoritative fallback
- Multi-source BT Tracker lists with merge, deduplication, manual editing, and reachability/latency checks
- Local-only RPC by default, with an explicit external-access switch and generated read-only token display
- Download-complete/error system notifications
- Persistent learned task names
- Single-instance handling for URLs, magnet links, and `.torrent` files
- Simplified Chinese, Traditional Chinese, and English UI support; first launch follows the supported system language and otherwise defaults to English
- Linux, macOS, and Windows code paths covered by CI

## Platform status

| Platform | Status |
| --- | --- |
| Linux | Primary development and manual validation platform |
| macOS | Supported in code and packaging; Intel macOS 12.7.6 is validated with PyQt6 6.8.1 / Qt 6.8.2, and Apple Silicon DMG builds are covered by CI |
| Windows | Supported in code, CI, and portable onefile packaging; a formal installer still needs physical-machine validation |

Ashore requires **Python 3.10+** when run from source and a working **aria2** installation for downloads. Packaged Ashore can be installed before aria2; if aria2 is missing at launch, Ashore shows platform-specific installation guidance.

## Installation

Prebuilt release artifacts should be preferred once a release is available. See the repository [Releases](https://github.com/Kai-x64/Ashore/releases) page.

### Linux

Unpack the Ashore Linux release package, then run:

```bash
sudo ./install.sh
```

The installer places Ashore under `/opt/Ashore` and the desktop entry under `/usr/local/share/applications/ashore.desktop`. User configuration remains in `~/.config/ashore/` or the directory selected by `XDG_CONFIG_HOME`.

If aria2 is not installed when Ashore starts, the application reports the missing dependency and shows the recommended installation command for the current system. After installing aria2, use the recheck action to continue.

### macOS

Install aria2 first. For a packaged release, use the DMG matching your Mac architecture and move `Ashore.app` to `Applications`. Ashore pins PyQt6 6.8.1 with Qt 6.8.2 so Intel macOS 12 remains supported.

### Windows

Windows releases include a portable `Ashore.exe` build. A formal installer and system-wide protocol/file association installer are intentionally deferred until they have been validated on a physical Windows machine.

## Run from source

```bash
git clone https://github.com/Kai-x64/Ashore.git
cd Ashore

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

python Ashore.py
```

On Windows, activate the virtual environment with the platform-appropriate command.

## Configuration and RPC

Ashore stores user configuration outside the source tree. RPC is local-only by default. External RPC access must be enabled explicitly in Settings; Ashore then generates and displays the authorization token as read-only UI.

The application shows the effective HTTP polling address, WebSocket notification address, connection state, and aria2 version. HTTP remains the authoritative source for task state; WebSocket is used to trigger prompt refreshes.

See [RPC and security](docs/rpc.md) for details.

## Tracker management

Ashore can combine multiple Tracker sources, remove duplicates, preserve the last successful list on failures, and test individual endpoints concurrently. Automatic refresh is optional and uses the last successful update time rather than refreshing on every launch.

## Development

Install development dependencies with:

```bash
python -m pip install -e ".[dev]"
```

Run the same core checks used by CI:

```bash
python -m compileall -q Ashore.py paths.py make.py core interface
python -m pyflakes Ashore.py paths.py make.py core interface tests
python -m unittest discover -s tests -v
```

The repository intentionally keeps application logic separated from UI code:

- `Ashore.py` — application bootstrap
- `core/` — aria2 integration, lifecycle, configuration, trackers, requests, and platform-independent services
- `interface/` — PyQt6 windows, pages, controls, themes, notifications, and window chrome
- `packaging/` — desktop packaging metadata and Linux installer
- `tests/` — unit, UI-structure, platform-behaviour, and packaging tests

More detail is available in [Architecture](docs/architecture.md) and [Development](docs/development.md).

## Packaging

Linux supports both PyInstaller `onefile` and `onedir` builds. macOS supports `.app` and DMG output. Windows supports a portable PyInstaller `onefile` build.

```bash
python make.py onefile   # Linux
python make.py onedir    # Linux
python make.py app       # macOS
python make.py dmg       # macOS
python make.py onefile   # Windows
```

See [Packaging](docs/packaging.md) for the release layout and validation notes.

## Roadmap

Ashore will continue to focus on being a small, dependable aria2 desktop manager rather than growing into a plugin or service ecosystem. Longer-term ideas, including a possible C++/Qt rewrite, are recorded in [Roadmap](docs/roadmap.md).

## License

Ashore is licensed under the [Mozilla Public License 2.0](LICENSE).
