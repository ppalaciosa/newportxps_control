class XPSMotionSession:
    def __init__(self, stages=None, skip_prep=False, verbose=False):
        from newportxpslib.xps_config import (
            load_full_config, load_user_credentials, CONFIG
        )
        from newportxps import NewportXPS
        load_user_credentials()
        self.config = load_full_config()
        if stages is not None:
            self.stages = []
            for s in stages:
                if isinstance(s, int):
                    if s <= 0 or s > len(CONFIG["STAGES"]):
                        raise ValueError(f"Stage number {s} out of range.")
                    self.stages.append(CONFIG["STAGES"][s - 1])
                elif isinstance(s, str):
                    if s not in CONFIG["STAGES"]:
                        raise ValueError(f"Stage name '{s}' not found.")
                    self.stages.append(s)
                else:
                    raise ValueError(f"Stage specifier must be int or str, got: {s}")
        else:
            self.stages = CONFIG["STAGES"]
        print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']}...")
        self.xps = NewportXPS(CONFIG["XPS_IP"], username=CONFIG["USERNAME"], password=CONFIG["PASSWORD"])
        print("✅ Connected.")
        # One-time prep!
        if not skip_prep:
            from newportxpslib.xps_motion import (
                initialize_groups, home_groups, enable_groups, all_groups_ready_and_enabled,
            )
            if all_groups_ready_and_enabled(self.xps):
                if verbose:
                    print("🚀 All groups referenced and enabled. Skipping init/home/enable steps.")
            else:
                initialize_groups(self.xps, verbose=verbose)
                home_groups(self.xps, force_home=False, verbose=verbose)
                enable_groups(self.xps, verbose=verbose)
        else:
            if verbose:
                print("⚡ Skipping ALL motion preparation! (skip_prep=True)")

    def move_motors(self, *positions, verbose=False):
        from newportxpslib.xps_motion import (
            move_stage_with_offset, wait_until_reached_blocking
        )
        if len(positions) != len(self.stages):
            raise ValueError(f"Expected {len(self.stages)} positions, got {len(positions)}.")
        move_targets = ", ".join(f"{stage} → {pos}" for stage, pos in zip(self.stages, positions))
        print(f"➡ Moving: {move_targets}")
        for stage, pos in zip(self.stages, positions):
            try:
                move_stage_with_offset(self.xps, stage, pos)
            except Exception as e:
                print(f"❌ Error moving {stage}: {e}")
        reached = wait_until_reached_blocking(self.xps, positions, stages=self.stages)
        if reached:
            print("✅ Reached all target positions.")
        else:
            print("❌ ERROR: Could not confirm all stages reached their targets.")

    def get_positions(self):
        from newportxpslib.xps_motion import get_stage_position_with_offset
        positions = {}
        for stage in self.stages:
            try:
                pos = get_stage_position_with_offset(self.xps, stage)
                positions[stage] = pos
            except Exception as e:
                print(f"❌ Failed to get position of {stage}: {e}")
                positions[stage] = None
        return positions

    def close(self):
        try:
            self.xps.ftpconn.close()
        except Exception:
            pass
