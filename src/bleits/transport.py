"""
SSH transport for talking to a rig's Raspberry Pi.

Deliberately shells out to the system `ssh` command rather than using a
Python SSH library. This means it uses each person's existing SSH key,
~/.ssh/config, and known_hosts automatically — exactly as if they typed
`ssh sava@host` themselves. No passwords or secrets ever touch this code.

Connections are reused via SSH "ControlMaster" multiplexing: the first
call opens a master connection, and subsequent calls piggyback on it
(fast, and doesn't hammer the Pi with fresh logins). The master is kept
alive briefly after the last call, then closed.
"""

import os
import subprocess
import tempfile

from .errors import RigConnectionError, RigCommandError


class SSHTransport:
    def __init__(self, host, user="sava", connect_timeout=10, persist_seconds=60):
        self.host = host
        self.user = user
        self.target = f"{user}@{host}"
        self.connect_timeout = connect_timeout

        # A per-target control socket so multiple Rig objects to different
        # hosts don't clash, and repeated calls to the same host reuse one
        # connection.
        safe = f"{user}-{host}".replace("/", "_")
        self._control_path = os.path.join(
            tempfile.gettempdir(), f"bleits-{safe}.sock"
        )

        self._opts = [
            "-o", "BatchMode=yes",                 # never prompt; fail fast instead
            "-o", f"ConnectTimeout={connect_timeout}",
            "-o", "ControlMaster=auto",
            "-o", f"ControlPath={self._control_path}",
            "-o", f"ControlPersist={persist_seconds}",
        ]

    def run(self, command):
        """Run a shell command on the Pi. Returns stdout (stripped).
        Raises RigConnectionError or RigCommandError on failure."""
        full = ["ssh", *self._opts, self.target, command]
        try:
            result = subprocess.run(
                full, capture_output=True, text=True,
                timeout=self.connect_timeout + 15,
            )
        except subprocess.TimeoutExpired as e:
            raise RigConnectionError(
                f"Timed out talking to {self.target}. Is the Pi up and is "
                f"Tailscale connected?"
            ) from e
        except FileNotFoundError as e:
            raise RigConnectionError(
                "The 'ssh' command was not found on this machine."
            ) from e

        if result.returncode != 0:
            err = (result.stderr or "").strip()
            # ssh itself uses 255 for connection-level failures
            if result.returncode == 255:
                raise RigConnectionError(
                    f"Could not connect to {self.target}: {err or 'unknown SSH error'}. "
                    f"Check the hostname, that your SSH key is authorised on the Pi, "
                    f"and that Tailscale is up."
                )
            raise RigCommandError(
                f"Command failed on {self.target} (exit {result.returncode}): "
                f"{err or 'no error output'}"
            )
        return (result.stdout or "").strip()

    def close(self):
        """Tear down the shared master connection, if one is open.
        Safe to call even if nothing is connected."""
        try:
            subprocess.run(
                ["ssh", *self._opts, "-O", "exit", self.target],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            # Closing is best-effort; never raise from cleanup.
            pass
