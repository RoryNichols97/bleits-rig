"""
Example: how someone embeds rig control in their own test.

Run from any machine that can SSH to the Pi (Tailscale up, your key
authorised). Change the hostname to your interrupter.
"""

import time

from bleits import Interrupter

HOST = "mbed-rpi-004"


def main():
    # The 'with' form is recommended: it guarantees the rig is left
    # connected and the SSH connection is cleaned up, even on error.
    with Interrupter(HOST) as interrupter:

        # --- simplest possible use ---
        interrupter.rf_off()          # block BLE
        time.sleep(5)
        interrupter.rf_on()           # allow BLE
        time.sleep(5)

        # --- the safe pattern: RF off only for the duration of a test ---
        with interrupter.disconnected():
            print("RF is off — running my test step here...")
            time.sleep(10)
        print("RF automatically back on.")

        # --- embedding in a loop (connection is reused automatically) ---
        for i in range(5):
            interrupter.rf_off()
            time.sleep(1)
            interrupter.rf_on()
            time.sleep(1)
            print(f"cycle {i + 1} done")


if __name__ == "__main__":
    main()
