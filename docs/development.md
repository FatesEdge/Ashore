# Development

## Environment

Ashore requires Python 3.12 or newer.

Create an isolated environment and install development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, use the corresponding virtual-environment activation command.

aria2 must also be installed and available to Ashore for normal runtime testing.

## Run

```bash
python Ashore.py
```

## Checks

Before merging changes, run:

```bash
python -m compileall -q Ashore.py paths.py make.py core interface
python -m pyflakes Ashore.py paths.py make.py core interface tests
python -m unittest discover -s tests -v
```

CI runs these checks on Ubuntu, Windows, and macOS. Linux additionally builds the onefile package and runs a packaged-GUI smoke test.

## Design rules

Ashore favours direct, maintainable structure over compatibility scaffolding.

- Use camelCase for project-defined Python identifiers where consistent with the surrounding code.
- Do not preserve obsolete APIs merely because they previously existed.
- Do not stack special-case patches over a flawed design. If a lifecycle or ownership model is wrong, correct the model.
- Keep `core/` focused on application logic and services.
- Keep `interface/` focused on PyQt6 presentation and interaction.
- Prefer Qt-native cross-platform behaviour when it is sufficiently reliable.
- Add platform-specific code only when behaviour genuinely differs.
- Keep user configuration outside the repository/source tree.
- Avoid network access in unit tests unless the test explicitly targets networking.
- New UI behaviour should remain usable in all three supported languages.

## UI lifecycle

Frameless-window behaviour is scoped to the main window. Do not install application-global event filters for window resize/move logic.

When creating QObject workers, make ownership explicit and stop asynchronous activity before the owner is destroyed.

Shutdown-related changes should be tested through an actual application start and exit, not only through isolated unit tests.

## Testing changes that affect startup or shutdown

For lifecycle changes, use Python's faulthandler when manually validating:

```bash
PYTHONFAULTHANDLER=1 python Ashore.py
```

A clean exit should return to the shell without a segmentation fault, abort, or unexpected Qt teardown warnings caused by Ashore ownership mistakes.

## Git workflow

Substantial refactors should be made on a feature branch and validated before merging into `main`.

Generated `build/` and `dist/` directories are ignored and must not be committed.
