# NewportXPS Control Library

This library provides a command-line tool and programmatic interface for controlling motion stages using a Newport XPS motion controller.

- **Supports:** Multi-axis motion, calibration, automation, and safe group control.
- **CLI:** User-friendly for routine operation and calibration.
- **API:** Ready for scripting, Jupyter, or integration with other projects.

---

## 📦 Structure Overview

```
project_root/
├── newportxps_control.py            # CLI entry point
├── config/
│   ├── xps_connection_parameters.json # Required credentials
│   └── xps_hardware.json              # Hardware/stage info & zero offsets
├── motion.txt                       # Example motion sequence file
├── newportxpslib/
│   ├── __init__.py
│   ├── controller_interface.py      # API helpers for scripting
│   ├── xps_config.py                # Config handling
│   ├── xps_motion.py                # Stage/group utilities
│   └── utils.py                     # CLI and API helpers (stage parsing, zero setting)
├── README.md
```

---

## ⚙️ Setup

### 1. Install required package
Make sure the `newportxps` driver library is installed (via pip or included locally).

### 2. Clone/copy this repository

### 3. Create your XPS credentials manually
Create `config/xps_connection_parameters.json`:
```json
{
  "ip": "YOUR_XPS_IP_ADDRESS",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```
If any field is left blank, the script will exit with a warning.

### 4. Generate hardware map from controller
You must run this step at least once for each new controller or after any hardware change:
```bash
python newportxps_control.py --generate-config
```
This queries the XPS and writes `config/xps_hardware.json`.

> ⚠️ **Note:** The hardware configuration retrieved by `--generate-config` reflects the current system setup in your XPS controller — this includes group and stage assignments configured through the **XPS web interface** (not via this library). You must rerun this step anytime new stages are connected or the XPS configuration changes. 

---

## **CLI Usage**

Run all commands from your project root.


### **1. Calibrate user zero (after homing and moving to your desired zero):**
```bash
python newportxps_control.py --set-zero
```
- Or for specific axes:
    ```bash
    python newportxps_control.py --set-zero --stages "1,3"
    ```

### **2 Home all axes:**
```bash
python newportxps_control.py --home
```

### **3. Move axes from a motion file:**
```bash
python newportxps_control.py --file motion.txt
```

### **4. Print current positions:**
```bash
python newportxps_control.py --get-positions
```
- Or for specific stages:
    ```bash
    python newportxps_control.py --get-positions --stages "Group2.Pos,Group4.Pos"
    ```

### **5. Other useful flags:**
- `--backup` — Download controller config backup and exit.
- `--loop` — Loop through motion.txt forever (Ctrl+C to stop).
- `--log` — Log positions to CSV during motion.
- `--reset` — Reset all stages to the configured zero position.
- `--format-guide` — Print motion.txt file format help.

---

## **Motion File Example (`motion.txt`)**

Each line specifies positions for each selected stage, **optionally followed by a label** (e.g., for logging or tracking):

```
10, 0, 90, 5, first_move
20, 5, 45, 0
```
- **Positions:** The first N values (comma-separated) are the target positions for each active stage.
- **Label (optional):** Anything after the last numeric value is treated as a label/comment and will be logged if `--log` is used.
---

## 🧠 Python API Usage

### **From a fresh system (stages disabled/not referenced):**

```python
from newportxpslib.controller_interface import move_motors, get_positions
from newportxpslib.xps_motion import initialize_groups, home_groups
from newportxpslib.xps_config import load_full_config, load_user_credentials, CONFIG
from newportxps import NewportXPS

# 1. Always load credentials and config first
load_user_credentials()
load_full_config()

# 2. Connect to XPS controller
xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])

# 3. Prepare hardware (initialize and home all groups ONCE after power up)
initialize_groups(xps)
home_groups(xps, force_home=True)

# 4. Now you can use high-level API for moves (no extra prep needed)
# Example: Move motors 1 and 3 to 10 and 90
move_motors(10, 90, stages=[1, 3], skip_prep=True)

# 5. Get positions
positions = get_positions(stages=[1, 3])
print(positions)  # {'SP1.Pos1': 10.0, 'SP3.Pos3': 90.0}
```

*You only need to run `initialize_groups` and `home_groups` once after every reboot or power-up! After that, you can call `move_motors(..., skip_prep=True)` repeatedly for fast, safe operation.*

---

### **Set user zero offset from Python:**

```python
from newportxpslib.utils import set_zero_for_stages
set_zero_for_stages(['SP1.Pos1', 'SP3.Pos3'])
```
---

## **Zero Offset: What is it?**

- After homing, the physical zero might not be exactly 0.0.
- Use `--set-zero` to define *your* logical zero wherever you want (e.g., at a calibration marker).
- The library will always handle the offset so you command moves and read positions **relative to your zero**.

---

## **Tips and Best Practices**

- Run `--generate-config` and `--home` after every controller reboot.
- Calibrate zero after mechanical adjustment or reassembly.
- Use `--loop` only for automated, supervised experiments.
- The code is **idempotent**: you can set zero as often as you want with no drift.

---

## 🛡️ Safety & Validation
- If `xps_connection_parameters.json` is missing or incomplete → script exits safely
- If `xps_hardware.json` is missing → instructs you to run `--generate-config`
- If number of values in `motion.txt` mismatches number of stages → line is skipped

---

## **Troubleshooting**

- **XPSError: Not allowed action** — The controller or group is already enabled/homed; ignore if expected.
- **Positions not matching commands?** — Check and (re)set zero offsets!
- **Timeout waiting for move?** — Increase your motion tolerance in config, or check for physical interlock.

---
## 📬 Author
Maintained by Pablo Palacios. Contributions welcome!

