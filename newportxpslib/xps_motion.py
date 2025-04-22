import time
import csv
from datetime import datetime
from .xps_config import CONFIG

def print_motion_format(stage_labels=None):
    if not stage_labels:
        stage_labels = CONFIG.get("LABELS", ["Stage1", "Stage2"])
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

def initialize_groups(xps):
    print("⚙️ Initializing groups...")
    for group in CONFIG["GROUPS"]:
        try:
            xps.initialize_group(group)
            print(f"✅ {group} initialized.")
        except Exception as e:
            if "Not allowed action" in str(e):
                print(f"ℹ️ {group} already initialized.")
            else:
                print(f"❌ Failed to initialize {group}: {e}")

def home_groups(xps, force_home=True):
    print("🏠 Checking homing status...")
    status = xps.status_report()
    for group in CONFIG["GROUPS"]:
        line = next((l for l in status.splitlines() if l.startswith(f"{group} (")), None)
        if line and "Not referenced" in line:
            if force_home:
                print(f"➡ {group} is not referenced. Homing...")
                try:
                    xps.home_group(group)
                    print(f"✅ {group} homed.")
                except Exception as e:
                    print(f"❌ Failed to home {group}: {e}")
            else:
                print(f"⚠️ {group} not referenced. Auto-homing as required...")
                try:
                    xps.home_group(group)
                    print(f"✅ {group} auto-homed.")
                except Exception as e:
                    print(f"❌ Failed to auto-home {group}: {e}")
        else:
            print(f"✅ {group} is already referenced.")

def enable_groups(xps):
    print("⚡ Enabling motion...")
    for group in CONFIG["GROUPS"]:
        try:
            xps.enable_group(group)
            print(f"✅ {group} motion enabled.")
        except Exception as e:
            if "Not allowed action" in str(e):
                print(f"ℹ️ {group} already enabled.")
            else:
                print(f"❌ Enable error for {group}: {e}")

def reset_stages(xps):
    print(f"🔁 Resetting all stages to {CONFIG['RESET_POSITION']}...")
    for stage in CONFIG["STAGES"]:
        try:
            pos = xps.get_stage_position(stage)
            if abs(pos - CONFIG["RESET_POSITION"]) < CONFIG["POSITION_TOL"]:
                print(f"✅ {stage} already at {CONFIG['RESET_POSITION']:.2f}")
            else:
                print(f"➡ Moving {stage} to {CONFIG['RESET_POSITION']}...")
                xps.move_stage(stage, CONFIG["RESET_POSITION"])
                print(f"✅ {stage} reset")
        except Exception as e:
            print(f"❌ Failed to reset {stage}: {e}")

def wait_until_reached(xps, targets):
    start_time = time.time()
    while time.time() - start_time < CONFIG["MAX_WAIT_TIME"]:
        all_reached = True
        for stage, target in zip(CONFIG["STAGES"], targets):
            try:
                pos = xps.get_stage_position(stage)
                if abs(pos - target) > CONFIG["POSITION_TOL"]:
                    all_reached = False
                    break
            except Exception:
                return False
        if all_reached:
            return True
        time.sleep(CONFIG["WAIT_DELAY"])
    return False

def execute_position_configurations(xps, combinations, log_file=None):
    for idx, positions in enumerate(combinations, start=1):
        print(f"\n➡ Moving to configuration {idx}: {positions}")
        for stage, pos in zip(CONFIG["STAGES"], positions):
            try:
                xps.move_stage(stage, pos)
            except Exception as e:
                print(f"❌ Error moving {stage}: {e}")

        success = wait_until_reached(xps, positions)
        status_line = " | ".join(f"{s}={p:.2f}" for s, p in zip(CONFIG["STAGES"], positions))
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
