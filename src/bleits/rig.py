"""
The Interrupter class - the thing other people's test code talks to.

    from bleits import Interrupter

    rig = Interrupter("mbed-rpi-004")
    rig.rf_off()      # break the DUT's antenna connection (BLE blocked)
    rig.rf_on()       # reconnect it (BLE allowed)
"""

from contextlib import contextmanager

from .transport import SSHTransport

DEFAULT_PI_SCRIPT = "~/bleits/pi/rf_switch.sh"


class Interrupter:
    def __init__(self, host, user="sava", pi_script=DEFAULT_PI_SCRIPT):
        """Connect to a rig."""
        self.host = host
        self.user = user
        self._pi_script = pi_script
        self._transport = SSHTransport(host, user)
        self._pi_runfile = "~/ble_interruptor/.bleits_current_run"

    # --- core actions -------------------------------------------------

    def rf_on(self):
        """Connect the DUT to the antenna - BLE allowed."""
        self._transport.run(f"bash {self._pi_script} on")

    def rf_off(self):
        """Break the DUT's antenna connection - BLE blocked."""
        self._transport.run(f"bash {self._pi_script} off")

    # --- safe pattern -------------------------------------------------

    @contextmanager
    def disconnected(self):
        """RF OFF inside the block, guaranteed back ON afterwards."""
        self.rf_off()
        try:
            yield self
        finally:
            self.rf_on()

    # --- laptop-side pattern runner -----------------------------------

    def run_pattern(self, off_s, on_s, cycles=None, duration_s=None,
                    verbose=True, log_file=None):
        """Run a simple off/on cycling pattern FROM THIS MACHINE.

        Each cycle is: RF off for off_s seconds, then RF on for on_s
        seconds. Repeat either a fixed number of times (cycles=) or until
        a total time has elapsed (duration_s=) - give exactly one.

        If log_file is given (a path), every transition is written to that
        file with a millisecond-resolution timestamp, in the same style as
        the Pi-side logs, so it can be correlated with the app log. If
        log_file is None (default), no log is written.

        If interrupted or errored, the rig is left ON and the log (if any)
        is closed cleanly. Returns the number of completed cycles.

            rig.run_pattern(off_s=40, on_s=40, cycles=30)
            rig.run_pattern(off_s=5, on_s=5, duration_s=600, log_file="run1.log")
        """
        if (cycles is None) == (duration_s is None):
            raise ValueError("give exactly one of cycles= or duration_s=")

        import time
        from datetime import datetime

        log_fh = open(log_file, "w") if log_file else None

        def _log(event):
            if log_fh:
                now = datetime.now()
                ts = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"
                log_fh.write(f"{ts}  {event}\n")
                log_fh.flush()

        start = time.time()
        completed = 0
        _log(f"run_pattern start: off_s={off_s} on_s={on_s} "
             f"cycles={cycles} duration_s={duration_s}")
        try:
            while True:
                if cycles is not None and completed >= cycles:
                    break
                if duration_s is not None and (time.time() - start) >= duration_s:
                    break

                if verbose:
                    if cycles is not None:
                        print(f"cycle {completed + 1}/{cycles}: off {off_s}s / on {on_s}s")
                    else:
                        elapsed = int(time.time() - start)
                        print(f"cycle {completed + 1}: off {off_s}s / on {on_s}s "
                              f"({elapsed}s / {int(duration_s)}s)")

                self.rf_off()
                _log(f"cycle {completed + 1}: RF OFF (BLE blocked)")
                time.sleep(off_s)
                self.rf_on()
                _log(f"cycle {completed + 1}: RF ON  (BLE allowed)")
                time.sleep(on_s)
                completed += 1

        except KeyboardInterrupt:
            if verbose:
                print("\ninterrupted - leaving rig ON")
            _log("interrupted - leaving rig ON")
        finally:
            try:
                self.rf_on()
                _log("run ended - rig left ON")
            except Exception:
                pass
            if log_fh:
                _log(f"run_pattern end: {completed} cycles completed")
                log_fh.close()

        if verbose:
            print(f"done - {completed} cycles completed, rig left ON")
            if log_file:
                print(f"log written to {log_file}")
        return completed

    # --- Pi-side launcher (autonomous, survives laptop disconnect) -----

    def list_profiles(self):
        """Names of the YAML patterns on the Pi (no '.yaml')."""
        out = self._transport.run("ls ~/ble_interruptor/patterns/*.yaml 2>/dev/null || true")
        names = []
        for line in out.splitlines():
            line = line.strip()
            if line.endswith(".yaml"):
                names.append(line.rsplit("/", 1)[-1][:-5])
        return names

    def run_profile(self, profile):
        """Launch a named YAML pattern on the Pi, DETACHED. Returns log path.

            rig.run_profile("BLE_Interruption_Pattern_Weekend1")
        """
        if self.is_running():
            raise RuntimeError(
                "A pattern is already running on this rig. Stop it first "
                "with stop_pattern(), or wait for it to finish."
            )

        profile = profile[:-5] if profile.endswith(".yaml") else profile

        check = self._transport.run(
            f"test -f ~/ble_interruptor/patterns/{profile}.yaml && echo OK || echo MISSING"
        )
        if check.strip() != "OK":
            available = ", ".join(self.list_profiles()) or "(none found)"
            raise RuntimeError(f"No pattern '{profile}' on the Pi. Available: {available}")

        launch = (
            f"cd ~/ble_interruptor && mkdir -p logs && "
            f"LOG=logs/$(date +%Y%m%d_%H%M%S)_{profile}.log && "
            f"( setsid ./venv/bin/python pattern_runner.py patterns/{profile}.yaml "
            f"--log-file \"$LOG\" >/dev/null 2>&1 & "
            f"echo \"$! $LOG\" > .bleits_current_run ) && "
            f"sleep 1 && cat .bleits_current_run"
        )
        out = self._transport.run(launch).strip()
        parts = out.split(None, 1)
        return parts[1] if len(parts) == 2 else "(unknown)"

    def is_running(self):
        """True if a run_profile() pattern is still running."""
        cmd = (
            f"if [ -f {self._pi_runfile} ]; then "
            f"PID=$(cut -d' ' -f1 {self._pi_runfile}); "
            f"if kill -0 \"$PID\" 2>/dev/null; then echo RUNNING; "
            f"else echo STOPPED; fi; "
            f"else echo NONE; fi"
        )
        return self._transport.run(cmd).strip() == "RUNNING"

    def tail_log(self, lines=20):
        """Last `lines` lines of the current/most-recent run's log."""
        cmd = (
            f"if [ -f {self._pi_runfile} ]; then "
            f"LOG=$(cut -d' ' -f2- {self._pi_runfile}); "
            f"cd ~/ble_interruptor && tail -n {int(lines)} \"$LOG\" 2>/dev/null || echo '(log not found)'; "
            f"else echo '(no run recorded)'; fi"
        )
        return self._transport.run(cmd)

    def stop_pattern(self):
        """Stop a running pattern and leave the rig OPEN. Safe if nothing running."""
        cmd = (
            f"if [ -f {self._pi_runfile} ]; then "
            f"PID=$(cut -d' ' -f1 {self._pi_runfile}); "
            f"kill \"$PID\" 2>/dev/null || true; "
            f"fi"
        )
        self._transport.run(cmd)
        self.rf_on()

    # --- housekeeping -------------------------------------------------

    def close(self):
        """Close the shared SSH connection."""
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.rf_on()
        except Exception:
            pass
        finally:
            self.close()
        return False

    def __repr__(self):
        return f"Interrupter(host={self.host!r}, user={self.user!r})"
