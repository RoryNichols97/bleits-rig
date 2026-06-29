"""
GPIO control for BLEITS IR emitter.

Uses gpiozero on a real Raspberry Pi.
On a non-Pi machine (e.g. dev laptop), set environment variable:
    BLEITS_MOCK_GPIO=1
to use gpiozero's built-in mock pin factory.

To mirror IR state onto the Pi's onboard green ACT LED (useful for visual
debugging), set environment variable:
    BLEITS_MIRROR_TO_ACT=1
Note: requires sudo because /sys/class/leds/ACT/brightness is root-owned.

Terminology:
- "open"   = IR OFF  = RF switch passes signal = BLE allowed
- "closed" = IR ON   = RF switch blocks signal = BLE blocked
"""

import logging
import os

log = logging.getLogger(__name__)

# --- Mock GPIO setup for local dev ---
# Must be done BEFORE importing LED, so the factory is set globally.
if os.environ.get("BLEITS_MOCK_GPIO") == "1":
    from gpiozero import Device
    from gpiozero.pins.mock import MockFactory
    Device.pin_factory = MockFactory()
    log.info("Mock GPIO enabled (BLEITS_MOCK_GPIO=1)")

from gpiozero import LED  # noqa: E402  (import after factory set)

# --- ACT LED mirror config ---
ACT_LED_PATH = "/sys/class/leds/ACT"
MIRROR_TO_ACT = os.environ.get("BLEITS_MIRROR_TO_ACT") == "1"


def _act_led_setup() -> bool:
    """Take control of the ACT LED by setting its trigger to 'none'.

    Returns True if successful, False otherwise (e.g. not running as root,
    or LED path doesn't exist on this hardware).
    """
    try:
        with open(f"{ACT_LED_PATH}/trigger", "w") as f:
            f.write("none")
        log.info("ACT LED control acquired (mirror mode enabled)")
        return True
    except (PermissionError, FileNotFoundError) as e:
        log.warning(
            f"Could not control ACT LED: {e}. "
            "Run with sudo, or unset BLEITS_MIRROR_TO_ACT."
        )
        return False


def _act_led_release() -> None:
    """Return ACT LED to its default behaviour (flash on SD card activity)."""
    try:
        with open(f"{ACT_LED_PATH}/trigger", "w") as f:
            f.write("mmc0")
        log.info("ACT LED returned to default behaviour")
    except (PermissionError, FileNotFoundError):
        pass


def _act_led_set(state: bool) -> None:
    """Set ACT LED on (True) or off (False). Silently no-ops on failure."""
    try:
        with open(f"{ACT_LED_PATH}/brightness", "w") as f:
            f.write("1" if state else "0")
    except (PermissionError, FileNotFoundError):
        pass


class IRControl:
    """
    Controls an IR emitter via a single GPIO pin.

    active_low:
      False -> GPIO HIGH = IR ON
      True  -> GPIO LOW  = IR ON (inverted hardware)

    Optionally mirrors the IR state onto the Pi's onboard ACT LED for
    visual debugging when the environment variable BLEITS_MIRROR_TO_ACT=1
    is set at process start.
    """

    def __init__(self, pin: int, active_low: bool = False):
        # gpiozero handles inversion internally
        self.ir = LED(pin, active_high=not active_low)
        self.pin = pin
        # Try to acquire ACT LED control if mirror mode is requested
        self._mirror = MIRROR_TO_ACT and _act_led_setup()
        log.info(
            f"IRControl initialised on pin {pin} "
            f"(active_low={active_low}, act_led_mirror={self._mirror})"
        )

    def open(self):
        """Turn IR emitter OFF — RF switch passes signal — BLE allowed."""
        self.ir.off()
        if self._mirror:
            _act_led_set(False)
        log.info("RF: OPEN  (BLE allowed)")

    def close(self):
        """Turn IR emitter ON — RF switch blocks signal — BLE blocked."""
        self.ir.on()
        if self._mirror:
            _act_led_set(True)
        log.info("RF: CLOSE (BLE blocked)")

    def cleanup(self) -> None:
        """Release ACT LED control on shutdown.

        Called from pattern_runner's KeyboardInterrupt handler so the
        ACT LED returns to its default SD-activity behaviour after a run.
        """
        if self._mirror:
            _act_led_release()