"""SSH transport for talking to a rig's Raspberry Pi."""

import os
import subprocess
import sys
import tempfile

from .errors import RigConnectionError, RigCommandError

_SUPPORTS_MULTIPLEXING = not sys.platform.startswith("win")


class SSHTransport:
    def __init__(self, host, user="sava", connect_timeout=10, persist_seconds=60):
        self.host = host
        self.user = user
        self.target = f"{user}@{host}"
        self.connect_timeout = connect_timeout
        self._multiplex = _SUPPORTS_MULTIPLEXING

        self._opts = [
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={connect_timeout}",
        ]

        if self._multiplex:
            safe = f"{user}-{host}".replace("/", "_")
            self._control_path = os.path.join(
                tempfile.gettempdir(), f"bleits-{safe}.sock"
            )
            self._opts += [
                "-o", "ControlMaster=auto",
                "-o", f"ControlPath={self._control_path}",
                "-o", f"ControlPersist={persist_seconds}",
            ]
        else:
            self._control_path = None

    def run(self, command):
        full = ["ssh", *self._opts, self.target, command]
        try:
            result = subprocess.run(
                full, capture_output=True, text=True,
                timeout=self.connect_timeout + 15,
            )
        except subprocess.TimeoutExpired as e:
            raise RigConnectionError(
                f"Timed out talking to {self.target}. Is the Pi up and is Tailscale connected?"
            ) from e
        except FileNotFoundError as e:
            raise RigConnectionError("The 'ssh' command was not found on this machine.") from e

        if result.returncode != 0:
            err = (result.stderr or "").strip()
            if result.returncode == 255:
                raise RigConnectionError(
                    f"Could not connect to {self.target}: {err or 'unknown SSH error'}. "
                    f"Check the hostname, your access, and that Tailscale is up."
                )
            raise RigCommandError(
                f"Command failed on {self.target} (exit {result.returncode}): {err or 'no error output'}"
            )
        return (result.stdout or "").strip()

    def close(self):
        if not self._multiplex:
            return
        try:
            subprocess.run(
                ["ssh", *self._opts, "-O", "exit", self.target],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            pass
