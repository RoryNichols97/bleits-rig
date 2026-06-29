"""Tests for the interactive manual session - no Pi needed."""

import builtins

from bleits import manual_session


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.closed = False

    def run(self, command):
        self.commands.append(command)
        return "ok"

    def close(self):
        self.closed = True


def run_with_inputs(monkeypatch, inputs):
    fake = FakeTransport()
    from bleits.rig import Interrupter
    real_init = Interrupter.__init__

    def patched_init(self, host, user="sava", pi_script=None):
        real_init(self, host, user=user)
        self._transport = fake

    monkeypatch.setattr(Interrupter, "__init__", patched_init)

    it = iter(inputs)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr(builtins, "input", fake_input)
    manual_session("test-host")
    return fake


def test_off_then_on_sends_both(monkeypatch):
    fake = run_with_inputs(monkeypatch, ["f", "o", "q"])
    sent = " ".join(fake.commands)
    assert "off" in sent
    assert "on" in sent


def test_quit_leaves_rig_on(monkeypatch):
    fake = run_with_inputs(monkeypatch, ["f", "q"])
    assert fake.commands[-1].endswith("on")


def test_closes_connection(monkeypatch):
    fake = run_with_inputs(monkeypatch, ["q"])
    assert fake.closed is True


def test_toggle_alternates(monkeypatch):
    fake = run_with_inputs(monkeypatch, ["f", "t", "q"])
    assert any(c.endswith("off") for c in fake.commands)
    assert fake.commands[-1].endswith("on")


def test_unknown_command_is_ignored(monkeypatch):
    fake = run_with_inputs(monkeypatch, ["xyz", "q"])
    assert fake.commands[-1].endswith("on")
