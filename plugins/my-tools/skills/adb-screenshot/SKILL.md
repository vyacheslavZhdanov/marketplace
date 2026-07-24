---
name: adb-screenshot
description: Use when user asks to take a screenshot from an Android device or emulator, capture screen, make screenshot via ADB, or save screen state for debugging/review
---

# ADB Screenshot

## Overview

Capture a screenshot from a connected Android device or emulator via ADB. Saves to the `screenshots/` folder in the project root with a timestamp and device name in the filename.

## Steps

### 1. Get connected devices

```bash
adb devices
```

Parse output — skip the first line ("List of devices attached") and any empty lines. Extract device IDs (serial numbers) with status `device`.

### 2. Select device

- **0 devices** — tell the user no devices are connected and stop.
- **1 device** — use it automatically, no need to ask.
- **2+ devices** — use the `AskUserQuestion` tool to show a picker. Build `options` from the device list (up to 4 options; if there are more than 4 devices, fall back to a numbered text list). Example:

```
AskUserQuestion(
  questions: [{
    question: "Which device should I take a screenshot from?",
    header: "Device",
    multiSelect: false,
    options: [
      { label: "emulator-5554", description: "Android Emulator" },
      { label: "emulator-5556", description: "Android Emulator" },
      { label: "R3CN90XXXXX",   description: "Physical device" }
    ]
  }]
)
```

Wait for the user's selection before continuing.

### 3. Ensure screenshots folder exists

```bash
mkdir -p screenshots
```

### 4. Build filename

Format: `screenshots/{device_name}_{timestamp}.png`

- `device_name` — the serial from `adb devices` (colons replaced with underscores, e.g. `emulator-5554`)
- `timestamp` — current date and time: `YYYYMMDD_HHMMSS`

Example: `screenshots/emulator-5554_20260422_112233.png`

### 5. Capture and save

```bash
adb -s {device_serial} exec-out screencap -p > screenshots/{filename}
```

> **Important:** use `exec-out screencap -p` (not `shell screencap`). This avoids Windows path expansion issues and pipes the PNG directly without writing to the device's SD card.

### 6. Display the screenshot

After saving, read the file with the `Read` tool so the image is shown inline in the conversation:

```
Read(file_path="<absolute_path_to_screenshot>")
```

Then report the saved path to the user.

## Quick Reference

| Situation                               | Action                              |
|-----------------------------------------|-------------------------------------|
| No devices                              | Stop, tell user                     |
| Single device                           | Use automatically                   |
| Multiple devices                        | Ask user to choose                  |
| Filename collision                      | Timestamp prevents this             |
| `shell screencap` path error on Windows | Use `exec-out screencap -p` instead |

## Common Mistakes

- **Using `shell screencap /sdcard/...`** — on Windows, Git Bash expands `/sdcard/` to `C:/Program Files/Git/sdcard/`. Use `exec-out screencap -p >` instead.
- **Forgetting `mkdir -p screenshots`** — redirect will fail if the folder doesn't exist.
- **Not showing the image** — always call `Read` on the saved file so the user sees the screenshot inline.