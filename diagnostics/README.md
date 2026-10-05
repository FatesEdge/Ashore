# Cursor probe

`cursorProbe.py` builds a cumulative subset of Ashore with current production
components. It is a manual desktop-integration diagnostic, not an alternative
application entry point.

List stages:

```bash
python diagnostics/cursorProbe.py --list
```

Run a stage natively or through XWayland:

```bash
python diagnostics/cursorProbe.py --stage tray
QT_QPA_PLATFORM=xcb python diagnostics/cursorProbe.py --stage tray
```

At stages before `tray`, observe startup and close the window normally. Starting
at `tray`, close the window, reopen it from the tray, then choose **Quit probe**.
The three tray boundary stages differ only in teardown:

- `tray`: quit without explicitly hiding either object;
- `trayWindowHide`: hide the main window first;
- `trayIconHide`: also hide the tray icon first, matching Ashore's current path.

The stages are cumulative. Start with `base`, `tray`, and `startupWindow`. If two
adjacent observations differ, use the stages between them to find the first
component that changes cursor behavior. Confirm the boundary in both directions:
the lower stage must remain clean and the first failing stage must reproduce.
