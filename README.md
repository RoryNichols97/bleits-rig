# bleits-rig

Simple Python control of a **BLE Interruption Test Stand**.

Lets any test program switch a rig's RF connection on and off without knowing
anything about the Pi, GPIO, IR, or the RF switch underneath:

```python
from bleits import Interrupter

interrupter = Interrupter("mbed-rpi-004")
interrupter.rf_off()    # break the DUT's antenna connection (BLE blocked)
interrupter.rf_on()     # reconnect it (BLE allowed)
```

It talks to the rig's Raspberry Pi over SSH, using **your own SSH key** — the
same one you already use to `ssh sava@<host>`. No passwords or secrets live in
the code.

---

## How it works (one picture)

```
your test machine                          the rig's Raspberry Pi
┌───────────────────┐     SSH (your key)   ┌────────────────────────┐
│  import bleits     │ ───────────────────▶ │  rf_switch.sh on|off    │
│  interrupter.rf_off()      │                      │  → sets GPIO 17         │
└───────────────────┘                      │  → drives the RF switch │
                                            └────────────────────────┘
```

Your code runs on your machine. The actual switching happens on the Pi. The
library is just the bridge.

---

## Install

```bash
pip install bleits-rig
```

(or, from a clone of this repo: `pip install -e .`)

**Prerequisites on your machine:**
- The normal `ssh` command works.
- You can already run `ssh sava@<your-rig-host>` without a password (i.e. your
  SSH key is set up and authorised on the Pi).
- Tailscale (or whatever network you use to reach the Pi) is up.

If `ssh sava@<host>` works in your terminal, the library will work.

---

## One-time Pi setup

The Pi needs the small switch script in place. From the repo:

```bash
ssh sava@<host> "mkdir -p ~/bleits/pi"
scp pi/rf_switch.sh sava@<host>:~/bleits/pi/
ssh sava@<host> "chmod +x ~/bleits/pi/rf_switch.sh"
```

That's it. The script uses `pinctrl` (or `raspi-gpio`) which ship with Pi OS.

---

## Usage

### Simplest

```python
from bleits import Interrupter

interrupter = Interrupter("mbed-rpi-004")
interrupter.rf_off()
interrupter.rf_on()
```

### Recommended: the `with` forms (safe even if your test crashes)

```python
with Interrupter("mbed-rpi-004") as rig:
    with interrupter.disconnected():
        run_my_test()      # RF is OFF in here
    # RF automatically ON again here, even if run_my_test() raised
# SSH connection cleaned up here
```

`rig.disconnected()` guarantees the rig goes back to **connected** when the
block ends — so a failing test never leaves the rig stuck off.

### Multiple rigs

Each rig is just one object — make as many as you need:

```python
int_a = Interrupter("rpi-004")
int_b = Interrupter("rpi-007")
int_a.rf_off()
int_b.rf_off()
```

---

## API

| Call | What it does |
|---|---|
| `Interrupter(host, user="sava")` | Connect to a rig by hostname |
| `interrupter.rf_on()` | Connect DUT to antenna (BLE allowed) |
| `interrupter.rf_off()` | Break the connection (BLE blocked) |
| `with interrupter.disconnected(): ...` | RF off for the block, back on after (even on error) |
| `interrupter.close()` | Close the SSH connection (optional; also auto-closes) |
| `with Interrupter(...) as rig: ...` | Auto safe-state + cleanup on exit |

**Errors** (all subclass `RigError`):
- `RigConnectionError` — couldn't reach the Pi (host down, key not authorised,
  Tailscale not up).
- `RigCommandError` — connected, but the switch command itself failed.

---

## Notes

- **Connection reuse:** repeated calls reuse one SSH connection (via SSH
  ControlMaster), so tight loops are fast and don't spam the Pi with logins.
- **State persistence:** the Pi-side script latches the GPIO level and exits,
  so the switch holds its position between calls.
- **What "on/off" means:** `rf_on` = RF path connected = BLE allowed;
  `rf_off` = path broken = BLE blocked. The GPIO/IR details are handled on the
  Pi so callers never see them.

---

## Roadmap

This first version covers on/off control. Planned next:
- Pattern running (cycle on/off on a schedule) as a library call.
- Reading back switch state.
- Optional analysis helpers.
