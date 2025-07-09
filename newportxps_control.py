# newportxps_control.py
"""
CLI entry point for Newport XPS motion control.
- Parses CLI args
- Dispatches to reusable API functions in controller_interface, utils, etc.
- Handles user-facing messages and file outputs only.

All actual device control is handled by the imported modules.

Dependencies:
- newportxpslib (your custom library)
- newportxps pip package
"""

import argparse
import json

from newportxps import NewportXPS
from newportxpslib.controller_interface import move_motors, get_positions, get_status
from newportxpslib.utils import parse_stages_arg, set_zero_for_stages
from newportxpslib.xps_config import (
    load_full_config, save_status_report_to_file, backup_xps_config,
    generate_config, load_user_credentials, CONFIG,
    set_active_stages, get_active_stages,
)
from newportxpslib.xps_motion import (
    print_motion_format, load_position_combinations,
    initialize_groups, home_groups, reset_stages,
    execute_position_configurations, all_groups_ready_and_enabled,
)

###############################
# --- CLI ARGUMENTS PARSING ---
###############################

def parse_args():
    """
    Set up and return the CLI argument parser.
    """
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
    parser.add_argument("--set-zero", action="store_true",
        help="Set the current position of all selected stages as their new zero offset in xps_hardware.json")
    return parser.parse_args()


def main():
    """
    Main CLI dispatch logic for Newport XPS control.
    All actual hardware and config logic lives in the imported modules.
    """
    args = parse_args()

    try:
        # 1. Print format guide and exit
        if args.format_guide:
            print_motion_format()
            return

        # 2. Load config and set up user credentials
        load_user_credentials()
        config = load_full_config(verbose=True)

        # 3. Handle active stages selection (by CLI, or all)
        stage_list = parse_stages_arg(args.stages)
        set_active_stages(stage_list)

        # 4. Option: Set zero offset by current position, then exit
        if args.set_zero:
            set_zero_for_stages(stage_list)
            return

        # 5. Option: Print positions of selected stages, then exit
        if args.get_positions:
            positions = get_positions(stages=stage_list)
            print("Current positions of selected stages:")
            for stage, pos in positions.items():
                if pos is not None:
                    print(f"  {stage}: {pos:.4f}")
                else:
                    print(f"  {stage}: ERROR (could not read)")
            return

        # 6. Connect to XPS controller
        print(f"🔌 Attempting connection to XPS at {CONFIG['XPS_IP']}...")
        try:
            xps = NewportXPS(CONFIG["XPS_IP"], 
                        username=CONFIG["USERNAME"], 
                        password=CONFIG["PASSWORD"])
            print("✅ Connected to XPS successfully!\n")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

        # 7. Backup or generate config and exit
        if args.backup:
            backup_xps_config(xps)
            return

        if args.generate_config:
            generate_config(xps)
            return

        # 8. Save status for inspection
        save_status_report_to_file(xps)

        # 9. Forced homing/setup if requested (and exit if only homing)
        if args.home:
            initialize_groups(xps, verbose=args.verbose)
            home_groups(xps, force_home=True, verbose=args.verbose)
            print("🏁 Homing completed. Exiting as requested by --home.")
            return
        
        # 10. If reset, reset positions (after setup)
        if args.reset:
            initialize_groups(xps, verbose=args.verbose)
            home_groups(xps, force_home=False, verbose=args.verbose)
            reset_stages(xps, verbose=args.verbose)

        # 11. Fast path: skip repeated group prep if everything ready
        if not args.reset and all_groups_ready_and_enabled(xps):
            if args.verbose:
                print("🚀 All groups referenced and enabled. Skipping init/home/enable steps.")
        else:
            initialize_groups(xps, verbose=args.verbose)
            home_groups(xps, force_home=False, verbose=args.verbose)

        # 12. Load positions from file 
        active_stages = get_active_stages()
        combos = load_position_combinations(args.file, active_stages)

        if not combos:
            print("❌ No valid combinations found in motion file.")
            return

        # 13. Execute moves (loop or single pass)
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

# Required to run from command line
if __name__ == "__main__":
    main()