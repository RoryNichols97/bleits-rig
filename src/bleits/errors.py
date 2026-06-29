"""Exceptions raised by the bleits rig library."""


class RigError(Exception):
    """Base class for all rig errors."""


class RigConnectionError(RigError):
    """Could not reach the rig over SSH (host down, key not accepted,
    Tailscale not up, etc.)."""


class RigCommandError(RigError):
    """The rig accepted the connection but the switch command failed
    (e.g. the Pi-side script returned an error)."""
