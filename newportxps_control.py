import argparse
from newportxps import NewportXPS
from newportxpslib.xps_config import (
    load_full_config,
    save_status_report_to_file,
    backup_xps_config,
    generate_config,
    load_user_credentials,
    CONFIG,
    set_active_stages,
)
from newportxpslib.xps_motion import (
    print_motion_format,
    load_position_combinations,
    initialize_groups,
    home_groups,
    enable_groups,
    wait_until_reached,
    reset_stages,
    execute_position_configurations,
    get_active_stages,
    all_groups_ready_and_enabled,
)

def parse_args():
    parser = argparse.ArgumentParser(description="Newport XPS Motion Control Tool")

    parser.add_argument("--file", type=str, default="motion.txt",
                        help="Path to file with motion configurations")
    parser.add_argument("--stages", type=str,
                        help="Comma-separated list of stages to operate (names or 1-based indices)")
    parser.add_argument("--home", action="store_true",
                        help="Perform homing if any stage is not referenced")
    parser.add_argument("--reset", action="store_true",
                        help="Reset all stages to configured initial position")
    parser.add_argument("--loop", action="store_true",
                        help="Continuously loop through the motion configurations")
    parser.add_argument("--log", type=str,
                        help="Path to CSV log file to record positions")
    parser.add_argument("--generate-config", action="store_true",
                        help="Generate hardware config from live XPS and exit")
    parser.add_argument("--backup", action="store_true",
                        help="Backup system.ini and stages.ini from XPS and exit")
    parser.add_argument("--format-guide", action="store_true",
                        help="Print format guide for motion.txt and exit")
    parser.add_argument("--get-positions", action="store_true", 
                        help="Print the current positions of the selected stages and exit")
    parser.add_argument("--verbose", action="store_true", 
                        help="Enable detailed output for initialization and status")
    parser.add_argument("--skip-prep", action="store_true", 
                        help="Skip ALL group initialization, homing, and enabling")


    return parser.parse_args()

def main():
    args = parse_args()

    try:
        # Show format help if requested
        if args.format_guide:
            print_motion_format()
            return

        load_user_credentials()
        config = load_full_config()

        # ---- Handle active stages selection ----
        if args.stages:
            stage_list = []
            if all(s.strip().isdigit() for s in args.stages.split(',')):
                # By index (1-based)
                indices = [int(s.strip())-1 for s in args.stages.split(',')]
                for i in indices:
                    if i < 0 or i >= len(CONFIG["STAGES"]):
                        raise ValueError(f"Stage index {i+1} out of range.")
                    stage_list.append(CONFIG["STAGES"][i])
            else:
                # By name
                for s in args.stages.split(','):
                    s = s.strip()
                    if s not in CONFIG["STAGES"]:
                        raise ValueError(f"Stage name '{s}' not found.")
                    stage_list.append(s)
            set_active_stages(stage_list)
        else:
            set_active_stages(CONFIG["STAGES"])
        # ---- End active stages selection ----

        # Handle --get-positions
        if args.get_positions:
            positions = get_positions()
            print("Current positions of selected stages:")
            for stage, pos in positions.items():
                if pos is not None:
                    print(f"  {stage}: {pos:.4f}")
                else:
                    print(f"  {stage}: ERROR (could not read)")
            return

        # Connect to the XPS
        print(f"🔌 Attempting connection to XPS at {CONFIG['XPS_IP']}...")
        try:
            xps = NewportXPS(CONFIG["XPS_IP"], 
                username=CONFIG["USERNAME"], 
                password=CONFIG["PASSWORD"])
            print("✅ Connected to XPS successfully!\n")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

        # Run selected one-time actions
        if args.backup:
            backup_xps_config(xps)
            return

        if args.generate_config:
            generate_config(xps)
            return

        # Load configuration (IP, credentials, stages, motion tolerances)
        #config = load_full_config()

        # Save status report to file for inspection
        save_status_report_to_file(xps)

        # Initialize and prepare motion groups
        #initialize_groups(xps)
        
        # Forced group setup or reset/homing gets highest priority
        if args.home:
            initialize_groups(xps, verbose=args.verbose)
            home_groups(xps, force_home=True, verbose=args.verbose)
            enable_groups(xps, verbose=args.verbose)
            print("🏁 Homing completed. Exiting as requested by --home.")
            return
        
        #enable_groups(xps)

        # Reset positions if requested
        if args.reset:
            initialize_groups(xps, verbose=args.verbose)
            home_groups(xps, force_home=False, verbose=args.verbose)
            enable_groups(xps, verbose=args.verbose)
            reset_stages(xps, verbose=args.verbose)
            # Do NOT return; continue to execute positions after reset

        # --------- SUPER FAST MOTION LAUNCH -----------
        if args.skip_prep:
            if args.verbose:
                print("⚡ Skipping ALL motion preparation! (You requested --skip-prep)")
            # You might want to warn the user if the move fails due to a group state problem!
        else:
            if not args.reset and all_groups_ready_and_enabled(xps):
                if args.verbose:
                    print("🚀 All groups referenced and enabled. Skipping init/home/enable steps.")
            else:
                initialize_groups(xps, verbose=args.verbose)
                home_groups(xps, force_home=False, verbose=args.verbose)
                enable_groups(xps, verbose=args.verbose)
        # ----------------------------------------------


        # ---- ACTIVE STAGES: from here on, only use get_active_stages() ----
        active_stages = get_active_stages()

        # Load position configurations from file (MUST MATCH number of active stages)
        combos = load_position_combinations(args.file, config["STAGES"])
        if not combos:
            print("❌ No valid combinations found in motion file.")
            return

        # Execute configurations
        if args.loop:
            print("🔁 Looping through motion configurations (Ctrl+C to stop)...\n")
            try:
                while True:
                    execute_position_configurations(xps, combos, args.log)
            except KeyboardInterrupt:
                print("\n⛔ Loop interrupted by user.")
        else:
            execute_position_configurations(xps, combos, args.log)

        print("\n🔄 Closing connection...")
        try:
            xps.ftpconn.close()
        except Exception:
            pass
        print("✅ Connection closed.")

    except Exception as e:
        print("\n❌ Unexpected failure occurred:")
        print(f"   {e}")
        print("💡 This might be due to sudden power loss or controller disconnection.")
        print("🧹 Cleaning up and exiting...")

# ---- Convenience for Python API/interactive use ----
def move_motors(*positions):
    """
    Moves Newport XPS motors to the given absolute positions (in active stages order).

    Arguments:
        positions: list of float values, one per configured stage.
    """
    from newportxpslib.xps_config import load_full_config, CONFIG, get_active_stages
    from newportxpslib.xps_motion import (
        initialize_groups, home_groups, enable_groups,
        wait_until_reached, move_stage_with_offset
    )

    # Load config and connect to XPS
    load_user_credentials()
    config = load_full_config()
    stages = get_active_stages()

    if len(positions) != len(config["STAGES"]):
        raise ValueError(f"Expected {len(stages)} positions, got {len(positions)}.")

    print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']}...")
    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
    print("✅ Connected.")

    initialize_groups(xps, verbose=args.verbose)
    home_groups(xps, force_home=False, verbose=args.verbose)
    enable_groups(xps, verbose=args.verbose)

    print(f"➡ Moving to: {positions}")
    for stage, pos in zip(stages, positions):
        try:
            move_stage_with_offset(xps, stage, pos)
        except Exception as e:
            print(f"❌ Error moving {stage}: {e}")

    reached = wait_until_reached(xps, positions)
    if reached:
        print("✅ Reached all target positions.")
    else:
        print("⚠️ Timed out waiting for stages to reach target.")

    try:
        xps.ftpconn.close()
    except Exception:
        pass


def get_positions():
    """
    Returns a dictionary of current stage positions.
    Format: { "stage_name": position }
    """
    from newportxpslib.xps_config import load_full_config, CONFIG, get_active_stages
    from newportxpslib.xps_motion import get_stage_position_with_offset

    load_user_credentials()
    config = load_full_config()

    from newportxps import NewportXPS
    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
    stages = get_active_stages()
    positions = {}

    for stage in stages:
        try:
            pos = get_stage_position_with_offset(xps, stage)
            positions[stage] = pos
        except Exception as e:
            print(f"❌ Failed to get position of {stage}: {e}")
            positions[stage] = None

    try:
        xps.ftpconn.close()
    except Exception:
        pass

    return positions


def get_status():
    """
    Returns the full status report string from the XPS system.
    """
    from newportxpslib.xps_config import load_user_credentials, CONFIG
    from newportxps import NewportXPS

    load_user_credentials()

    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
    report = xps.status_report()

    try:
        xps.ftpconn.close()
    except Exception:
        pass

    return report

# Required to run from command line
if __name__ == "__main__":
    main()
