"""
The Interrupter class — the thing other people's test code talks to.

Typical use:

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
        """Connect to a rig.

        host:      the Pi's hostname (e.g. "mbed-rpi-004").
        user:      the Pi login account (defaults to "sava").
        pi_script: path to rf_switch.sh on the Pi.
        """
        self.host = host
        self.user = user
        self._pi_script = pi_script
        self._transport = SSHTransport(host, user)

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
        """Context manager: RF OFF inside the block, guaranteed back ON
        afterwards - even if the code inside raises an exception."""
        self.rf_off()
        try:
            yield self
        finally:
            self.rf_on()

    # --- laptop-side pattern runner -----------------------------------

    def run_pattern(self, off_s, on_s, cycles=None, duration_s=None, verbose=True):
        """Run a simple off/on cycling pattern FROM THIS MACHINE.

        Each cycle is: RF off for off_s seconds, then RF on for on_s
        seconds. Repeat either a fixed number of times (cycles=) or until
        a total time has elapsed (duration_s=) - give exactly one.

        Loops on the calling machine, so it ties up your terminal and stops
        if your laptop sleeps. Meant for short bench runs; for long
        unattended runs hand a profile to the Pi (run_profile()).

        If interrupted or errored, the rig is left ON. Returns cycles done.

            rig.run_pattern(off_s=40, on_s=40, cycles=30)
            rig.run_pattern(off_s=5, on_s=5, duration_s=600)
        """
        if (cycles is None) == (duration_s is None):
            raise ValueError("give exactly one of cycles= or duration_s=")

        import time

        start = time.time()
        completed = 0
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
                time.sleep(off_s)
                self.rf_on()
                time.sleep(on_s)
                completed += 1

        except KeyboardInterrupt:
            if verbose:
                print("\ninterrupted - leaving rig ON")
        finally:
            try:
                self.rf_on()
            except Exception:
                pass

        if verbose:
            print(f"done - {completed} cycles completed, rig left ON")
        return completed

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
