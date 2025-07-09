"""
controller_interface.py

Reusable API-like functions for controlling Newport XPS stages:
- move_motors
- get_positions
- get_status

All functions are stateless: connect, do the work, disconnect.
"""
from newportxpslib.xps_config import (
    load_full_config, load_user_credentials, CONFIG, get_active_stages
)
from newportxpslib.xps_motion import (
    initialize_groups, home_groups, enable_groups,
    wait_until_reached_blocking, move_stage_with_offset,
    all_groups_ready_and_enabled, get_stage_position_with_offset,
)
from newportxps import NewportXPS

def move_motors(*positions, stages=None, skip_prep=False, verbose=False):
    """
    Moves Newport XPS motors to the given absolute positions.

    Arguments:
        positions: list of float values, one per stage.
        stages: list of stage names, e.g. ["SP1.Pos1", "SP3.Pos3"]. 
                If None, uses all active stages.
        skip_prep: if True, skips group enable/init/homing steps 
                            (faster, but assumes system is ready).
        verbose: if True, prints extra info.
    """

    # Load config and connect to XPS
    load_user_credentials()
    config = load_full_config()
    
    # Parse the stages argument (name or 1-based index)
    if stages is not None:
        chosen_stages = []
        for s in stages:
            if isinstance(s, int):
                if s <= 0 or s > len(CONFIG["STAGES"]):
                    raise ValueError(f"Stage index {s} out of range.")
                chosen_stages.append(CONFIG["STAGES"][s - 1]) # 1-based to 0-based!
            elif isinstance(s, str):
                if s not in CONFIG["STAGES"]:
                    raise ValueError(f"Stage name '{s}' not found.")
                chosen_stages.append(s)
            else:
                raise ValueError(f"Stage specifier must be int or str, got: {s}")
    else:
        chosen_stages = get_active_stages()

    if len(positions) != len(stages):
        raise ValueError(f"Expected {len(stages)} positions, got {len(positions)}.")

    print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']}...")
    xps = NewportXPS(CONFIG["XPS_IP"], 
                    username=CONFIG["USERNAME"], 
                    password=CONFIG["PASSWORD"])
    print("✅ Connected.")

    if not skip_prep:
        if all_groups_ready_and_enabled(xps):
            if verbose:
                print("🚀 All groups referenced and enabled. Skipping init/home/enable steps.")
        else:
            initialize_groups(xps, verbose=verbose)
            home_groups(xps, force_home=False, verbose=verbose)
            enable_groups(xps, verbose=verbose)
    else:
        if verbose:
            print("⚡ Skipping ALL motion preparation! (skip_prep=True)")

    move_targets = ", ".join(f"{stage} → {pos}" for stage, pos in zip(chosen_stages, positions))
    print(f"➡ Moving: {move_targets}")

    move_failed = False
    for stage, pos in zip(chosen_stages, positions):
        try:
            move_stage_with_offset(xps, stage, pos)
        except Exception as e:
            print(f"❌ Error moving {stage}: {e}")
            move_failed = True

    if move_failed:
        print("❌ One or more move commands failed. Skipping wait for completion.")
        try: xps.ftpconn.close()
        except Exception: pass
        return False

    reached = wait_until_reached_blocking(xps, positions, stages=chosen_stages)
    if reached:
        print("✅ Reached all target positions.")
    else:
        print("❌ ERROR: Could not confirm all stages reached their targets.")

    try:
        xps.ftpconn.close()
    except Exception:
        pass
    return reached


def get_positions(stages=None):
    """
    Returns a dictionary of current stage positions.
    Args:
        stages: Optional list of stage names (str) or numbers (int, 1-based).
                If None, uses all configured stages.
    Returns:
        dict: { "stage_name": position }
    """

    load_user_credentials()
    config = load_full_config()

    # Determine which stages to use
    if stages is not None:
        chosen_stages = []
        for s in stages:
            if isinstance(s, int):
                # 1-based
                if s <= 0 or s > len(CONFIG["STAGES"]):
                    raise ValueError(f"Stage number {s} out of range.")
                chosen_stages.append(CONFIG["STAGES"][s - 1])
            elif isinstance(s, str):
                # Name-based
                if s not in CONFIG["STAGES"]:
                    raise ValueError(f"Stage name '{s}' not found.")
                chosen_stages.append(s)
            else:
                raise ValueError(f"Stage specifier must be int or str, got: {s}")
    else:
        chosen_stages = CONFIG["STAGES"]

    xps = NewportXPS(CONFIG["XPS_IP"], 
                    username=CONFIG["USERNAME"], 
                    password=CONFIG["PASSWORD"])
    positions = {}

    for stage in chosen_stages:
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

    load_user_credentials()
    xps = NewportXPS(CONFIG["XPS_IP"], 
                    username=CONFIG["USERNAME"], 
                    password=CONFIG["PASSWORD"])
    report = xps.status_report()

    try:
        xps.ftpconn.close()
    except Exception:
        pass

    return report