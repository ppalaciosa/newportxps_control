# NewportXPS Control Library

This library provides a command-line tool and programmatic interface for controlling motion stages using a Newport XPS motion controller.

---

## 📦 Structure Overview

```
project_root/
├── newportxps_control.py               # Command-line entry point
├── config/
│   ├── xps_connection_parameters.json  # Required credentials
│   └── xps_hardware.json               # Auto-generated stage/group info
├── newportxpslib/                      # Core reusable motion library
│   ├── __init__.py                     # Exposes top-level API
│   ├── controller_interface.py         # move_motors(), get_positions(), etc.
│   ├── xps_config.py                   # Config handling
│   └── xps_motion.py                   # Group and stage utilities
├── motion.txt                          # Example motion list
└── README.md
```

---

## ⚙️ Setup

### 1. Install required package
Make sure the `newportxps` driver library is installed (via pip or included locally).

### 2. Create your XPS credentials manually
Create `config/xps_connection_parameters.json`:
```json
{
  "ip": "YOUR_XPS_IP_ADDRESS",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```
If any field is left blank, the script will exit with a warning.

### 3. Generate hardware map from controller
```bash
python newportxps_control.py --generate-config
```
This queries the XPS and writes `config/xps_hardware.json`.

> ⚠️ **Note:** The hardware configuration retrieved by `--generate-config` reflects the current system setup in your XPS controller — this includes group and stage assignments configured through the **XPS web interface** (not via this library). You must rerun this step anytime new stages are connected or the XPS configuration changes. 

---

## 🚀 CLI Usage

### Move through a list of positions:
```bash
python newportxps_control.py --file motion.txt
```

### Only home (and then exit):
```bash
python newportxps_control.py --home
```

### Loop through motions indefinitely:
```bash
python newportxps_control.py --file motion.txt --loop
```

### Back up XPS configuration:
```bash
python newportxps_control.py --backup
```

### Reset all axes to initial position:
```bash
python newportxps_control.py --reset
```

### Show expected format of motion.txt:
```bash
python newportxps_control.py --format-guide
```

---

## 🧠 Python API Usage

Use the library programmatically:

```python
from newportxpslib import move_motors, get_positions, get_status

move_motors(0, 10, 90, 5, 180)
print(get_positions())
print(get_status())
```

You can also import specific stage utility functions from:
```python
from newportxpslib.xps_motion import home_groups, reset_stages
```

---

## 🛡️ Safety & Validation
- If `xps_connection_parameters.json` is missing or incomplete → script exits safely
- If `xps_hardware.json` is missing → instructs you to run `--generate-config`
- If number of values in `motion.txt` mismatches number of stages → line is skipped

---


## 📬 Author
Maintained by Pablo Palacios. Contributions welcome!

