# RPC and Security

Ashore controls aria2 through JSON-RPC.

## Default behaviour

External RPC access is disabled by default.

Ashore is designed so that normal desktop use does not require exposing aria2 RPC to the local network. The default configuration binds RPC locally.

## Enabling external access

External access must be enabled explicitly in Settings.

When enabled, Ashore creates the required authorization token and exposes it in the UI as a read-only value for copying. The token is not intended to be edited manually through the Ashore interface.

Treat this token as a credential. Do not publish it in screenshots, logs, bug reports, or repository files.

## Port changes

Ashore can optionally allow RPC-port modification. Port editing is locked unless that option is enabled.

When settings require aria2 to restart, Ashore attempts a controlled shutdown through the current RPC connection before starting aria2 with the new configuration. If the running process cannot be stopped safely, the configuration is retained and the user is told that a manual restart is required.

## HTTP and WebSocket roles

Ashore uses two related channels:

- HTTP JSON-RPC — authoritative state and commands
- WebSocket JSON-RPC — event notifications that trigger immediate refreshes

If WebSocket is unavailable, polling continues to keep the task list synchronised.

## Network exposure

Enabling external RPC increases attack surface. Only expose it on networks you trust, protect the token, and use host/firewall controls appropriate to the environment.

Ashore does not attempt to turn raw aria2 RPC into an internet-facing service.
