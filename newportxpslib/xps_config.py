import os
import sys
import json
from pathlib import Path

CONFIG = {
    "XPS_IP": "",
    "USERNAME": "",
    "PASSWORD": "",
    "GROUPS": [],
    "STAGES": [],
    "LABELS": [],
    "ZERO_OFFSETS":{},
    "POSITION_TOL": 0.1,
    "WAIT_DELAY": 0.5,
    "MAX_WAIT_TIME": 10,
    "RESET_POSITION": 0.0,
}

# New: Store the currently active stages for this instance
ACTIVE_STAGES = None

def set_active_stages(stages):
    """Set which stages will be operated in this instance."""
    global ACTIVE_STAGES
    ACTIVE_STAGES = stages

def get_active_stages():
    """Return the list of active stages for this instance."""
    global ACTIVE_STAGES
    if ACTIVE_STAGES is None:
        return CONFIG["STAGES"]
    return ACTIVE_STAGES


def load_user_credentials(user_file=None):
    # Default to config/xps_connection_parameters.json with cross-platform support
    THIS_DIR = Path(__file__).parent.parent  # <-- points to newportxps_control/
    if user_file is None:
        user_file = THIS_DIR / "config" / "xps_connection_parameters.json"

    if not os.path.exists(user_file):
        print(f"🚫 Missing connection file: '{user_file}' not found.")
        print("👉 Create the file manually with your XPS login info.")
        print("📌 Example:\n", json.dumps({
            "ip": "10.0.0.1",
            "username": "username",
            "password": "password"
        }, indent=4))
        sys.exit(1)

    try:
        with open(user_file, "r") as f:
            user = json.load(f)
            CONFIG["XPS_IP"] = user.get("ip", "").strip()
            CONFIG["USERNAME"] = user.get("username", "").strip()
            CONFIG["PASSWORD"] = user.get("password", "").strip()

            if not CONFIG["XPS_IP"] or not CONFIG["USERNAME"] or not CONFIG["PASSWORD"]:
                print("\u274c XPS connection parameters are incomplete.")
                print("👉 Please fill in all fields in xps_connection_parameters.json")
                sys.exit(1)

    except Exception as e:
        print(f"❌ Failed to load user credentials from '{user_file}': {e}")
        sys.exit(1)

def load_full_config(verbose=False):
    """
    Loads user credentials and hardware configuration including
    zero offsets for stages, motion parameters, and groups.
    """
    load_user_credentials()
    THIS_DIR = Path(__file__).parent.parent  # <-- points to newportxps_control/
    hardware_file = THIS_DIR / "config" / "xps_hardware.json"
    if not os.path.exists(hardware_file):
        print(f"🚫 Missing hardware file: '{hardware_file}' not found.")
        print("👉 Generate it using --generate-config.")
        sys.exit(1)

    try:
        with open(hardware_file, "r") as f:
            hw = json.load(f)
            CONFIG["GROUPS"] = hw.get("groups", [])
            CONFIG["STAGES"] = hw.get("stages", [])
            CONFIG["LABELS"] = hw.get("labels", CONFIG["STAGES"])

            # Load zero offsets per stage; default to 0.0 if missing for any stage
            zero_offsets_raw = hw.get("zero_offsets", {})
            CONFIG["ZERO_OFFSETS"] = {
                stage: float(zero_offsets_raw.get(stage, 0.0))
                for stage in CONFIG["STAGES"]
            }

            motion = hw.get("motion", {})
            CONFIG["POSITION_TOL"] = motion.get("position_tolerance", 0.1)
            CONFIG["WAIT_DELAY"] = motion.get("wait_delay", 0.5)
            CONFIG["MAX_WAIT_TIME"] = motion.get("max_wait_time", 10)
            CONFIG["RESET_POSITION"] = motion.get("reset_position", 0.0)
        if verbose:
            print("✅ Configuration loaded from xps_connection_parameters.json and xps_hardware.json\n")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)

    return CONFIG

def backup_xps_config(xps):
    output_folder = Path("xps_config_backup")
    output_folder.mkdir(exist_ok=True)
    try:
        xps.save_systemini(output_folder / "system.ini")
        xps.save_stagesini(output_folder / "stages.ini")
        print(f"✅ Config files backed up to '{output_folder}/'\n")
    except Exception as e:
        print(f"❌ Failed to backup config: {e}")

def generate_config(xps, output_file=Path("config") / "xps_hardware.json"):
    print("🛠 Generating config from live XPS system...")
    config = {
        "groups": list(xps.groups.keys()),
        "stages": [],
        "labels": [],
        "zero_offsets": {},   # New field added for zero offsets; empty by default
        "motion": {
            "position_tolerance": CONFIG["POSITION_TOL"],
            "wait_delay": CONFIG["WAIT_DELAY"],
            "max_wait_time": CONFIG["MAX_WAIT_TIME"],
            "reset_position": CONFIG["RESET_POSITION"]
        }
    }

    for group, details in xps.groups.items():
        for pos in details.get("positioners", []):
            stage_name = f"{group}.{pos}"
            config["stages"].append(stage_name)
            config["labels"].append(stage_name)
            config["zero_offsets"][stage_name] = 0.0  # Default offset zero on generation


    with open(output_file, "w") as f:
        json.dump(config, f, indent=4)

    print(f"✅ Config generated and saved to '{output_file}'")

def save_status_report_to_file(xps, filename="xps_status_report.txt"):
    try:
        report = xps.status_report()
        with open(filename, "w") as f:
            f.write(report)
        print(f"📄 XPS status report saved to '{filename}'\n")
    except Exception as e:
        print(f"❌ Failed to save status report: {e}")
