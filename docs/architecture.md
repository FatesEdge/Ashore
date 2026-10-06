# Architecture

Ashore is intentionally split into a small bootstrap layer, application/runtime services, and the PyQt6 interface.

## Runtime flow

`Ashore.py` creates the application object, configures startup, and enters the Qt event loop. Startup orchestration lives in `core/applicationRuntime.py`, which is responsible for single-instance routing, configuration loading, aria2 startup checks, splash/recovery windows, main-window creation, and deterministic teardown before Python interpreter shutdown.

The main window itself lives in `interface/mainWindow.py`.

## Core layer

The `core/` package contains logic that should not depend on a particular page layout.

- `applicationInfo.py` — application identity and version
- `applicationRuntime.py` — startup, single-instance routing, and shutdown coordination
- `aria2Client.py` — lightweight aria2 JSON-RPC client
- `aria2Service.py` — aria2 process lifecycle, polling, startup, restart, removal, and shutdown workers
- `aria2Events.py` — WebSocket notifications and reconnect behaviour
- `configStore.py` — configuration reading and atomic persistence
- `downloadRequest.py` — normalisation of URLs, magnet links, and torrent inputs
- `environmentCheck.py` — environment validation and recovery information
- `fileOperations.py` — local file deletion and reveal/open integration
- `formatters.py` — display formatting helpers
- `missionNames.py` — persistent learned task names
- `singleInstance.py` — primary/secondary instance coordination
- `trackerHealth.py` — Tracker reachability/latency probing
- `trackerManager.py` — Tracker state and persistence
- `trackerSources.py` — built-in/custom Tracker source loading and merge logic

## Interface layer

The `interface/` package contains PyQt6 presentation and interaction code.

The current window uses a custom frameless title bar. `WindowChrome` is owned by the Ashore main window and installs event filters only on that window's QWidget subtree. It deliberately does **not** install a global QApplication event filter. This keeps resize handling scoped to the window and avoids coupling window chrome lifetime to unrelated Qt objects such as sockets and WebSocket internals.

`TitleBar` delegates moving and resizing to the platform through QWindow operations rather than implementing geometry changes manually.

## aria2 state model

HTTP JSON-RPC is the authoritative task-state source.

WebSocket notifications do not replace polling. They only trigger prompt refreshes so the UI reacts quickly to aria2 events. Periodic polling remains responsible for progress synchronisation and recovery when WebSocket is unavailable.

Desktop completion/error notifications carry the task id back into the main window. Notification activation restores Ashore, routes outcome notifications to the downloaded-task page, and focuses the matching task when its card is already present.

## Ownership and shutdown

Qt/Python ownership is treated explicitly.

The startup controller owns the runtime references needed while the application is alive. Before Python interpreter finalisation, `StartupController.dispose()` breaks remaining Python/Qt reference chains and closes runtime objects in a defined order.

UI-owned workers are parented where practical. Long-running workers and timers are stopped before their owner is released.

## Language selection

The bundled default is `system`. On first use, Ashore maps the operating-system locale to Simplified Chinese, Traditional Chinese, or English. Unsupported system languages fall back to English. Once the user explicitly saves a language choice, that persisted setting takes precedence.

## Project boundaries

Ashore is not intended to become a browser, cloud service, plugin marketplace, or general automation platform. New features should directly improve download management, aria2 operation, or desktop integration.

When a design can be simplified by replacing an old path, prefer replacement over retaining obsolete compatibility layers.
