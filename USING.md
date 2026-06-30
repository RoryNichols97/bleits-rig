# Using bleits in your own tests

This shows how to drop rig control into a larger test program. If your machine
can already `ssh sava@<rig-host>`, you need nothing more than the installed
package — `from bleits import Interrupter` and call the methods wherever you
need them.

## Install

```bash
pip install git+https://github.com/<org>/bleits-rig.git
```

Prerequisites: your machine can reach the rig over SSH/Tailscale (test it with
`ssh sava@<rig-host> "echo ok"`), and the Pi-side script is deployed (see
`pi/README.md`).

---

## 1. One step in a bigger test

The simplest case — BLE off/on is just one action among many in your own flow:

```python
from bleits import Interrupter

def my_big_test():
    set_up_dut()
    run_first_part()

    rig = Interrupter("mbed-rpi-004")
    rig.rf_off()                 # drop the BLE link
    check_device_handles_dropout()
    rig.rf_on()                  # restore it
    rig.close()                  # optional: tidy the connection

    run_final_part()
```

---

## 2. "Do this with BLE off" — the safe pattern

`disconnected()` turns RF off for the block and **guarantees it back on
afterwards, even if your code raises**. This is the recommended way to wrap a
step, because a failure can't leave the rig stuck disconnected for the rest of
your run or the next person.

```python
from bleits import Interrupter

rig = Interrupter("mbed-rpi-004")

with rig.disconnected():
    # BLE is blocked in here
    assert_app_shows_disconnected()
    wait_for_reconnect_attempt()
# BLE is allowed again here — even if an assert above failed
```

---

## 3. Inside a pytest suite (as a fixture)

If you write tests in pytest, expose the rig as a fixture so every test can use
it and it's always cleaned up:

```python
import pytest
from bleits import Interrupter

@pytest.fixture
def rig():
    r = Interrupter("mbed-rpi-004")
    yield r
    r.rf_on()      # leave the rig connected after each test
    r.close()

def test_app_recovers_from_dropout(rig):
    with rig.disconnected():
        trigger_app_action()
    assert app_reconnected_within(seconds=10)

def test_repeated_dropouts(rig):
    for _ in range(5):
        with rig.disconnected():
            brief_pause()
        assert still_healthy()
```

---

## 4. A quick cycling pattern from your script

For short, ad-hoc interruption patterns run from your machine:

```python
rig = Interrupter("mbed-rpi-004")
rig.run_pattern(off_s=10, on_s=10, cycles=20)     # 20 cycles of 10s off / 10s on
# or by total time:
rig.run_pattern(off_s=40, on_s=40, duration_s=3600)
```

This loops on your machine, so it ties up your script for the duration and
stops if your machine sleeps. For long unattended runs, hand a profile to the
Pi instead (next section).

---

## 5. A long, unattended run on the Pi

For runs that must survive your machine sleeping or disconnecting, launch a
named YAML profile on the Pi. It runs autonomously; your script can fire it and
walk away.

```python
rig = Interrupter("mbed-rpi-004")

log_path = rig.run_profile("BLE_Interruption_Pattern_Weekend1")
print("running on the Pi, logging to", log_path)

# later, from anywhere that can reach the rig:
rig.is_running()        # True / False
print(rig.tail_log(30)) # last 30 log lines
rig.stop_pattern()      # end it early and leave the rig safe
```

---

## Things to know

- **One rig per object.** Running several rigs is just several Interrupters:
  `Interrupter("rig-a")`, `Interrupter("rig-b")`. They're independent.
- **No locking yet.** If two programs drive the same rig at once they'll fight
  over the switch. For now, coordinate so one test uses a rig at a time.
- **Errors are typed.** Catch `RigConnectionError` (can't reach the rig) or the
  base `RigError` (anything rig-related) if you want to handle failures
  gracefully in a larger suite:

  ```python
  from bleits import Interrupter, RigError

  try:
      rig = Interrupter("mbed-rpi-004")
      rig.rf_off()
  except RigError as e:
      skip_or_flag_test(f"rig unavailable: {e}")
  ```
