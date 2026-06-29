"""Tests for the laptop-side run_pattern - no Pi, no real waiting."""

import pytest

from bleits import Interrupter
from bleits.errors import RigError


class FakeTransport:
    def __init__(self, fail_after=None):
        self.commands = []
        self.closed = False
        self.fail_after = fail_after

    def run(self, command):
        if self.fail_after is not None and len(self.commands) >= self.fail_after:
            raise RigError("simulated failure")
        self.commands.append(command)
        return "ok"

    def close(self):
        self.closed = True


def make(fake=None):
    itp = Interrupter("test-host")
    itp._transport = fake or FakeTransport()
    return itp


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)


def test_runs_requested_number_of_cycles():
    itp = make()
    n = itp.run_pattern(off_s=1, on_s=1, cycles=5, verbose=False)
    assert n == 5
    offs = [c for c in itp._transport.commands if c.endswith("off")]
    assert len(offs) == 5


def test_leaves_rig_on_at_end():
    itp = make()
    itp.run_pattern(off_s=1, on_s=1, cycles=3, verbose=False)
    assert itp._transport.commands[-1].endswith("on")


def test_requires_exactly_one_stop_condition():
    itp = make()
    with pytest.raises(ValueError):
        itp.run_pattern(off_s=1, on_s=1, verbose=False)
    with pytest.raises(ValueError):
        itp.run_pattern(off_s=1, on_s=1, cycles=5, duration_s=10, verbose=False)


def test_duration_mode_runs_at_least_one_cycle():
    itp = make()
    n = itp.run_pattern(off_s=1, on_s=1, duration_s=0.001, verbose=False)
    assert n >= 1


def test_crash_midrun_still_leaves_on():
    fake = FakeTransport(fail_after=3)
    itp = make(fake)
    with pytest.raises(RigError):
        itp.run_pattern(off_s=1, on_s=1, cycles=10, verbose=False)
