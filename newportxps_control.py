import argparse
from newportxps import NewportXPS
from newportxpslib.xps_config import (
    load_full_config,
    save_status_report_to_file,
    backup_xps_config,
    generate_config,
    load_user_credentials,
    CONFIG
)
from newportxpslib.xps_motion import (
    print_motion_format,
    load_position_combinations,
    initialize_groups,
    home_groups,
    enable_groups,
    wait_until_reached,
    reset_stages,
    execute_position_configurations
)

def parse_args():
    parser = argparse.ArgumentParser(description="Newport XPS Motion Control Tool")

    parser.add_argument("--file", type=str, default="motion.txt",
                        help="Path to file with motion configurations")
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

    return parser.parse_args()

def main():
    args = parse_args()

    try:
        # Show format help if requested
        if args.format_guide:
            print_motion_format()
            return

        load_user_credentials()

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
        config = load_full_config()

        # Save status report to file for inspection
        save_status_report_to_file(xps)

        # Initialize and prepare motion groups
        initialize_groups(xps)
        
        if args.home:
            # Only perform homing and exit
            home_groups(xps, force_home=True)
            print("🏁 Homing completed. Exiting as requested by --home.")
            return
        else:
            # Auto-home only if not already referenced
            home_groups(xps, force_home=False)
        
        enable_groups(xps)

        # Reset positions if requested
        if args.reset:
            reset_stages(xps)

        # Load position configurations from file
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


def move_motors(*positions):
    """
    Moves Newport XPS motors to the given absolute positions.

    Arguments:
        positions: list of float values, one per configured stage.
    """
    from xps_config import load_full_config, CONFIG
    from xps_motion import (
        initialize_groups, home_groups, enable_groups,
        wait_until_reached
    )

    # Load config and connect to XPS
    load_user_credentials()
    config = load_full_config()

    if len(positions) != len(config["STAGES"]):
        raise ValueError(f"Expected {len(config['STAGES'])} positions, got {len(positions)}.")

    print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']}...")
    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
    print("✅ Connected.")

    initialize_groups(xps)
    home_groups(xps, force_home=False)
    enable_groups(xps)

    print(f"➡ Moving to: {positions}")
    for stage, pos in zip(config["STAGES"], positions):
        try:
            xps.move_stage(stage, pos)
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
    from xps_config import load_full_config, CONFIG

    load_user_credentials()
    config = load_full_config()

    xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
    positions = {}

    for stage in config["STAGES"]:
        try:
            pos = xps.get_stage_position(stage)
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
    from xps_config import load_user_credentials, CONFIG

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
