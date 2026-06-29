# Pi-side scripts

These run **on the rig''s Raspberry Pi**, not on your laptop. The `bleits`
Python package (in `../src/bleits`) talks to them over SSH.

| File | What it does |
|---|---|
| `rf_switch.sh` | Sets GPIO 17 to switch the RF path on/off and exits with the level latched. Called by `Interrupter.rf_on()` / `rf_off()`. |
| `pattern_runner.py` | Runs a YAML interruption pattern (cycles/holds/variable-cycles), logging every transition. Exits cleanly when the sequence finishes. Called by `Interrupter.run_profile()`. |
| `gpio_control.py` | The `IRControl` class `pattern_runner.py` uses to drive the IR emitter (and optionally mirror to the Pi''s ACT LED). |

## Deploying to a Pi

Assumes the Pi is reachable over SSH (e.g. Tailscale) as `sava@<host>`.

### 1. The switch script (for rf_on / rf_off)

```bash
ssh sava@<host> "mkdir -p ~/bleits/pi"
scp pi/rf_switch.sh sava@<host>:~/bleits/pi/
ssh sava@<host> "chmod +x ~/bleits/pi/rf_switch.sh"
```

`rf_switch.sh` uses `pinctrl` (or `raspi-gpio`), which ship with Pi OS.

### 2. The pattern runner (for run_profile)

Lives in `~/ble_interruptor/` on the Pi, with a venv and the YAML patterns:
Set up from scratch:

```bash
mkdir -p ~/ble_interruptor/patterns ~/ble_interruptor/logs
# from your laptop:
#   scp pi/pattern_runner.py sava@<host>:~/ble_interruptor/
#   scp pi/gpio_control.py   sava@<host>:~/ble_interruptor/
cd ~/ble_interruptor
python3 -m venv venv
./venv/bin/pip install gpiozero pyyaml lgpio
```

`lgpio` matters: without it gpiozero falls back to a slower native pin factory
(the `PinFactoryFallback` warnings) which is less reliable for long runs.

### 3. Pattern YAML format

```yaml
name: My_Test
gpio_pin: 17
active_low: false        # current hardware (true = old inverted convention)
default_state: closed
sequence:
  - type: cycle
    open_time: 40
    closed_time: 40
    duration: 3600
  - type: hold
    state: open
    duration: 60
  - type: variable_cycles
    disconnect_time: 10
    reconnect_times: [5, 10, 20, 40]
```

State: **open** = IR off = RF passes = BLE allowed; **closed** = IR on =
RF blocked = BLE blocked.

## Keeping in sync

The Pi runs whatever is on its SD card. This repo is the source of truth - if
you change a Pi-side script, change it here and re-deploy with `scp`.
