"""Command-line interface for bleits."""

import argparse
import sys

from .rig import Interrupter
from .manual import manual_session
from .errors import RigError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bleits", description="Control a BLE Interruption Test Stand.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_manual = sub.add_parser("manual", help="interactive manual control session")
    p_manual.add_argument("host", help="rig hostname, e.g. mbed-rpi-004")
    p_manual.add_argument("--user", default="sava")

    p_on = sub.add_parser("on", help="set RF on once and exit")
    p_on.add_argument("host")
    p_on.add_argument("--user", default="sava")

    p_off = sub.add_parser("off", help="set RF off once and exit")
    p_off.add_argument("host")
    p_off.add_argument("--user", default="sava")

    args = parser.parse_args(argv)

    try:
        if args.command == "manual":
            manual_session(args.host, user=args.user)
        elif args.command == "on":
            with Interrupter(args.host, user=args.user) as i:
                i.rf_on(); print("RF on")
        elif args.command == "off":
            with Interrupter(args.host, user=args.user) as i:
                i.rf_off(); print("RF off")
    except RigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
