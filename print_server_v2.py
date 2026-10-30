# Optimized Print Server Example
# This shows how to update your existing print servers for better efficiency

import argparse
import ctypes
import json
import logging
import os
import socket
import sys
import time
import traceback
import requests
from escpos.printer import Network

# Configuration
DOMAIN = "potteryapp.greenwichhouse.org"
POLL_INTERVAL = 60  # 60 seconds
LOCATIONS = ['Barrow', 'Chelsea', 'Greenwich']

# Each location's print server holds one localhost port for as long as it runs, so a
# second copy started at the same location (e.g. the .bat double-clicked twice) sees the
# port taken and exits instead of fetching receipts too. The ports sit below Windows'
# ephemeral range (49152+), so an outgoing connection can't be holding one by chance.
SINGLE_INSTANCE_PORTS = {'Barrow': 48631, 'Chelsea': 48632, 'Greenwich': 48633}

# Everything the print server prints is also written to one log file per day, kept for
# this many days, so an outage can be looked into after the window has been closed.
LOG_DAYS_KEPT = 60

# A check that starts this many seconds later than planned means the program itself
# wasn't running in between: the computer was asleep, or the window was paused.
LATE_CHECK_SECONDS = 120


def parse_args(argv=None):
    # The same exe runs at every location. run_<location>_print_server.bat (written by
    # build_exe.bat) passes the location and its receipt printer's static IP, so a new
    # printer IP only needs that .bat edited, not a rebuild.
    parser = argparse.ArgumentParser(description='Poll the pottery app for receipts and print them.')
    parser.add_argument('location', choices=LOCATIONS, help='location this print server runs at')
    parser.add_argument('--printer-ip', required=True, help="static IP of the location's receipt printer")
    return parser.parse_args(argv)


def log_dir(location):
    # Next to the secret key file: the folder the location's .bat file is run from
    return f'./{location.lower()}_print_server_logs'


class DailyLogTee:
    """
    Stand-in for sys.stdout/sys.stderr that writes everything to the console and to
    <log dir>/<prefix>_YYYY-MM-DD.log, with the time at the start of each line. A new file
    starts each day, and files older than LOG_DAYS_KEPT days are deleted.
    """

    def __init__(self, console, directory, prefix):
        self.console = console
        self.directory = directory
        self.prefix = prefix
        self.date = None
        self.file = None
        self.at_line_start = True
        self.open_error_shown = False

    def _today_file(self):
        today = time.strftime('%Y-%m-%d')
        if today != self.date:
            if self.file:
                self.file.close()
                self.file = None
            try:
                os.makedirs(self.directory, exist_ok=True)
                self.file = open(os.path.join(self.directory, f'{self.prefix}_{today}.log'), 'a', encoding='utf-8')
            except OSError as e:
                # Leave self.date unset so the next write tries again; say so only once
                if not self.open_error_shown:
                    self._to_console(f"Could not open a log file in {self.directory}: {e}\n")
                    self.open_error_shown = True
                return None
            self.date = today
            self.open_error_shown = False
            prune_old_logs(self.directory, self.prefix, LOG_DAYS_KEPT)
        return self.file

    def _to_console(self, text):
        if self.console is None:
            return
        try:
            self.console.write(text)
            self.console.flush()
        except (OSError, ValueError):
            pass

    def write(self, text):
        log_file = self._today_file()
        if log_file:
            stamped = []
            for line in text.splitlines(keepends=True):
                if self.at_line_start:
                    stamped.append(time.strftime('%H:%M:%S '))
                stamped.append(line)
                self.at_line_start = line.endswith('\n')
            try:
                # Write the file first and flush every time, so the log is complete up to
                # the moment the program stops, however it stops
                log_file.write(''.join(stamped))
                log_file.flush()
            except (OSError, ValueError):
                pass
        self._to_console(text)
        return len(text)

    def flush(self):
        if self.file:
            try:
                self.file.flush()
            except (OSError, ValueError):
                pass
        if self.console is not None:
            try:
                self.console.flush()
            except (OSError, ValueError):
                pass


def prune_old_logs(directory, prefix, days_kept):
    cutoff = time.strftime('%Y-%m-%d', time.localtime(time.time() - days_kept * 24 * 60 * 60))
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        date = name[len(prefix) + 1:-len('.log')]
        if name.startswith(prefix + '_') and name.endswith('.log') and len(date) == 10 and date < cutoff:
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                pass


def start_logging(location):
    tee = DailyLogTee(sys.stdout, log_dir(location), f'{location.lower()}_print_server')
    sys.stdout = tee
    sys.stderr = tee
    # python-escpos calls logging.basicConfig() on import, which points the root logger at
    # the original stderr; send its messages (e.g. "Network device ... not found") here too
    logging.basicConfig(stream=tee, force=True)
    return tee


def disable_console_quick_edit():
    """
    Turn off QuickEdit Mode for this console window. With it on, a click inside the
    window starts selecting text, and Windows then stops the program the next time it
    prints anything, until someone presses a key in the window. The window shows no sign
    of this except the selection, so the print server looks like it has silently stopped.
    """
    if os.name != 'nt':
        return
    ENABLE_QUICK_EDIT_MODE = 0x0040
    ENABLE_EXTENDED_FLAGS = 0x0080  # required for the QuickEdit flag to take effect
    STD_INPUT_HANDLE = -10
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            print("Could not read the console mode; QuickEdit Mode left as it is")
            return
        if kernel32.SetConsoleMode(handle, (mode.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS):
            print("Turned off QuickEdit Mode, so clicking in this window can't pause printing")
        else:
            print("Could not turn off QuickEdit Mode")
    except Exception as e:
        print(f"Could not turn off QuickEdit Mode: {e}")


def acquire_single_instance_lock(location):
    """
    Bind this location's localhost port and return the socket, or None if another
    print server for this location already holds it. Keep the socket open (referenced)
    for as long as the print server runs; the OS releases it when the process exits.
    """
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        # Windows only: stop another process from binding the same port with SO_REUSEADDR
        lock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        lock.bind(('127.0.0.1', SINGLE_INSTANCE_PORTS[location]))
    except OSError as e:
        # Usually another copy holds the port, but Windows can also reserve port ranges
        # (Hyper-V, WSL), so show the actual error
        print(f"Could not hold local port {SINGLE_INSTANCE_PORTS[location]}: {e}")
        lock.close()
        return None
    return lock


def load_secret_key(location):
    secret_key = os.environ.get(f'{location.upper()}_PRINT_SERVER_SECRET_KEY', '')
    if not secret_key:
        print(f"Trying to read secret key from file: ./{location.lower()}_print_server_secret_key.txt")
        try:
            with open(f'./{location.lower()}_print_server_secret_key.txt', 'r') as f:
                secret_key = f.read().strip()
        except FileNotFoundError:
            print(f"Could not find secret key file. Please set environment variable.")
            sys.exit(1)
    return secret_key


def spool_path(location):
    # Next to the secret key file: the folder the location's .bat file is run from
    return f'./{location.lower()}_unprinted_receipts.json'


def load_spool(path):
    """
    Load receipts that were fetched but not yet printed when the print server last stopped.
    The server marks receipts printed when it hands them out, so this file is the only
    remaining copy of them.
    """
    try:
        with open(path, 'r') as f:
            spool = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        # Keep the unreadable file for a person to look at rather than overwriting it
        aside = f"{path}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
        print(f"Could not read unprinted receipts from {path} ({e}); moved it to {aside}")
        try:
            os.replace(path, aside)
        except OSError as move_error:
            print(f"Could not move {path} aside: {move_error}")
        return []
    if not isinstance(spool, list):
        print(f"Ignoring {path}: expected a list of receipts")
        return []
    return [job for job in spool if isinstance(job, dict)]


def save_spool(path, spool):
    """Write the unprinted receipts to disk, replacing the file atomically."""
    try:
        tmp_path = f'{path}.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(spool, f)
        os.replace(tmp_path, path)
    except OSError as e:
        print(f"Could not save unprinted receipts to {path}: {e}")


def fetch_print_jobs_optimized(location, secret_key):
    """
    Fetch print jobs using the optimized endpoint
    """
    try:
        print(f"Fetching print jobs for {location}")
        params = {
            'location': location  # Optional: can be omitted for backward compatibility
        }

        # Use the optimized endpoint. The key goes in a header, not the query string,
        # because the hosting platform's router logs every request's full URL.
        response = requests.get(
            f'https://{DOMAIN}/api/printjobs_v2/',  # New endpoint
            params=params,
            headers={'X-Print-Server-Key': secret_key},
            timeout=30  # Add timeout
        )

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Received {data.get('count', 0)} jobs for {data.get('location', location)}")
            jobs = data.get('unprinted_receipts', [])
            return [job for job in jobs if isinstance(job, dict)] if isinstance(jobs, list) else []
        elif response.status_code == 403:
            print("Authentication failed - check secret key")
            return None
        else:
            print(f"Server error: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection failed - server may be down")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching jobs: {e}")
        return None


def print_to_receipt_printer_optimized(jobs, printer_ip):
    """
    Print each job, returning the ids of the jobs that no longer need printing: those
    sent to the printer, and those with no text (retrying can't help them).
    """
    if not jobs:
        return []

    print(f"Attempting to print {len(jobs)} jobs")
    done_job_ids = []

    for job in jobs:
        job_id = job.get('id')
        print_text = job.get('print_string', '')

        if not print_text:
            print(f"No print text for job {job_id}; skipping it")
            done_job_ids.append(job_id)
            continue

        try:
            # Initialize printer with timeout
            printer = Network(printer_ip, timeout=10)

            if not printer.is_usable():
                raise Exception("Printer not usable")

            # Print with consistent formatting
            printer.set(
                align='center',
                double_height=True,
                double_width=True,
            )
            printer.text(print_text)
            printer.cut()
            printer.close()

            done_job_ids.append(job_id)
            print(f"Successfully printed job {job_id}")

        except Exception as e:
            print(f"Failed to print job {job_id}: {e}")

    return done_job_ids


def poll_once(spool, spool_file, location, printer_ip, secret_key):
    """
    Fetch new receipts, then try to print everything not yet printed. Returns the
    receipts still unprinted, and whether the fetch succeeded.

    Earlier unprinted receipts are retried even when the fetch fails, since the
    printer is on the local network and may be reachable while the server is not.
    """
    print_jobs = fetch_print_jobs_optimized(location, secret_key)
    if print_jobs:
        spooled_ids = {job.get('id') for job in spool}
        spool = spool + [job for job in print_jobs if job.get('id') not in spooled_ids]
        # The server has already marked these printed, so save them before printing in
        # case the window is closed (or the printer hangs) partway through.
        save_spool(spool_file, spool)

    if spool:
        print(f"Processing {len(spool)} print jobs")
        done_job_ids = print_to_receipt_printer_optimized(spool, printer_ip)
        spool = [job for job in spool if job.get('id') not in done_job_ids]
        print(f"Done with {len(done_job_ids)} jobs; {len(spool)} left to retry")
        save_spool(spool_file, spool)
    else:
        print("No print jobs found")

    return spool, print_jobs is not None


def main(argv=None):
    """
    Main print server loop with improved error handling
    """
    args = parse_args(argv)
    location = args.location
    printer_ip = args.printer_ip

    start_logging(location)
    print(f"Log files: {os.path.abspath(log_dir(location))}")
    disable_console_quick_edit()

    instance_lock = acquire_single_instance_lock(location)
    if instance_lock is None:
        print(f"Another {location} print server is probably already running on this computer "
              f"(it would hold local port {SINGLE_INSTANCE_PORTS[location]}).")
        print("Close that print server's window first, or keep using it. This one will not print anything.")
        print("If no other copy is running, the error above says what is holding the port.")
        sys.exit(1)

    secret_key = load_secret_key(location)
    spool_file = spool_path(location)
    spool = load_spool(spool_file)

    print(f"Starting optimized print server for {location}")
    print(f"Polling interval: {POLL_INTERVAL} seconds")
    print(f"Printer IP: {printer_ip}")
    if spool:
        print(f"Loaded {len(spool)} unprinted receipts from {spool_file}")

    consecutive_failures = 0
    max_consecutive_failures = 5
    next_check_due = None

    try:
        while True:
            wait = POLL_INTERVAL
            try:
                print(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
                if next_check_due is not None and time.time() - next_check_due > LATE_CHECK_SECONDS:
                    print(f"This check is {(time.time() - next_check_due) / 60:.0f} minutes late. The program was "
                          f"not running in between: the computer was probably asleep, or this window was paused.")
                if spool:
                    print(f"Retrying {len(spool)} unprinted earlier jobs: {[job.get('id') for job in spool]}")

                spool, fetched = poll_once(spool, spool_file, location, printer_ip, secret_key)

                if fetched:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    print(f"Failed to fetch jobs (attempt {consecutive_failures})")
                    if consecutive_failures >= max_consecutive_failures:
                        print("Too many consecutive failures. Increasing wait time.")
                        wait = POLL_INTERVAL * 5  # Wait longer after failures
                        consecutive_failures = 0  # Reset counter

            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                traceback.print_exc()
                # poll_once saves the spool after every change, so the file is current
                spool = load_spool(spool_file)

            # Wait for next polling cycle
            print(f"Waiting {wait} seconds until next check...")
            next_check_due = time.time() + wait
            time.sleep(wait)

    except KeyboardInterrupt:
        print("\nShutting down print server...")
    finally:
        instance_lock.close()


if __name__ == "__main__":
    main()
