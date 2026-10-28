# Tests for the Windows print client, print_server_v2.py. They mock the printer and HTTP.
# python-escpos is a print-client-only dependency (not in requirements.txt), so run with e.g.
#   uv run --with python-escpos --with requests python -m unittest test_print_server_v2
import contextlib
import io
import json
import os
import tempfile
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

    def run_main(self, polls):
        def sleep(seconds):
            self.sleeps.append(seconds)
            if len(self.sleeps) >= polls:
                raise KeyboardInterrupt
        with mock.patch.object(print_server_v2.time, 'sleep', side_effect=sleep):
            print_server_v2.main(['Chelsea', '--printer-ip', '10.0.0.1'])

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


if __name__ == '__main__':
    unittest.main()
