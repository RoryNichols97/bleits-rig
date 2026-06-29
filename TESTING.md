# Testing

Two layers of testing for this package.

## 1. Automated tests (no Pi needed)

These check the library's own logic by faking the SSH connection — they prove
the on/off commands, the `disconnected()` restore-on-crash behaviour, and clean
error handling, without touching real hardware.

```bash
pip install -e ".[dev]"
pytest
```

All tests should pass. These run on every push via GitHub Actions (see
`.github/workflows/ci.yml`), so a future change can't silently break the logic.

## 2. Manual smoke test (real Pi) — DO THIS BEFORE SHARING

The automated tests can't prove the actual switch flips. This walkthrough does.
Run it once on a fresh checkout before letting anyone else use the package.

### Prerequisites
- Tailscale up; `ssh sava@mbed-rpi-004` works in your terminal without a password.
- The Pi-side script is installed (see README "One-time Pi setup").

### Steps

**a. Fresh install**
```bash
git clone <your-repo-url>
cd bleits-rig
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -e .
```

**b. Confirm the connection + Pi script work directly**
```bash
ssh sava@mbed-rpi-004 "bash ~/bleits/pi/rf_switch.sh off"   # expect: RF off
ssh sava@mbed-rpi-004 "bash ~/bleits/pi/rf_switch.sh on"    # expect: RF on
```
Watch/listen for the switch actuating. If this works, the hardware chain is good.

**c. Confirm through the library**
```python
python
>>> from bleits import Interrupter
>>> i = Interrupter("mbed-rpi-004")
>>> i.rf_off()      # switch should actuate to blocked
>>> i.rf_on()       # switch should actuate to allowed
>>> i.close()
```

**d. Confirm the safe-restore behaviour**
```python
>>> from bleits import Interrupter
>>> i = Interrupter("mbed-rpi-004")
>>> try:
...     with i.disconnected():     # RF goes off
...         raise RuntimeError("pretend the test crashed")
... except RuntimeError:
...     pass
>>> # RF should now be back ON despite the crash — verify the switch state
```

**e. Confirm it fails cleanly on a bad host**
```python
>>> from bleits import Interrupter, RigConnectionError
>>> bad = Interrupter("no-such-host")
>>> try:
...     bad.rf_on()
... except RigConnectionError as e:
...     print("clean failure:", e)
```

### Pass criteria
- [ ] Switch physically actuates on `rf_off()` / `rf_on()`
- [ ] State restores to ON after a crash inside `disconnected()`
- [ ] Bad host raises `RigConnectionError` with a helpful message (no ugly traceback)
- [ ] Repeated calls in a loop are fast (connection reuse working)

Once all four are ticked, it's safe to tag a release and share with the team.
