# Roadmap

This file records direction rather than promises or release dates.

## Near-term direction

Ashore should remain a focused desktop download manager around aria2.

Priorities include:

- stable behaviour across Linux, macOS, and Windows
- reliable packaging and desktop integration
- clear download/task state
- robust Tracker management
- predictable startup and shutdown
- restrained, consistent UI design
- maintaining Simplified Chinese, Traditional Chinese, and English support

Features that would push Ashore toward a plugin marketplace, cloud platform, browser, or broad automation ecosystem are intentionally out of scope unless the product direction changes.

## Packaging

Linux packaging is established. macOS packaging exists and should continue to receive real-device validation. Windows packaging remains a future release task.

## Possible C++ / Qt rewrite

A future reimplementation of Ashore in **C++ with Qt** is an idea worth exploring.

This is **not a current migration plan** and does not mean the Python/PyQt6 codebase is scheduled for replacement. It is recorded as a longer-term technical experiment that may become attractive if Ashore eventually benefits from:

- a smaller or more predictable deployment/runtime footprint
- tighter control over native Qt object lifetime
- simpler native packaging on desktop systems
- reduced Python/PyInstaller distribution overhead
- deeper platform integration

Any rewrite should first preserve the behaviour and product boundaries established by the current Ashore implementation. It should not be undertaken merely for language preference, and it should not block maintenance of the working Python version.

If explored, the sensible first step would be a small C++/Qt prototype of application startup, aria2 RPC communication, the task list, and the custom window shell before deciding whether a full rewrite is justified.
