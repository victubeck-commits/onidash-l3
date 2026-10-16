# OniDash L3

OniDash L3 is a Windows helper for Xbox controllers. It detects a quick double tap of the left analog stick (or configurable button presses) and automatically simulates a Left Stick Click (LS/L3), used in games like **Onimusha: Way of the Sword** to sprint.

## Why this project

Running in games like Onimusha can rely on double-tapping the left stick or pressing LS/L3. On real controllers, this detection can feel unreliable or uncomfortable. This tool creates a virtual Xbox controller and injects the LS at the right moment without interfering with normal movement.

## Features

- Real-time reading of the real Xbox controller via XInput.
- Virtual Xbox controller via ViGEmBus/vgamepad.
- Mirroring of all axes and buttons to the virtual controller.
- Automatic detection of the real controller slot ("Automatic" option), with manual choice from 0 to 3.
- Visual mapping editor: pick the physical input (with a "Detect input" button that reads the press for you), the target action and the activation mode using selectors only - no code to type.
- Activation modes: Hold, Single tap, Toggle, Repeat and Analog threshold.
- Repeat Nx per activation (e.g. exactly 3 times per tap), with interval, press duration and an optional continuous repeat (off by default).
- Activation conditions: direct, analog threshold or quick tap sequence (e.g. double-push of the LS), with an optional modifier input (e.g. LB).
- "Test mapping" button sends the sequence to the virtual controller before saving.
- List with a readable summary (e.g. `LS to B · Repeat 3x · Interval 300 ms`), double-click to edit, duplicate, enable/disable and remove.
- Conflict warning between mappings before saving.
- Automatic migration of old settings, without discarding data.
- Dark/gold UI, icon, real-time status and LS indicator.
- Optional HidHide support to hide the real controller while running, making the virtual one primary.
- Languages: Portuguese, English, Spanish.

## Requirements

- Windows 10/11.
- Xbox controller (USB recommended).
- ViGEmBus Driver 1.22 or newer.
- XInput (included with Windows).
- To run the script: Python 3.10+ with `XInput-Python` and `vgamepad`.
- Optional: HidHide.

## How to use (script)

```bat
cd %USERPROFILE%\Documents\XboxDashL3
pip install XInput-Python vgamepad
python xbox_dash_l3.py
```

## How to use (.exe)

Open `dist\OniDashL3\OniDashL3.exe` or the `OniDash L3` shortcut.

Steps:
1. Connect the Xbox controller via USB.
2. In Settings, pick the XInput slot of the controller (or leave it on "Automatic").
3. In Mapping, click "Add mapping".
4. Choose the input (or use "Detect input" and press it), the action, the mode and options.
5. Use "Test mapping" to check, then "Save".
6. In the game/Steam, choose the virtual controller if needed.

## HidHide (optional)

To make the virtual controller primary automatically:
1. Install HidHide: https://github.com/nefarius/HidHide/releases
2. Check "Use HidHide" in the app.
3. Restart the app.
4. Reconnect the controller USB.

## Limitations

- Some games read the physical controller (slot 0) before the virtual one. If the virtual does not respond, use HidHide, reconnect or change controller order.
- Double-tap detection depends on analog calibration; adjust threshold, hysteresis, interval and delays.
- HidHide is a third-party driver and may require a restart.
- The program does not replace or alter the real controller driver.

## Troubleshooting

- If "vgamepad unavailable" appears, install ViGEmBus and restart.
- False positives: raise the threshold and reduce the interval.
- Not detecting: lower the threshold and increase the interval; check the Y axis inversion option.
- Button presses not counted: fully release the button between taps.