"""
bleits - simple control of a BLE Interruption Test Stand.

    from bleits import Interrupter

    rig = Interrupter("mbed-rpi-004")
    rig.rf_off()
    rig.rf_on()
"""

from .rig import Interrupter
from .manual import manual_session
from .errors import RigError, RigConnectionError, RigCommandError

__all__ = ["Interrupter", "manual_session", "RigError", "RigConnectionError", "RigCommandError"]
__version__ = "0.1.0"
