"""
The Interrupter class — the thing other people's test code talks to.

Typical use:

    from bleits import Interrupter

    rig = Interrupter("mbed-rpi-004")
    rig.rf_off()      # break the DUT's antenna connection (BLE blocked)
    rig.rf_on()       # reconnect it (BLE allowed)

Or, the safer pattern that always restores the rig even if your test
crashes mid-way:

    with Interrupter("mbed-rpi-004") as rig:
        with rig.disconnected():
            run_my_test()        # RF is OFF in here
        # RF automatically back ON here
    # connection cleaned up here
"""

from contextlib import contextmanager

from .transport import SSHTransport

# Where the Pi-side script lives on the Pi. Override per-rig if needed.
DEFAULT_PI_SCRIPT = "~/bleits/pi/rf_switch.sh"


class Interrupter:
    def __init__(self, host, user="sava", pi_script=DEFAULT_PI_SCRIPT):
        """Connect to a rig.

        host:      the Pi's hostname (e.g. "mbed-rpi-004"), reachable over
                   Tailscale / your normal SSH setup.
        user:      the Pi login account (defaults to the shared "sava" account;
                   your own SSH key authenticates you to it).
        pi_script: path to rf_switch.sh on the Pi (only change if you put it
                   somewhere non-standard).
        """
        self.host = host
        self.user = user
        self._pi_script = pi_script
        self._transport = SSHTransport(host, user)

    # --- core actions -------------------------------------------------

    def rf_on(self):
        """Connect the DUT to the antenna — BLE allowed."""
        self._transport.run(f"bash {self._pi_script} on")

    def rf_off(self):
        """Break the DUT's antenna connection — BLE blocked."""
        self._transport.run(f"bash {self._pi_script} off")

    # --- safe pattern -------------------------------------------------

    @contextmanager
    def disconnected(self):
        """Context manager: RF OFF inside the block, guaranteed back ON
        afterwards — even if the code inside raises an exception.

            with rig.disconnected():
                ...                # BLE blocked here
            # BLE allowed again here
        """
        self.rf_off()
        try:
            yield self
        finally:
            self.rf_on()

    # --- housekeeping -------------------------------------------------

    def close(self):
        """Close the shared SSH connection. Optional — it also times out
        on its own — but tidy to call when you're finished with the rig."""
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Leave the rig in a safe (connected) state, then close the
        # connection. Best-effort: never mask the original exception.
        try:
            self.rf_on()
        except Exception:
            pass
        finally:
            self.close()
        return False  # don't suppress exceptions from the with-block

    def __repr__(self):
        return f"Interrupter(host={self.host!r}, user={self.user!r})"
