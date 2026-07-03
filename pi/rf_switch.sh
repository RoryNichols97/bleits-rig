#!/usr/bin/env bash
# ============================================================
# rf_switch.sh — runs ON the Raspberry Pi
# ============================================================
# Sets the RF-switch IR-control GPIO and exits, leaving the pin
# level LATCHED in hardware (so the state persists after this
# command returns — important, because the control library calls
# this fresh over SSH for each on/off).
#
# Uses `pinctrl` (current Pi OS) or `raspi-gpio` (older) rather
# than a Python GPIO library, because those set-and-exit cleanly
# without resetting the pin when the process ends.
#
#   on  = BLE allowed  = IR emitter OFF = RF path connected
#   off = BLE blocked  = IR emitter ON  = RF path broken
#
# Hardware mapping (current rig): active_low = false,
#   verified on rig: on = GPIO HIGH = BLE allowed; off = GPIO LOW = BLE blocked.
# ============================================================

set -euo pipefail

PIN=17

case "${1:-}" in
  on)  LEVEL=dh ;;   # BLE allowed -> drive GPIO high
  off) LEVEL=dl ;;   # BLE blocked -> drive GPIO low
  *)
    echo "usage: rf_switch.sh on|off" >&2
    exit 2
    ;;
esac

if command -v pinctrl >/dev/null 2>&1; then
  pinctrl set "$PIN" op "$LEVEL"
elif command -v raspi-gpio >/dev/null 2>&1; then
  raspi-gpio set "$PIN" op "$LEVEL"
else
  echo "error: neither 'pinctrl' nor 'raspi-gpio' found on this Pi" >&2
  exit 3
fi

echo "RF $1"
