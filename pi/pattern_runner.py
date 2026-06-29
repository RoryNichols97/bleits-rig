"""
Pattern runner for BLEITS - loads YAML test definitions and executes them.

- Timestamped logging of every state transition
- Per-cycle event logging in variable_cycles
- Graceful keyboard-interrupt exit, rig left in a safe (OPEN) state
- Clean exit when the sequence completes (no infinite hold), so the
  process can be launched detached and will finish on its own
- Command-line entry point: python3 pattern_runner.py <file> [--log-file PATH]
"""
import argparse
import logging
import sys
import time

import yaml

from gpio_control import IRControl

log = logging.getLogger(__name__)


def run_pattern(pattern_file: str, interactive: bool = False):
    """Load a YAML interruption pattern and execute it sequentially."""
    with open(pattern_file, "r") as f:
        pattern = yaml.safe_load(f)

    log.info(f"Loaded pattern: {pattern_file}")
    log.info(f"Pattern name: {pattern.get('name', '(unnamed)')}")

    ir = IRControl(
        pin=pattern["gpio_pin"],
        active_low=pattern.get("active_low", False),
    )

    if pattern.get("default_state", "closed") == "closed":
        ir.close()
    else:
        ir.open()

    if interactive and pattern.get("start_condition") == "user_trigger":
        input("Press ENTER to start test sequence...")

    log.info("=== Starting test sequence ===")
    try:
        for i, step in enumerate(pattern["sequence"], start=1):
            log.info(f"--- Step {i}: type={step['type']} ---")
            _handle_step(step, ir)

        log.info("=== Sequence complete ===")
        ir.open()
        log.info("Rig left OPEN (BLE allowed). Exiting.")
        ir.cleanup()
    except KeyboardInterrupt:
        log.info("Interrupted by user - leaving rig in OPEN (BLE-allowed) state")
        ir.open()
        ir.cleanup()


def _handle_step(step: dict, ir: IRControl):
    """Execute a single step from the YAML sequence."""
    if step["type"] == "hold":
        if step["state"] == "closed":
            ir.close()
        else:
            ir.open()
        duration = step.get("duration", 1_000_000)
        log.info(f"Holding {step['state']} for {duration}s")
        time.sleep(duration)

    elif step["type"] == "cycle":
        end_time = time.time() + step["duration"]
        cycle_count = 0
        log.info(
            f"Cycling for {step['duration']}s "
            f"(open={step['open_time']}s, closed={step['closed_time']}s)"
        )
        while time.time() < end_time:
            cycle_count += 1
            log.info(f"Cycle {cycle_count}: opening")
            ir.open()
            time.sleep(step["open_time"])
            log.info(f"Cycle {cycle_count}: closing")
            ir.close()
            time.sleep(step["closed_time"])
        log.info(f"Completed {cycle_count} cycles")

    elif step["type"] == "variable_cycles":
        log.info(
            f"Variable cycles: disconnect_time={step['disconnect_time']}s, "
            f"{len(step['reconnect_times'])} reconnect windows"
        )
        for i, reconnect_time in enumerate(step["reconnect_times"], start=1):
            disconnect_at = time.time()
            log.info(
                f"Cycle {i}/{len(step['reconnect_times'])}: "
                f"OPEN (disconnect_at={disconnect_at:.3f})"
            )
            ir.open()
            time.sleep(step["disconnect_time"])
            reconnect_at = time.time()
            log.info(
                f"Cycle {i}/{len(step['reconnect_times'])}: "
                f"CLOSE (reconnect_at={reconnect_at:.3f}, "
                f"holding for {reconnect_time}s)"
            )
            ir.close()
            time.sleep(reconnect_time)
    else:
        raise ValueError(f"Unknown step type: {step['type']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a BLEITS interruption pattern.")
    parser.add_argument("pattern_file", help="path to a YAML pattern file")
    parser.add_argument("--log-file", default=None, help="also write logs to this file")
    parser.add_argument("--interactive", action="store_true",
                        help="wait for ENTER before starting if the pattern requests it")
    args = parser.parse_args(argv)

    handlers = [logging.StreamHandler(sys.stdout)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    run_pattern(args.pattern_file, interactive=args.interactive)


if __name__ == "__main__":
    main()