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

## Formal startup probe

`startupProbe.py` follows the real startup path and adds one group at a time:

```bash
python diagnostics/startupProbe.py --list
python diagnostics/startupProbe.py --stage base
python diagnostics/startupProbe.py --stage ariaStartup
python diagnostics/startupProbe.py --stage windowBase
python diagnostics/startupProbe.py --stage windowFrame
python diagnostics/startupProbe.py --stage windowControlsPlain
python diagnostics/startupProbe.py --stage windowSingleIcon
python diagnostics/startupProbe.py --stage windowSingleIcon --single-icon add.png
python diagnostics/startupProbe.py --stage windowSingleIcon --single-icon add.png --icon-mode preloaded
python diagnostics/startupProbe.py --stage windowFirstTwoIcons
python diagnostics/startupProbe.py --stage windowNavigationIcons
python diagnostics/startupProbe.py --stage windowControls
python diagnostics/startupProbe.py --stage windowContent
python diagnostics/startupProbe.py --stage windowMenus
python diagnostics/startupProbe.py --stage windowStatus
python diagnostics/startupProbe.py --stage windowTray
python diagnostics/startupProbe.py --stage windowSignals
python diagnostics/startupProbe.py --stage mainWindow
python diagnostics/startupProbe.py --stage tray
```

Compare the lowest clean stage with the first stage that produces the busy
cursor. Use Ctrl+C in the terminal to close stages before `windowTray`; those
stages intentionally omit the production quit action and tray object. From
`windowTray` onward, Ctrl+Q and the tray exit path are available.
