import time
import csv
from datetime import datetime
from .xps_config import CONFIG, get_active_stages

def print_motion_format(stage_labels=None):
    if not stage_labels:
        stage_labels = get_active_stages()
    print("\n📘 Format Guide for motion.txt")
    print("Each line represents a configuration of positions for all stages.")
    print("Values must be comma-separated and match the number of stages.\n")
    print("# Example:")
    print("# " + ", ".join(stage_labels))
    print("30.0, 45.0, 90.0, 0.0, 180.0")
    print("10.0, 30.0, 60.0, 90.0, 120.0\n")

def load_position_combinations(filepath, stages):
    combos = []
    print(f"📄 Loading position combinations from '{filepath}' expecting {len(stages)} values per line...")
    try:
        with open(filepath, "r") as f:
            for lineno, line in enumerate(f, start=1):
                parts = line.strip().split(",")
                if len(parts) != len(stages):
                    print(f"⚠️ Line {lineno} skipped (expected {len(stages)} values): {line.strip()}")
                    continue
                try:
                    positions = [float(p) for p in parts]
                    combos.append(positions)
                except ValueError:
                    print(f"⚠️ Line {lineno} has invalid number(s): {line.strip()}")
    except Exception as e:
        print(f"❌ Error loading positions: {e}")
    return combos

def home_groups(xps, force_home=True, verbose=False):
    if verbose:
        print("🏠 Checking homing status...")
    status = xps.status_report()
    for group in CONFIG["GROUPS"]:
        line = next((l for l in status.splitlines() if l.startswith(f"{group} (")), None)
        if line and "Not referenced" in line:
            if force_home:
                if verbose:
                    print(f"➡ {group} is not referenced. Homing...")
                try:
                    xps.home_group(group)
                    if verbose:
                        print(f"✅ {group} homed.")
                except Exception as e:
                    print(f"❌ Failed to home {group}: {e}")
            else:
                if verbose:
                    print(f"⚠️ {group} not referenced. Auto-homing as required...")
                try:
                    xps.home_group(group)
                    if verbose:
                        print(f"✅ {group} auto-homed.")
                except Exception as e:
                    print(f"❌ Failed to auto-home {group}: {e}")
        else:
            if verbose:
                print(f"✅ {group} is already referenced.")

def all_groups_ready_and_enabled(xps):
    """
    Returns True if all groups are referenced and enabled, False otherwise.
    """
    status_lines = xps.status_report().splitlines()
    all_ready = True
    for group in CONFIG["GROUPS"]:
        for line in status_lines:
            if line.startswith(f"{group} ("):
                if not ("Referenced" in line and "Enabled" in line):
                    all_ready = False
                break
    return all_ready

def initialize_groups(xps, verbose=False):
    if verbose:
        print("⚙️ Initializing groups...")

    # Get current status report for all groups
    status_lines = xps.status_report().splitlines()
    for group in CONFIG["GROUPS"]:
        already_initialized = False
        # Search for group status in the report
        for line in status_lines:
             # Typical format: SP1 (ID 0): Ready from homing, Referenced, Enabled, ...
            if line.startswith(f"{group} ("):
                # Look for the "Referenced" or "Ready" keyword, meaning initialized
                if "Referenced" in line or "Ready" in line or "Enabled" in line:
                    already_initialized = True
                break
        if already_initialized:
            if verbose:
                print(f"ℹ️ {group} already initialized.")
            continue

        try:
            xps.initialize_group(group)
            if verbose:
                print(f"✅ {group} initialized.")
        except Exception as e:
            msg = str(e)
            # Only print unexpected errors; suppress 'Not allowed action'
            if "Not allowed action" in msg:
                if verbose:
                    print(f"ℹ️ {group} already initialized (from exception).")
            else:
                print(f"❌ Failed to initialize {group}: {e}")


def enable_groups(xps, verbose=False):
    if verbose:
        print("⚡ Enabling motion...")
    # Get current status report for all groups
    status_lines = xps.status_report().splitlines()

    for group in CONFIG["GROUPS"]:
        already_enabled = False
        for line in status_lines:
            if line.startswith(f"{group} ("):
                # Try to match both "Enabled" and common state names (for robustness)
                if "Enabled" in line:
                    already_enabled = True
                break
        if already_enabled:
            if verbose:
                print(f"ℹ️ {group} already enabled.")
            continue

        try:
            xps.enable_group(group)
            if verbose:
                print(f"✅ {group} motion enabled.")
        except Exception as e:
            msg = str(e)
            # Only print unexpected errors; suppress the known 'Not allowed action'
            if "Not allowed action" in msg:
                if verbose:
                    print(f"ℹ️ {group} already enabled (from exception).")
            else:
                print(f"❌ Enable error for {group}: {e}")

def reset_stages(xps, verbose=False):
    if verbose:
        print(f"🔁 Resetting active stages to {CONFIG['RESET_POSITION']}...")
    for stage in get_active_stages():
        try:
            pos = get_stage_position_with_offset(xps, stage)
            if pos is None:
                print(f"⚠️ Could not get position of {stage} to reset.")
                continue
            if abs(pos - CONFIG["RESET_POSITION"]) < CONFIG["POSITION_TOL"]:
                if verbose:
                    print(f"✅ {stage} already at {CONFIG['RESET_POSITION']:.2f}")
            else:
                if verbose:
                    print(f"➡ Moving {stage} to {CONFIG['RESET_POSITION']}...")
                move_stage_with_offset(xps, stage, CONFIG["RESET_POSITION"])
                if verbose:
                    print(f"✅ {stage} reset")
        except Exception as e:
            print(f"❌ Failed to reset {stage}: {e}")

def wait_until_reached(xps, targets):
    start_time = time.time()
    stages = get_active_stages()
    while time.time() - start_time < CONFIG["MAX_WAIT_TIME"]:
        all_reached = True
        for stage, target in zip(stages, targets):
            try:
                pos = get_stage_position_with_offset(stage)
                if pos is None or abs(pos - target) > CONFIG["POSITION_TOL"]:
                    all_reached = False
                    break
            except Exception:
                return False
        if all_reached:
            return True
        time.sleep(CONFIG["WAIT_DELAY"])
    return False

def wait_until_reached_blocking(xps, targets, stages=None, tolerance=None, poll_delay=None):
    from .xps_config import CONFIG, get_active_stages
    if stages is None:
        stages = get_active_stages()
    tol = tolerance if tolerance is not None else CONFIG["POSITION_TOL"]
    delay = poll_delay if poll_delay is not None else CONFIG["WAIT_DELAY"]
    while True:
        all_reached = True
        for stage, target in zip(stages, targets):
            try:
                pos = get_stage_position_with_offset(xps, stage)
                if pos is None or abs(pos - target) > tol:
                    all_reached = False
                    break
            except Exception:
                return False
        if all_reached:
            return True
        time.sleep(delay)

def execute_position_configurations(xps, combinations, log_file=None):
    stages = get_active_stages()
    for idx, positions in enumerate(combinations, start=1):
        print(f"\n➡ Moving to configuration {idx}: {positions}")
        for stage, pos in zip(stages, positions):
            try:
                move_stage_with_offset(xps, stage, pos)
            except Exception as e:
                print(f"❌ Error moving {stage}: {e}")

        success = wait_until_reached(xps, positions)
        status_line = " | ".join(f"{s}={p:.2f}" for s, p in zip(stages, positions))
        if success:
            print(f"✅ Reached: {status_line}")
            if log_file:
                append_to_log(log_file, positions)
        else:
            print(f"⚠️ Timeout: {status_line}")

def append_to_log(filename, positions):
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat()] + positions)
    except Exception as e:
        print(f"❌ Failed to write to log: {e}")

# ------------------------
# New helper functions to apply zero offset transparently

def move_stage_with_offset(xps, stage, position):
    """
    Move a stage to a position relative to its zero offset.
    Sends the position + zero_offset to the hardware.
    """
    zero_offset = CONFIG["ZERO_OFFSETS"].get(stage, 0.0)
    target = position + zero_offset
    xps.move_stage(stage, target)

def get_stage_position_with_offset(xps, stage):
    """
    Get the current position of a stage relative to its zero offset.
    Returns hardware position minus zero offset.
    """
    zero_offset = CONFIG["ZERO_OFFSETS"].get(stage, 0.0)
    pos_hw = xps.get_stage_position(stage)
    if pos_hw is None:
        return None
    return pos_hw - zero_offset