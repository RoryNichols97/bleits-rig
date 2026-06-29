"""Tests for the Pi-side launcher (run_profile, is_running, etc.) - no Pi."""

import pytest

from bleits import Interrupter


class FakeTransport:
    def __init__(self, profile_exists=True):
        self.commands = []
        self.running = False
        self.profile_exists = profile_exists

    def run(self, command):
        self.commands.append(command)
        if "test -f" in command and "echo OK" in command:
            return "OK" if self.profile_exists else "MISSING"
        if "kill -0" in command:
            return "RUNNING" if self.running else "STOPPED"
        if "ls " in command and ".yaml" in command:
            return ("/home/sava/ble_interruptor/patterns/TC1_quick.yaml\n"
                    "/home/sava/ble_interruptor/patterns/BLE_Interruption_Sweep.yaml")
        if "setsid" in command and "cat .bleits_current_run" in command:
            self.running = True
            return "12345 /home/sava/ble_interruptor/logs/20260629_163000_TC1_quick.log"
        if "tail -n" in command:
            return "log line one\nlog line two"
        if "kill " in command:
            self.running = False
            return ""
        return ""

    def close(self):
        pass


def make(profile_exists=True):
    i = Interrupter("test-host")
    i._transport = FakeTransport(profile_exists=profile_exists)
    return i


def test_list_profiles_strips_extension():
    i = make()
    profiles = i.list_profiles()
    assert "TC1_quick" in profiles
    assert all(not p.endswith(".yaml") for p in profiles)


def test_run_profile_returns_log_path():
    i = make()
    log = i.run_profile("TC1_quick")
    assert log.endswith(".log")


def test_run_profile_marks_running():
    i = make()
    assert i.is_running() is False
    i.run_profile("TC1_quick")
    assert i.is_running() is True


def test_run_profile_missing_raises():
    i = make(profile_exists=False)
    with pytest.raises(RuntimeError):
        i.run_profile("does_not_exist")


def test_cannot_launch_two_at_once():
    i = make()
    i.run_profile("TC1_quick")
    with pytest.raises(RuntimeError):
        i.run_profile("BLE_Interruption_Sweep")


def test_stop_pattern_leaves_rig_on():
    i = make()
    i.run_profile("TC1_quick")
    i.stop_pattern()
    assert i._transport.commands[-1].endswith("on")


def test_tail_log_returns_text():
    i = make()
    i.run_profile("TC1_quick")
    out = i.tail_log(5)
    assert "log line" in out


