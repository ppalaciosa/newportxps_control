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