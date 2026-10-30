# Tests for the Windows print client, print_server_v2.py. They mock the printer and HTTP.
# python-escpos is a print-client-only dependency (not in requirements.txt), so run with e.g.
#   uv run --with python-escpos --with requests python -m unittest test_print_server_v2
import contextlib
import ctypes
import io
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

try:
    import requests
    import print_server_v2
except ImportError:
    print_server_v2 = None

JOB = {'id': 7, 'print_string': 'SLIP 7'}


def ok_response(jobs):
    response = mock.Mock(status_code=200)
    response.json.return_value = {'unprinted_receipts': jobs, 'location': 'Chelsea', 'count': len(jobs)}
    return response


def working_printer():
    printer = mock.MagicMock()
    printer.return_value.is_usable.return_value = True
    return printer


def broken_printer():
    printer = mock.MagicMock()
    printer.return_value.is_usable.return_value = False
    return printer


@unittest.skipIf(print_server_v2 is None, 'needs python-escpos and requests')
class PrintClientTestCase(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.spool_file = os.path.join(self.dir.name, 'chelsea_unprinted_receipts.json')
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def patch(self, name, **kwargs):
        patcher = mock.patch.object(print_server_v2, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def poll(self, spool):
        return print_server_v2.poll_once(spool, self.spool_file, 'Chelsea', '10.0.0.1', 'chelsea-key')

    def saved_spool(self):
        with open(self.spool_file) as f:
            return json.load(f)


class FetchTests(PrintClientTestCase):

    def test_key_sent_in_header_not_query_string(self):
        get = self.patch('requests')
        get.get.return_value = ok_response([JOB])
        get.exceptions = requests.exceptions
        self.assertEqual(print_server_v2.fetch_print_jobs_optimized('Chelsea', 'chelsea-key'), [JOB])
        kwargs = get.get.call_args.kwargs
        self.assertEqual(kwargs['headers'], {'X-Print-Server-Key': 'chelsea-key'})
        self.assertNotIn('secret_key', kwargs['params'])

    def test_server_down_returns_none(self):
        bad_json = mock.Mock(status_code=200)
        bad_json.json.side_effect = ValueError('not json')
        for outcome in [requests.exceptions.ConnectionError('down'), requests.exceptions.Timeout('slow'),
                        mock.Mock(status_code=503), mock.Mock(status_code=403), bad_json]:
            with mock.patch.object(print_server_v2.requests, 'get', side_effect=[outcome]):
                self.assertIsNone(print_server_v2.fetch_print_jobs_optimized('Chelsea', 'chelsea-key'))


class SpoolTests(PrintClientTestCase):

    def test_failed_print_is_saved_to_disk(self):
        self.patch('Network', new=broken_printer())
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([JOB])):
            spool, fetched = self.poll([])
        self.assertTrue(fetched)
        self.assertEqual(spool, [JOB])
        self.assertEqual(self.saved_spool(), [JOB])
        self.assertEqual(print_server_v2.load_spool(self.spool_file), [JOB])

    def test_fetched_jobs_saved_before_printing(self):
        # The server marks receipts printed when it hands them out, so a window closed
        # mid-print must still find them on disk
        on_disk_while_printing = []
        printer = working_printer()
        printer.side_effect = lambda *args, **kwargs: on_disk_while_printing.append(self.saved_spool()) or mock.DEFAULT
        self.patch('Network', new=printer)
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([JOB])):
            spool, _ = self.poll([])
        self.assertEqual(on_disk_while_printing, [[JOB]])
        self.assertEqual(spool, [])
        self.assertEqual(self.saved_spool(), [])

    def test_spool_retried_while_server_down(self):
        printer = self.patch('Network', new=working_printer())
        with mock.patch.object(print_server_v2.requests, 'get', side_effect=requests.exceptions.ConnectionError('down')):
            spool, fetched = self.poll([JOB])
        self.assertFalse(fetched)
        self.assertEqual(spool, [])
        printer.return_value.text.assert_called_once_with('SLIP 7')

    def test_job_already_spooled_is_not_printed_twice(self):
        printer = self.patch('Network', new=working_printer())
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([JOB])):
            spool, _ = self.poll([JOB])
        self.assertEqual(spool, [])
        printer.return_value.text.assert_called_once_with('SLIP 7')

    def test_job_without_text_is_dropped(self):
        self.patch('Network', new=broken_printer())
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([{'id': 8, 'print_string': ''}])):
            spool, _ = self.poll([])
        self.assertEqual(spool, [])

    def test_missing_spool_file_is_empty(self):
        self.assertEqual(print_server_v2.load_spool(self.spool_file), [])

    def test_unreadable_spool_file_is_moved_aside(self):
        with open(self.spool_file, 'w') as f:
            f.write('{not json')
        self.assertEqual(print_server_v2.load_spool(self.spool_file), [])
        self.assertFalse(os.path.exists(self.spool_file))
        aside = [name for name in os.listdir(self.dir.name) if '.unreadable-' in name]
        self.assertEqual(len(aside), 1)


class MainLoopTests(PrintClientTestCase):

    def setUp(self):
        super().setUp()
        cwd = os.getcwd()
        os.chdir(self.dir.name)
        self.addCleanup(os.chdir, cwd)
        self.patch('load_secret_key', return_value='chelsea-key')
        self.sleeps = []
        # main() points sys.stdout and sys.stderr at its log file; put them back afterwards
        stdout, stderr = sys.stdout, sys.stderr
        self.addCleanup(setattr, sys, 'stderr', stderr)
        self.addCleanup(setattr, sys, 'stdout', stdout)
        # Close the log files main() opened; a test may already have put sys.stdout back
        self.tees = []
        start_logging = print_server_v2.start_logging
        self.patch('start_logging', side_effect=lambda location: self.tees.append(start_logging(location)) or self.tees[-1])
        self.addCleanup(self.close_log_files)
        root_handlers = logging.getLogger().handlers[:]
        self.addCleanup(setattr, logging.getLogger(), 'handlers', root_handlers)

    def close_log_files(self):
        for tee in self.tees:
            if tee.file:
                tee.file.close()

    def run_main(self, polls, overslept=()):
        # overslept[i]: extra seconds the i-th sleep took (the computer asleep, say)
        clock = [time.time()]

        def sleep(seconds):
            clock[0] += seconds + (overslept[len(self.sleeps)] if len(self.sleeps) < len(overslept) else 0)
            self.sleeps.append(seconds)
            if len(self.sleeps) >= polls:
                raise KeyboardInterrupt
        with mock.patch.object(print_server_v2.time, 'sleep', side_effect=sleep), \
                mock.patch.object(print_server_v2.time, 'time', side_effect=lambda: clock[0]):
            print_server_v2.main(['Chelsea', '--printer-ip', '10.0.0.1'])

    def log_text(self):
        log_dir = os.path.join(self.dir.name, 'chelsea_print_server_logs')
        return ''.join(open(os.path.join(log_dir, name), encoding='utf-8').read() for name in sorted(os.listdir(log_dir)))

    def test_output_is_written_to_daily_log_file(self):
        self.patch('Network', new=broken_printer())
        with mock.patch.object(print_server_v2.requests, 'get', side_effect=requests.exceptions.ConnectionError('down')):
            self.run_main(polls=2)
        log_dir = os.path.join(self.dir.name, 'chelsea_print_server_logs')
        self.assertEqual(os.listdir(log_dir), [f"chelsea_print_server_{time.strftime('%Y-%m-%d')}.log"])
        log = self.log_text()
        self.assertIn('Starting optimized print server for Chelsea', log)
        self.assertEqual(log.count('Connection failed - server may be down'), 2)
        self.assertNotIn('chelsea-key', log)
        for line in log.splitlines():
            self.assertRegex(line, r'^\d\d:\d\d:\d\d ')

    def test_late_check_is_logged(self):
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([])):
            self.run_main(polls=3, overslept=(0, 45 * 60))
        log = self.log_text()
        self.assertEqual(log.count('minutes late'), 1)
        self.assertIn('This check is 45 minutes late', log)

    def test_library_log_messages_reach_the_log_file(self):
        def unusable_printer(*args, **kwargs):
            logging.getLogger('escpos').error('Network device %s not found', '10.0.0.1')
            return mock.Mock(is_usable=mock.Mock(return_value=False))
        self.patch('Network', side_effect=unusable_printer)
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([JOB])):
            self.run_main(polls=1)
        self.assertIn('Network device 10.0.0.1 not found', self.log_text())

    def test_unexpected_error_logs_traceback(self):
        self.patch('poll_once', side_effect=RuntimeError('boom'))
        self.run_main(polls=1)
        log = self.log_text()
        self.assertIn('Unexpected error in main loop: boom', log)
        self.assertIn('Traceback (most recent call last)', log)

    def test_keeps_polling_while_server_down(self):
        get = self.patch('requests')
        get.exceptions = requests.exceptions
        get.get.side_effect = [requests.exceptions.ConnectionError('down'), requests.exceptions.Timeout('slow'),
                               mock.Mock(status_code=503), RuntimeError('unexpected'),
                               requests.exceptions.ConnectionError('down'), ok_response([])]
        self.run_main(polls=6)
        self.assertEqual(get.get.call_count, 6)
        self.assertEqual(self.sleeps, [60, 60, 60, 60, 300, 60])

    def test_spool_survives_restart(self):
        self.patch('Network', new=broken_printer())
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([JOB])):
            self.run_main(polls=1)
        # Restarted: the server has nothing new, the printer works again
        self.sleeps = []
        printer = self.patch('Network', new=working_printer())
        with mock.patch.object(print_server_v2.requests, 'get', return_value=ok_response([])):
            self.run_main(polls=1)
        printer.return_value.text.assert_called_once_with('SLIP 7')
        self.assertEqual(self.saved_spool(), [])

    def test_second_copy_exits(self):
        lock = print_server_v2.acquire_single_instance_lock('Chelsea')
        self.assertIsNotNone(lock)
        self.addCleanup(lock.close)
        get = self.patch('requests')
        with self.assertRaises(SystemExit) as exit:
            self.run_main(polls=1)
        self.assertEqual(exit.exception.code, 1)
        get.get.assert_not_called()

    def test_lock_failure_reports_the_os_error(self):
        # e.g. Windows (Hyper-V/WSL) has reserved the port: say why, not just "already running"
        sock = mock.MagicMock()
        sock.bind.side_effect = OSError(10013, 'An attempt was made to access a socket in a way forbidden by its access permissions')
        out = io.StringIO()
        with mock.patch.object(print_server_v2.socket, 'socket', return_value=sock), \
                contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            self.run_main(polls=1)
        self.assertIn('forbidden by its access permissions', out.getvalue())


@unittest.skipIf(print_server_v2 is None, 'needs python-escpos and requests')
class SingleInstanceLockTests(unittest.TestCase):

    def test_lock_is_exclusive_per_location(self):
        chelsea = print_server_v2.acquire_single_instance_lock('Chelsea')
        self.assertIsNotNone(chelsea)
        try:
            self.assertIsNone(print_server_v2.acquire_single_instance_lock('Chelsea'))
            greenwich = print_server_v2.acquire_single_instance_lock('Greenwich')
            self.assertIsNotNone(greenwich)
            greenwich.close()
        finally:
            chelsea.close()
        # Released when the first copy exits
        again = print_server_v2.acquire_single_instance_lock('Chelsea')
        self.assertIsNotNone(again)
        again.close()




@unittest.skipIf(print_server_v2 is None, 'needs python-escpos and requests')
class LogFileTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.console = io.StringIO()
        self.tee = print_server_v2.DailyLogTee(self.console, self.dir.name, 'barrow_print_server')
        self.addCleanup(lambda: self.tee.file and self.tee.file.close())

    def log_path(self, date):
        return os.path.join(self.dir.name, f'barrow_print_server_{date}.log')

    def test_each_line_is_timestamped_and_also_shown(self):
        self.tee.write('one\ntw')
        self.tee.write('o\n')
        self.tee.write('three\n')
        self.assertEqual(self.console.getvalue(), 'one\ntwo\nthree\n')
        with open(self.log_path(time.strftime('%Y-%m-%d')), encoding='utf-8') as f:
            lines = f.read().splitlines()
        self.assertEqual([line[9:] for line in lines], ['one', 'two', 'three'])
        for line in lines:
            self.assertRegex(line, r'^\d\d:\d\d:\d\d ')

    def test_new_file_each_day_and_old_files_pruned(self):
        self.tee.write('today\n')
        old_file = self.tee.file
        expired = self.log_path('2000-01-01')
        recent = self.log_path(time.strftime('%Y-%m-%d', time.localtime(time.time() - 5 * 24 * 60 * 60)))
        unrelated = os.path.join(self.dir.name, 'barrow_unprinted_receipts.json')
        for path in [expired, recent, unrelated]:
            open(path, 'w').close()
        self.tee.date = '2000-01-02'  # as if the date just changed
        self.tee.write('later\n')
        self.assertTrue(old_file.closed)
        self.assertEqual(self.tee.date, time.strftime('%Y-%m-%d'))
        self.assertFalse(os.path.exists(expired))
        self.assertTrue(os.path.exists(recent))
        self.assertTrue(os.path.exists(unrelated))

    def test_unwritable_log_dir_still_prints_to_console(self):
        blocker = os.path.join(self.dir.name, 'not_a_dir')
        open(blocker, 'w').close()
        tee = print_server_v2.DailyLogTee(self.console, blocker, 'barrow_print_server')
        tee.write('still shown\n')
        tee.write('again\n')
        self.assertIn('still shown\n', self.console.getvalue())
        self.assertEqual(self.console.getvalue().count('Could not open a log file'), 1)
        # Once the folder can be created, logging starts without waiting for the next day
        os.remove(blocker)
        tee.write('logged now\n')
        self.addCleanup(tee.file.close)
        with open(os.path.join(blocker, f"barrow_print_server_{time.strftime('%Y-%m-%d')}.log"), encoding='utf-8') as f:
            self.assertIn('logged now', f.read())


@unittest.skipIf(print_server_v2 is None, 'needs python-escpos and requests')
class QuickEditTests(unittest.TestCase):

    def test_does_nothing_off_windows(self):
        fake = mock.MagicMock()
        with mock.patch.object(print_server_v2.os, 'name', 'posix'), mock.patch.object(print_server_v2, 'ctypes', fake):
            print_server_v2.disable_console_quick_edit()
        fake.windll.kernel32.SetConsoleMode.assert_not_called()

    def test_clears_quick_edit_and_keeps_other_flags(self):
        # (mode before, mode set): QuickEdit (0x40) cleared, extended flags (0x80) always set
        for before, after in [(0x01F7, 0x01B7), (0x0047, 0x0087)]:
            fake = mock.MagicMock(c_uint32=ctypes.c_uint32, byref=ctypes.byref)
            kernel32 = fake.windll.kernel32

            def get_console_mode(handle, ref, before=before):
                ref._obj.value = before
                return 1
            kernel32.GetConsoleMode.side_effect = get_console_mode
            kernel32.SetConsoleMode.return_value = 1
            with mock.patch.object(print_server_v2.os, 'name', 'nt'), mock.patch.object(print_server_v2, 'ctypes', fake), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                print_server_v2.disable_console_quick_edit()
            kernel32.GetStdHandle.assert_called_once_with(-10)
            self.assertEqual(kernel32.SetConsoleMode.call_args.args[1], after)
            self.assertIn('Turned off QuickEdit Mode', out.getvalue())


if __name__ == '__main__':
    unittest.main()
