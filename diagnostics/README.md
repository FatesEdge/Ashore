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

If all three stages spin on exit, keep the stage at `tray` and compare the
delay between closing the tray menu and quitting the application:

```bash
python diagnostics/cursorProbe.py --stage tray --tray-quit-delay 250
python diagnostics/cursorProbe.py --stage tray --tray-quit-delay 1000
python diagnostics/cursorProbe.py --stage tray --tray-quit-delay 3000
```

The terminal prints once when the tray action arrives and again immediately
before `app.quit()`. Note whether the busy cursor starts before or after the
second message.

If the cursor starts spinning as soon as the action arrives, compare a tray
action that performs no exit with one that explicitly activates the main
window before exiting:

```bash
python diagnostics/cursorProbe.py --stage tray --tray-action observe
python diagnostics/cursorProbe.py --stage tray --tray-action activate --tray-quit-delay 3000
```

For `observe`, leave the main window open, choose **Observe action only**, and
then use Ctrl+Q after observing the cursor. For `activate`, close the main
window first and choose **Activate then quit**; the window should reappear and
the process exits three seconds later.

If activation prevents the busy cursor with a delay but not at zero
milliseconds, wait for actual window activation and painting instead of using a
fixed delay:

```bash
python diagnostics/cursorProbe.py --stage tray --tray-action windowReady
```

Close the main window first, then choose **Wait for window then quit**. The
terminal reports both window events before the application exits.

The stages are cumulative. Start with `base`, `tray`, and `startupWindow`. If two
adjacent observations differ, use the stages between them to find the first
component that changes cursor behavior. Confirm the boundary in both directions:
the lower stage must remain clean and the first failing stage must reproduce.

## Startup handoff comparison

Run the normal startup path first, then compare it with a handoff that keeps
the startup window visible until the main window is activated and painted:

```bash
ASHORE_STARTUP_TRACE=1 python Ashore.py
ASHORE_STARTUP_TRACE=1 ASHORE_STARTUP_HANDOFF=windowReady python Ashore.py
```

`ASHORE_STARTUP_HANDOFF` is a temporary diagnostic switch. It does not change
the default startup path and should be removed after the Wayland comparison is
complete.
