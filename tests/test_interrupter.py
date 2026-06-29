"""
Tests for the bleits Interrupter — these run WITHOUT a real Pi.

They check the library's own logic (does it construct correctly, call the
right command, fail cleanly, restore state) by faking the SSH transport.
The one thing they can't check is the real Pi switching — that's the manual
smoke test in TESTING.md.

Run with:   pytest
"""

import pytest

from bleits import Interrupter, RigConnectionError
from bleits.transport import SSHTransport
from bleits.errors import RigError


class FakeTransport:
    """Stand-in for SSHTransport that records commands instead of running
    them over SSH. Lets us test the Interrupter logic with no network."""

    def __init__(self, fail=False):
        self.commands = []
        self.closed = False
        self.fail = fail

    def run(self, command):
        if self.fail:
            raise RigConnectionError("simulated connection failure")
        self.commands.append(command)
        return "RF ok"

    def close(self):
        self.closed = True


def make_interrupter(fail=False):
    itp = Interrupter("test-host")
    itp._transport = FakeTransport(fail=fail)  # swap in the fake
    return itp


# --- construction ---------------------------------------------------

def test_constructs_with_defaults():
    itp = Interrupter("mbed-rpi-004")
    assert itp.host == "mbed-rpi-004"
    assert itp.user == "sava"


def test_repr_is_readable():
    itp = Interrupter("mbed-rpi-004")
    assert "mbed-rpi-004" in repr(itp)


# --- the core actions send the right command -------------------------

def test_rf_off_sends_off():
    itp = make_interrupter()
    itp.rf_off()
    assert itp._transport.commands[-1].endswith("off")


def test_rf_on_sends_on():
    itp = make_interrupter()
    itp.rf_on()
    assert itp._transport.commands[-1].endswith("on")


# --- the disconnected() context manager ------------------------------

def test_disconnected_turns_off_then_back_on():
    itp = make_interrupter()
    with itp.disconnected():
        # inside the block, the last command should be 'off'
        assert itp._transport.commands[-1].endswith("off")
    # after the block, it should have turned back on
    assert itp._transport.commands[-1].endswith("on")


def test_disconnected_restores_even_on_error():
    itp = make_interrupter()
    with pytest.raises(ValueError):
        with itp.disconnected():
            raise ValueError("simulated test crash")
    # despite the crash, RF must have been turned back on
    assert itp._transport.commands[-1].endswith("on")


# --- the with-block cleanup ------------------------------------------

def test_context_manager_closes_connection():
    itp = make_interrupter()
    with itp:
        itp.rf_off()
    assert itp._transport.closed is True


# --- errors propagate cleanly ----------------------------------------

def test_connection_error_propagates():
    itp = make_interrupter(fail=True)
    with pytest.raises(RigConnectionError):
        itp.rf_on()


def test_errors_are_rigerror_subclasses():
    # so callers can catch everything with one `except RigError`
    assert issubclass(RigConnectionError, RigError)


# --- transport builds a sane command ---------------------------------

def test_transport_control_path_is_per_target():
    a = SSHTransport("host-a", "sava")
    b = SSHTransport("host-b", "sava")
    assert a._control_path != b._control_path
