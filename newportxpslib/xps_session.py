class XPSMotionSession:
    """
    Session object for robust, efficient Newport XPS control.

    - Initializes only once per session (unless you want to reconnect).
    - Remembers which motors (stages) you care about, and in which order.
    - Handles all move/get operations without repeated hardware prep.
    - Provides a method to fully prepare (initialize, home, enable) groups, if needed.
    - Handles out-of-range or not-enabled/homed errors gracefully.
    """

    def __init__(self, stages=None, verbose=False):
        """
        Initialize the session and connect to XPS.

        Arguments:
            stages: list of stage names (str) or numbers (int, 1-based). Default: all stages.
            verbose: print extra diagnostics.
        """
        from .xps_config import (
            load_full_config, load_user_credentials, CONFIG
        )
        from newportxps import NewportXPS
        
        load_user_credentials()
        self.config = load_full_config()
        
        # ---- Interpret 'stages' (support names or 1-based numbers) ----
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

        # ---- Connect to controller once ----    
        print(f"🔌 Connecting to XPS at {CONFIG['XPS_IP']}...")
        self.xps = NewportXPS(CONFIG["XPS_IP"], 
            username=CONFIG["USERNAME"], 
            password=CONFIG["PASSWORD"])
        print("✅ Connected.")

        self.verbose = verbose

    def kill_all_groups(self):
        """
        Kill all motion groups, bringing all axes to the Not Initialized state.
        This is the safest possible shutdown state.
        """
        from .xps_motion import kill_all_groups
        print("🛑 Killing all groups (bringing system to NOT INITIALIZED state)...")
        kill_all_groups(self.xps, verbose=self.verbose)
        print("🔴 All groups killed (not initialized).")

    def initialize_groups(self):
        """Initialize all groups (prepares for homing, but cannot move yet)."""
        from .xps_motion import initialize_groups
        print("🔄 Initializing all groups...")
        initialize_groups(self.xps, verbose=self.verbose)
        print("🟡 All groups initialized (ready to home).")

    def home_groups(self, force_home=True):
        """Home all groups (brings axes to referenced state)."""
        from .xps_motion import home_groups
        print("🏠 Homing all groups...")
        home_groups(self.xps, force_home=force_home, verbose=self.verbose)
        print("🟢 All groups homed (referenced).")

    def enable_groups(self):
        """Enable all groups (axes ready to move)."""
        from .xps_motion import enable_groups
        print("⚡ Enabling all groups...")
        enable_groups(self.xps, verbose=self.verbose)
        print("🟢 All groups enabled (ready to move).")

    def prepare_groups(self, force_home=True):
        """
        Fully prepare all groups for motion: initialize and home (in this order).
        (Enabling is not required for most Newport XPS hardware/firmware.)
        """
        self.initialize_groups()
        self.home_groups(force_home=force_home)
        print("🟢 Groups fully prepared for motion (initialized and homed).")
    
    def move_motors(self, *positions, verbose=False, ensure_prep=True):
        """
        Move all session stages to given absolute positions (with zero offsets).

        - If any move is illegal (out of range, not enabled/homed), error is printed for that stage.
        - If any move fails, skips waiting for completion and returns False.

        Arguments:
            positions: one per stage (order = self.stages)
            verbose: print extra info for this move (default: session verbose)
        Returns:
            True if all moves succeeded and all reached targets, False otherwise.
        """
        from .xps_motion import (
            move_stage_with_offset, wait_until_reached_blocking
        )

        if len(positions) != len(self.stages):
            raise ValueError(f"Expected {len(self.stages)} positions, got {len(positions)}.")

        if verbose is None:
            verbose = self.verbose
        
        move_targets = ", ".join(f"{stage} → {pos}" 
                            for stage, pos in zip(self.stages, positions))
        print(f"➡ Moving: {move_targets}")
        
        move_failed = False  # Track if any move failed
        for stage, pos in zip(self.stages, positions):
            try:
                move_stage_with_offset(self.xps, stage, pos)
            except Exception as e:
                print(f"❌ Error moving {stage}: {e}")
                # Typical errors: Not allowed action (not enabled), out of range, etc.
                if "Not allowed action" in str(e) or "not enabled" in str(e) or "not referenced" in str(e):
                    print(f"⚠️ Stage '{stage}' is not enabled/homed. Please run initialization once before motion.")
                move_failed = True

        if move_failed:
            print("❌ One or more move commands failed. Skipping wait for completion.")
            return False

        reached = wait_until_reached_blocking(self.xps, positions, stages=self.stages)
        if reached:
            print("✅ Reached all target positions.")
        else:
            print("❌ ERROR: Could not confirm all stages reached their targets.")

    def get_positions(self):
        """
        Return dictionary of positions for all session stages.
        Example: { 'SP1.Pos1': 90.001, 'SP3.Pos3': 0.002 }
        """
        from .xps_motion import get_stage_position_with_offset
        positions = {}
        for stage in self.stages:
            try:
                pos = get_stage_position_with_offset(self.xps, stage)
                positions[stage] = pos
            except Exception as e:
                print(f"❌ Failed to get position of {stage}: {e}")
                positions[stage] = None
        return positions

    def close(self, kill_all=False):
        """
        Close the XPS connection.
        If kill_all is True, will kill all groups (safest state for hardware!).
        """
        if kill_all:
            try:
                self.kill_all_groups()
            except Exception as e:
                print(f"❌ Error during kill_all: {e}")
        try:
            self.xps.ftpconn.close()
        except Exception:
            pass

"""
Usage: 
session = XPSMotionSession(stages=[1,3])
session.enable_groups()  # Only call this after power-up/reset or if hardware requires it!
session.move_motors(10, 12)  # No XPSError if already enabled!
print(session.get_positions())
session.close()
"""