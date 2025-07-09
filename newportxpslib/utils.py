"""
utils.py

Utility functions for Newport XPS CLI/API.

- Stage parsing from CLI args (names or 1-based indices)
- Setting zero offsets after user calibration

No direct device control logic here!
"""

import json
from newportxpslib.xps_config import CONFIG, load_full_config
from newportxps import NewportXPS

def parse_stages_arg(stages_arg):
    """
    Parse a --stages argument into a list of stage names.
    Supports names or 1-based indices (for CLI or scripting).

    Args:
        stages_arg: Comma-separated string (e.g. "1,3" or "SP1.Pos1,SP3.Pos3")
    Returns:
        List of stage names (as in CONFIG["STAGES"])
    """
    if not stages_arg:
        return CONFIG["STAGES"]
    stage_list = []
    if all(s.strip().isdigit() for s in stages_arg.split(',')):
        # By index (1-based)
        indices = [int(s.strip())-1 for s in stages_arg.split(',')]
        for i in indices:
            if i < 0 or i >= len(CONFIG["STAGES"]):
                raise ValueError(f"Stage index {i+1} out of range.")
            stage_list.append(CONFIG["STAGES"][i])
    else:
        # By name
        for s in stages_arg.split(','):
            s = s.strip()
            if s not in CONFIG["STAGES"]:
                raise ValueError(f"Stage name '{s}' not found.")
            stage_list.append(s)
    return stage_list

def set_zero_for_stages(selected_stages=None):
    """
    Set the current position of all (or selected) stages as their new zero offset in xps_hardware.json.

    Args:
        selected_stages: List of stage names (default: all stages in config)

    Usage:
        set_zero_for_stages(["SP1.Pos1", "SP3.Pos3"])
        # or (in CLI)
        python newportxps_control.py --set-zero --stages "1,3"
    """

    load_full_config(verbose=True)
    stages = selected_stages or CONFIG["STAGES"]

    print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']} to set zero offset(s)...")
    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])

    zero_offsets = {}
    for stage in stages:
        pos = xps.get_stage_position(stage)
        print(f"  {stage}: Current position {pos:.6f} set as new zero.")
        zero_offsets[stage] = pos

    hwfile = "config/xps_hardware.json"
    with open(hwfile, "r") as f:
        hw = json.load(f)
    hw["zero_offsets"] = hw.get("zero_offsets", {})
    hw["zero_offsets"].update(zero_offsets)
    with open(hwfile, "w") as f:
        json.dump(hw, f, indent=4)
    print(f"✅ Zero offsets updated in {hwfile}.")

    try:
        xps.ftpconn.close()
    except Exception:
        pass
