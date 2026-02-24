import argparse
import logging
import subprocess
import time
import re
import pexpect

from bluekit.report import report_vulnerable, report_not_vulnerable, report_error
from bluekit.constants import LOG_FILE

HCITOOL_INFO = "sudo hcitool info {target}"
BLUETOOTHCTL_REMOVE = "sudo bluetoothctl remove {target}"
BLUETOOTHCTL_PAIR = "sudo bluetoothctl pair {target}"
BLUETOOTHCTL_CONNECT = "sudo bluetoothctl connect {target}"

INSTRUCTIONS = """
1. Have your target device in discoverable and pairable mode. Always keep it that way
2. Once the prompt to connect appears - press yes
3. If device is vulnerable it would pair and connect.
"""

"""
Ubuntu 2204 has bt-agent and PulseAudio controlling the agent at the same time. Hence, even when bt-agent set the agent to NoInputNoOutput, this gets overwritten if we run bluetoothctl using pipes. Hence, we need to use pseudo terminal so that bluetoothctl recognises NINO set by bt-agent as default.
This was not a problem when running bluekit_nino_check.py on Ubuntu 24.04, since it only has bt-agent providing agent for bluetooth; bluetoothctl run inside pipes will fall back to whatever agent set by bt-agent.
"""
def strip_ansi(text):
    """Remove ANSI escape codes from output."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


def run_with_pty(command, timeout=30):
    """Run a command with a real PTY (like a manual terminal), return output."""
    child = pexpect.spawn('/bin/bash', ['-c', command], encoding='utf-8', timeout=timeout)
    child.expect(pexpect.EOF, timeout=timeout)
    output = strip_ansi(child.before)
    child.close()
    return output, child.exitstatus


def check_nino(target):
    bt_agent = None
    try:
        # Terminal 1: sudo bt-agent -c NoInputNoOutput
        bt_agent = subprocess.Popen(
            "sudo bt-agent -c NoInputNoOutput",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        time.sleep(2)

        # Terminal 2: Run commands one by one

        # Step 1: bluetoothctl remove (clean slate)
        output, _ = run_with_pty(BLUETOOTHCTL_REMOVE.format(target=target), timeout=10)
        print("Remove: {}".format(output.strip()))
        time.sleep(1)

        # Step 2: sudo hcitool info (populate device cache)
        output, _ = run_with_pty(HCITOOL_INFO.format(target=target), timeout=15)
        print("Hcitool info: done")
        time.sleep(1)

        # Step 3: sudo bluetoothctl pair
        output, exitcode = run_with_pty(BLUETOOTHCTL_PAIR.format(target=target), timeout=30)
        print("Pair output: {}".format(output.strip()))

        if "AuthenticationFailed" in output or "AuthenticationCanceled" in output:
            report_not_vulnerable("Not vulnerable — device rejected NiNo pairing")
            return
        if "Pairing successful" not in output and "AlreadyExists" not in output:
            report_error("Pairing failed: {}".format(output.strip()))
            return

        time.sleep(1)

        # Step 4: sudo bluetoothctl connect
        output, exitcode = run_with_pty(BLUETOOTHCTL_CONNECT.format(target=target), timeout=15)
        print("Connect output: {}".format(output.strip()))

        if "Connection successful" in output:
            report_vulnerable(
                "Vulnerable to NiNo attack as allows NiNo devices to connect (Unauthenticated keys)"
            )
            # Cleanup
            run_with_pty(BLUETOOTHCTL_REMOVE.format(target=target), timeout=10)
        elif "Failed to connect" in output:
            report_not_vulnerable("Not vulnerable to NiNo attack as doesn't allow to connect")
        else:
            report_error("Unexpected connect result: {}".format(output.strip()))

    except Exception as e:
        logging.info("nino_check.py -> Error: {}".format(str(e)))
        report_error("nino_check.py -> error: {}".format(str(e)))
    finally:
        if bt_agent is not None:
            bt_agent.terminate()
            try:
                bt_agent.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                bt_agent.kill()
        logging.info("nino_check.py -> Finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', required=False, type=str, help="target MAC address")
    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

    if args.target:
        print(INSTRUCTIONS)
        check_nino(args.target)
    else:
        parser.print_help()