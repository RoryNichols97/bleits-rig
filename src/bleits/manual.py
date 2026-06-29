"""Interactive manual control of an Interrupter from the terminal."""

from .rig import Interrupter
from .errors import RigError

_HELP = """
commands:
  o   RF on   (BLE allowed)
  f   RF off  (BLE blocked)
  t   toggle
  s   show last state set this session
  h   this help
  q   quit (leaves rig ON)
"""


def manual_session(host, user="sava"):
    """Start an interactive manual control session against a rig."""
    interrupter = Interrupter(host, user=user)
    last_state = None

    print(f"bleits manual mode - connected to {host}")
    print("type h for help, q to quit")

    try:
        while True:
            try:
                cmd = input("bleits> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if cmd in ("q", "quit", "exit"):
                break
            elif cmd in ("o", "on"):
                interrupter.rf_on(); last_state = "on"
                print("RF on  (BLE allowed)")
            elif cmd in ("f", "off"):
                interrupter.rf_off(); last_state = "off"
                print("RF off (BLE blocked)")
            elif cmd in ("t", "toggle"):
                if last_state == "off":
                    interrupter.rf_on(); last_state = "on"
                    print("RF on  (BLE allowed)")
                else:
                    interrupter.rf_off(); last_state = "off"
                    print("RF off (BLE blocked)")
            elif cmd in ("s", "state", "status"):
                print("no state set yet this session" if last_state is None else f"last set: RF {last_state}")
            elif cmd in ("h", "help", "?"):
                print(_HELP)
            elif cmd == "":
                continue
            else:
                print(f"unknown command: {cmd!r}  (h for help)")
    except RigError as e:
        print(f"\nrig error: {e}")
    finally:
        try:
            interrupter.rf_on()
            print("left rig ON.")
        except RigError as e:
            print(f"warning: could not restore rig to ON: {e}")
        finally:
            interrupter.close()
            print("connection closed.")
