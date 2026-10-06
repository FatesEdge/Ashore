"""Cross-platform process smoke check for Ashore startup.

The target must stay alive long enough to reach either the main window or the
environment-recovery UI. The process is then terminated by the test harness.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('Ashore.py')
    if target.suffix == '.py':
        command = [sys.executable, str(target)]
    else:
        command = [str(target)]

    environment = os.environ.copy()
    environment.setdefault('QT_QPA_PLATFORM', 'offscreen')

    process = subprocess.Popen(
        command,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(5)
        result = process.poll()
        if result is not None:
            stdout, stderr = process.communicate(timeout=2)
            raise RuntimeError(
                f'Ashore exited too early with status {result}.\n'
                f'--- stdout ---\n{stdout}\n'
                f'--- stderr ---\n{stderr}')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
